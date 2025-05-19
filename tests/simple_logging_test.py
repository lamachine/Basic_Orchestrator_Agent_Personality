import logging
import os

# Create a debug folder if it doesn't exist
os.makedirs("debug", exist_ok=True)

# Configure logging to write to a file
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("debug/log_test.log", mode="a"),
        logging.StreamHandler(),
    ],
)

# Log a test message
logging.debug("This is a test log message to verify logging setup.")

print("Logging test complete. Check the 'debug/log_test.log' file for the message.")
