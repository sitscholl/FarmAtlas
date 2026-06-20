import logging

from fastapi import APIRouter, HTTPException, Query, status

from ..schemas import FruitCountSurveyCreate, FruitCountSurveyRead, FruitCountSurveyUpdate
from .utils import raise_write_http_error, runtime

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/fruit-counts", tags=["fruit-counts"])


@router.get("/surveys", response_model=list[FruitCountSurveyRead])
async def list_fruit_count_surveys(
    season_year: int | None = None,
    field_id: int | None = None,
    planting_id: int | None = None,
    section_id: int | None = None,
    timing_code: str | None = None,
    include_excluded: bool = Query(default=True),
):
    with runtime.db.session_scope() as session:
        surveys = runtime.db.fruit_counts.list_surveys(
            session,
            season_year=season_year,
            field_id=field_id,
            planting_id=planting_id,
            section_id=section_id,
            timing_code=timing_code,
            include_excluded=include_excluded,
        )
    return [FruitCountSurveyRead.model_validate(survey) for survey in surveys]


@router.get("/surveys/{survey_id}", response_model=FruitCountSurveyRead)
async def get_fruit_count_survey(survey_id: int):
    with runtime.db.session_scope() as session:
        survey = runtime.db.fruit_counts.get_by_id(session, survey_id)
    if survey is None:
        raise HTTPException(status_code=404, detail=f"Could not find any fruit count survey with id {survey_id}")
    return FruitCountSurveyRead.model_validate(survey)


@router.post("/surveys", response_model=FruitCountSurveyRead, status_code=status.HTTP_201_CREATED)
async def create_fruit_count_survey(survey: FruitCountSurveyCreate):
    try:
        data = survey.model_dump(exclude={"samples"})
        new_survey = runtime.db.fruit_count_service.create(
            **data,
            samples=[sample.model_dump() for sample in survey.samples],
        )
        return FruitCountSurveyRead.model_validate(new_survey)
    except Exception as exc:
        logger.exception("Adding fruit count survey failed: %s", exc)
        raise_write_http_error(exc)


@router.put("/surveys/{survey_id}", response_model=FruitCountSurveyRead)
async def update_fruit_count_survey(survey_id: int, survey: FruitCountSurveyUpdate):
    try:
        updates = survey.model_dump(exclude_unset=True)
        updated_survey = runtime.db.fruit_count_service.update(survey_id=survey_id, updates=updates)
        return FruitCountSurveyRead.model_validate(updated_survey)
    except Exception as exc:
        logger.exception("Updating fruit count survey %s failed: %s", survey_id, exc)
        raise_write_http_error(exc, not_found_prefixes=("Could not find any fruit count survey with id",))


@router.delete("/surveys/{survey_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_fruit_count_survey(survey_id: int):
    deleted = runtime.db.fruit_count_service.delete(survey_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Could not find any fruit count survey with id {survey_id}")
