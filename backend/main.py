import uvicorn

import logging
from src.app_config import get_log_config_path
from src.log_handler import LogHandler
from src.api import app

# Configure logging
log_handler = LogHandler.from_file(get_log_config_path())
log_handler.start_logger()

uvicorn.run(app, host="0.0.0.0", port=8000, log_level=None)
