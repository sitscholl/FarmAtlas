import logging
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

from .database.db import Database
from .et import ET0Calculator
from .et.et_correction import ETCorrection
from .field import FieldContext
from .meteo.load import MeteoLoader
from .meteo.resample import MeteoResampler
from .meteo.validate import MeteoValidator
from .workflows.water_balance import WaterBalanceWorkflow

logger = logging.getLogger(__name__)


def load_config_file(config_file: str | Path) -> dict:
    """Load configuration from YAML file."""
    try:
        with open(config_file, 'r') as file:
            config = yaml.safe_load(file)
            logger.info(f"Loaded config file from {config_file}")
    except FileNotFoundError:
        logger.error(f"Configuration file {config_file} not found")
        raise
    except yaml.YAMLError as e:
        logger.error(f"Error parsing configuration file: {e}")
        raise

    for handler in config.get('logging', {}).get('handlers', {}).values():
        if "filename" in handler.keys():
            Path(handler['filename']).parent.mkdir(parents=True, exist_ok=True)

    return config


@dataclass
class WorkflowCollection:
    water_balance: WaterBalanceWorkflow

    def get(self, workflow_name: str):
        workflow = getattr(self, workflow_name, None)
        if workflow is None:
            raise ValueError(f"Unknown workflow: {workflow_name}")
        return workflow


@dataclass
class RuntimeContext:
    config: dict
    config_file: str | Path | None = None

    @classmethod
    def from_config_file(cls, config_file: str | Path):
        config = load_config_file(config_file)
        return cls(config=config, config_file=config_file)

    def __post_init__(self):
        if self.config is None:
            raise ValueError("RuntimeContext requires a config dictionary")
        self.initialize_runtime(self.config)

    def initialize_runtime(self, config: dict):
        logger.info("Initializing Runtime Context")

        ## Timezone
        tz_name = config.get('general', {}).get('timezone')
        self.timezone = ZoneInfo(tz_name)

        ## Meteo Handler
        self.meteo_loader = MeteoLoader(**config.get('meteo', {}))
        
        ## Meteo Validator
        validator_config = config.get('meteo_validation', {})
        if 'timezone' in validator_config:
            logger.warning(
                "Found timezone key in validator config. This will be ignored and timezone is set to %s",
                self.timezone,
            )
            validator_config = {i: j for i, j in validator_config.items() if i != 'timezone'}
        self.meteo_validator = MeteoValidator(timezone=self.timezone, **validator_config)

        ## Meteo Resampler
        self.min_sample_size = config.get('resampling', {}).get('min_sample_size', 1)
        self.meteo_resampler = MeteoResampler(
            resample_colmap=config.get('resampling', {}).get('resample_colmap'),
        )

        ## Database
        self.db = Database(config.get('database', {}).get('path', 'sqlite:///db/database.db'))
       
        ## Fields
        if len(self.fields) == 0:
            logger.warning('No fields found in database.')

        ## Evapotranspiration
        et_calculator_cls = ET0Calculator.get_calculator_by_name(config['evapotranspiration']['method'])
        if et_calculator_cls is None:
            raise ValueError(
                f"ET0 calculator {config['evapotranspiration']['method']} not found. "
                f"Choose one of {ET0Calculator.registry.keys()}"
            )
        self.et_calculator = et_calculator_cls(
            corrector=ETCorrection(**config['evapotranspiration']['correction'])
        )

        self.workflows = WorkflowCollection(
            water_balance=WaterBalanceWorkflow(
                db=self.db,
                meteo_loader=self.meteo_loader,
                meteo_validator=self.meteo_validator,
                et_calculator=self.et_calculator,
                timezone=self.timezone,
                meteo_resampler=self.meteo_resampler,
                min_sample_size=int(self.min_sample_size),
            ),
        )

    def update_runtime(self, config_file: str | Path):
        self.config_file = Path(config_file)
        self.config = load_config_file(self.config_file)
        self.initialize_runtime(self.config)

    @property
    def fields(self) -> list[FieldContext]:
        with self.db.session_scope() as session:
            return [FieldContext.from_model(field) for field in self.db.fields.list_all(session)]

    def get_field(self, field_id: int) -> FieldContext:
        with self.db.session_scope() as session:
            field_model = self.db.fields.get_by_id(session, field_id)
            if field_model is None:
                raise ValueError(f"Unknown field id: {field_id}")
            return FieldContext.from_model(field_model)

    def get_fields_by_ids(self, field_ids: list[int] | None = None) -> list[FieldContext]:
        if field_ids is None:
            return list(self.fields)

        fields_by_id = {field.id: field for field in self.fields}
        missing_ids = [field_id for field_id in field_ids if field_id not in fields_by_id]
        if missing_ids:
            raise ValueError(f"Unknown field ids: {missing_ids}")
        return [fields_by_id[field_id] for field_id in field_ids]

    def run_workflow_for_fields(
        self,
        workflow_name: str,
        field_ids: list[int] | None = None,
        **kwargs,
    ) -> list[FieldContext]:
        fields = self.get_fields_by_ids(field_ids)
        workflow = self.workflows.get(workflow_name)
        return workflow.run(fields=fields, **kwargs)

    def run_workflow_for_field(
        self,
        workflow_name: str,
        field_id: int,
        **kwargs,
    ) -> FieldContext | None:
        results = self.run_workflow_for_fields(
            workflow_name=workflow_name,
            field_ids=[field_id],
            **kwargs,
        )
        return results[0] if results else None


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, force=True)
    runtime = RuntimeContext.from_config_file('config.example.yaml')
