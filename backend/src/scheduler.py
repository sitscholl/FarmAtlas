from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, time
from typing import Any, Awaitable, Callable

import pandas as pd
from pandas.tseries.frequencies import to_offset
from pandas.tseries.offsets import BaseOffset, Tick

from .runtime import RuntimeContext

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class WorkflowJob:
    workflow_name: str
    freq: str
    time_of_day: time
    run_kwargs: dict[str, Any] = field(default_factory=dict)
    next_run: pd.Timestamp | None = None
    last_started_at: pd.Timestamp | None = None
    last_finished_at: pd.Timestamp | None = None
    last_error: str | None = None


class WorkflowScheduler:
    def __init__(
        self,
        runtime: RuntimeContext,
        workflows_config: dict[str, Any] | None = None,
    ) -> None:
        self.runtime = runtime
        self.timezone = runtime.timezone
        self.workflows_config = workflows_config or runtime.config.get("workflows", {})
        self.jobs = self._build_jobs(self.workflows_config)
        self._tasks: dict[str, asyncio.Task] = {}

    def start(self) -> None:
        if self._tasks:
            logger.debug("Workflow scheduler already running")
            return

        for job in self.jobs.values():
            self._tasks[job.workflow_name] = asyncio.create_task(
                self._run_job_loop(job),
                name=f"workflow-scheduler:{job.workflow_name}",
            )

        logger.info("Workflow scheduler started with %s job(s)", len(self.jobs))

    def stop(self) -> None:
        for task in self._tasks.values():
            task.cancel()
        self._tasks.clear()

    async def run_workflow_once(self, workflow_name: str) -> None:
        job = self.jobs.get(workflow_name)
        if job is None:
            raise ValueError(f"Unknown scheduled workflow: {workflow_name}")
        await self._execute_job(job)

    def get_job_states(self) -> dict[str, dict[str, Any]]:
        return {
            workflow_name: {
                "freq": job.freq,
                "time": job.time_of_day.strftime("%H:%M"),
                "next_run": None if job.next_run is None else job.next_run.isoformat(),
                "last_started_at": None if job.last_started_at is None else job.last_started_at.isoformat(),
                "last_finished_at": None if job.last_finished_at is None else job.last_finished_at.isoformat(),
                "last_error": job.last_error,
                "run_kwargs": dict(job.run_kwargs),
            }
            for workflow_name, job in self.jobs.items()
        }

    def _build_jobs(self, workflows_config: dict[str, Any]) -> dict[str, WorkflowJob]:
        jobs: dict[str, WorkflowJob] = {}

        for workflow_name, workflow_config in workflows_config.items():
            if not workflow_config.get("enabled", True):
                logger.info("Skipping disabled workflow schedule for %s", workflow_name)
                continue

            self.runtime.workflows.get(workflow_name)

            schedule_config = workflow_config.get("schedule")
            if not schedule_config:
                logger.info("Skipping workflow %s because no schedule is configured", workflow_name)
                continue

            freq = str(schedule_config.get("freq", "D"))
            self._validate_freq(freq)
            jobs[workflow_name] = WorkflowJob(
                workflow_name=workflow_name,
                freq=freq,
                time_of_day=self._parse_time_of_day(schedule_config.get("time", "00:00")),
                run_kwargs=dict(workflow_config.get("run") or {}),
            )

        return jobs

    async def _run_job_loop(self, job: WorkflowJob) -> None:
        try:
            while True:
                now = pd.Timestamp.now(tz=self.timezone)
                next_run = self._next_run(job, now)
                job.next_run = next_run

                sleep_seconds = max((next_run - now).total_seconds(), 0.0)
                logger.info(
                    "Workflow %s scheduled for %s (in %.1fs)",
                    job.workflow_name,
                    next_run.isoformat(),
                    sleep_seconds,
                )
                await asyncio.sleep(sleep_seconds)
                await self._execute_job(job)
        except asyncio.CancelledError:
            logger.info("Workflow scheduler loop cancelled for %s", job.workflow_name)
            raise

    async def _execute_job(self, job: WorkflowJob) -> None:
        started_at = pd.Timestamp.now(tz=self.timezone)
        job.last_started_at = started_at
        job.last_error = None
        logger.info(
            "Starting scheduled workflow %s with args=%s",
            job.workflow_name,
            job.run_kwargs,
        )

        try:
            await asyncio.to_thread(
                self.runtime.run_workflow_for_fields,
                workflow_name=job.workflow_name,
                **job.run_kwargs,
            )
        except Exception as exc:
            job.last_error = str(exc)
            logger.exception("Scheduled workflow %s failed", job.workflow_name)
        finally:
            job.last_finished_at = pd.Timestamp.now(tz=self.timezone)

    def _next_run(self, job: WorkflowJob, now: pd.Timestamp) -> pd.Timestamp:
        offset = to_offset(job.freq)
        if isinstance(offset, Tick):
            return self._next_tick_run(offset, job.time_of_day, now)
        return self._next_calendar_run(offset, job.time_of_day, now)

    def _next_tick_run(
        self,
        offset: BaseOffset,
        time_of_day: time,
        now: pd.Timestamp,
    ) -> pd.Timestamp:
        candidate = now.normalize() + self._time_to_timedelta(time_of_day)
        while candidate <= now:
            candidate = candidate + offset
        return candidate

    def _next_calendar_run(
        self,
        offset: BaseOffset,
        time_of_day: time,
        now: pd.Timestamp,
    ) -> pd.Timestamp:
        current_day = now.normalize()
        if offset.is_on_offset(current_day):
            candidate = current_day + self._time_to_timedelta(time_of_day)
            if candidate > now:
                return candidate
            return (current_day + offset) + self._time_to_timedelta(time_of_day)

        next_day = offset.rollforward(current_day)
        candidate = next_day + self._time_to_timedelta(time_of_day)
        if candidate > now:
            return candidate
        return (next_day + offset) + self._time_to_timedelta(time_of_day)

    @staticmethod
    def _validate_freq(freq: str) -> None:
        try:
            to_offset(freq)
        except ValueError as exc:
            raise ValueError(
                f"Invalid workflow schedule frequency {freq!r}. "
                "Use a pandas offset alias such as 'D', 'W-MON', '6H', or 'MS'."
            ) from exc

    @staticmethod
    def _parse_time_of_day(value: str) -> time:
        try:
            return datetime.strptime(value, "%H:%M").time()
        except ValueError as exc:
            raise ValueError(
                "Workflow schedule time must be in HH:MM 24-hour format."
            ) from exc

    @staticmethod
    def _time_to_timedelta(value: time) -> pd.Timedelta:
        return pd.Timedelta(
            hours=value.hour,
            minutes=value.minute,
            seconds=value.second,
        )
