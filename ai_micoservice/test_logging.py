"""
Utility to test the custom logging configuration and ensure logs are written to both console and file.
"""
from app.logger import logger
import time

def test_logging():
    """
    Generates logs at different levels to verify formatting and output handlers.
    """
    print("--- Starting Logging Test ---")
    
    logger.info("This is an INFO message - it shows things are working normally.")
    time.sleep(0.5)
    
    logger.warning("This is a WARNING message - it signals a potential minor issue.")
    time.sleep(0.5)
    
    logger.debug("This is a DEBUG message - usually used for deep troubleshooting.")
    time.sleep(0.5)
    
    try:
        # Simulate an error
        result = 1 / 0
    except Exception as e:
        logger.error(f"This is an ERROR message: {str(e)}", exc_info=True)

    print("--- Logging Test Complete ---")
    print("Check the console above for the formatted logs.")
    print("Also, check 'app.log' in the current directory to see if it was saved to a file!")

if __name__ == "__main__":
    test_logging()
