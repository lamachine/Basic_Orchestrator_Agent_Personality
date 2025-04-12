import logging
from src.config import Configuration

class LoggingService:
    def __init__(self, config: Configuration, log_level=logging.DEBUG, log_file='app.log'):
        self.config = config
        self.log_level = log_level
        self.log_file = log_file
        self.logger = logging.getLogger(__name__)
        self.setup_logging()

    def setup_logging(self):
        try:
            # Initialize logging
            logging.basicConfig(
                level=self.log_level,
                format='%(asctime)s - %(levelname)s - %(message)s',
                handlers=[
                    logging.FileHandler(self.log_file),
                    logging.StreamHandler()
                ]
            )
            self.logger.debug("Logging initialized successfully")
        except Exception as e:
            print(f"Error setting up logging: {e}")
            # Setup basic logging as fallback
            logging.basicConfig(level=logging.INFO) 