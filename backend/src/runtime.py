import yaml

from pathlib import Path
from dataclasses import dataclass
import logging
from zoneinfo import ZoneInfo

from .meteo.load import MeteoLoader
from .meteo.validate import MeteoValidator
from .field import FieldContext
from .database.db import FarmDB
from .meteo.resample import MeteoResampler
from .et.base import ET0Calculator
from .et.et_correction import ETCorrection

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

    #Make sure log directory exists
    for handler_name, handler in config.get('logging', {}).get('handlers', {}).items():
        if "filename" in handler.keys():
            Path(handler['filename']).parent.mkdir(parents=True, exist_ok=True)

    return config

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
        tz_name = config.get('api', {}).get('timezone', 'Europe/Rome')
        self.timezone = ZoneInfo(tz_name)

        ## Meteo Handler
        self.meteo_loader = MeteoLoader(**config.get('meteo', {}))
        
        ## Meteo Validator
        self.meteo_validator = MeteoValidator(**config.get('meteo_validation', {}))

        ## Meteo Resampler
        self.min_sample_size = config.get('resampling', {}).get('min_sample_size', {})
        self.meteo_resampler = MeteoResampler(
            resample_colmap=config.get('resampling', {}).get('resample_colmap'),
        )

        ## Database
        self.db = FarmDB(config.get('database', {}).get('path', 'sqlite:///database.db'))
       
        ## Fields
        self.fields = [FieldContext.from_model(field) for field in self.db.get_all_fields()]
        if len(self.fields) == 0:
            logger.warning('No fields found in database.')

        ## Evapotranspiration
        et_calculator = ET0Calculator.get_calculator_by_name(config['evapotranspiration']['method'])
        if et_calculator is None:
            raise ValueError(f"ET0 calculator {config['evapotranspiration']['method']} not found. Choose one of {ET0Calculator.registry.keys()}")
        et_calculator.add_corrector(ETCorrection(**config['evapotranspiration']['correction']))
        self.et_calculator = et_calculator

        ## Scheduler

    def update_runtime(self, config_file: str | Path):
        self.config_file = Path(config_file)
        self.config = load_config_file(self.config_file)
        self.initialize_runtime(self.config)

if __name__ == '__main__':
    logging.basicConfig(level = logging.DEBUG, force = True)
    runtime = RuntimeContext.from_config_file('config.example.yaml')
