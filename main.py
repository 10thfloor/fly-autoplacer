import os
from automation.auto_placer import main
from utils.fancy_logger import get_logger
from utils.metrics_fetcher import MetricsFetcher
import logging
import sys
import signal

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("logs/auto_placer.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = get_logger(__name__)

def signal_handler(signum, frame):
    logger.debug(f"Received signal {signum}. Shutting down gracefully...")
    # Cleanup code here
    sys.exit(0)

if __name__ == "__main__":
    os.makedirs('data', exist_ok=True)
    # fetcher = MetricsFetcher()

    # fly_app_name = os.environ.get('FLY_APP_NAME')
    
    # if not fly_app_name:
    #     raise ValueError("FLY_APP_NAME not set in environment variables")
    
    # traffic_data = fetcher.fetch_region_traffic(fly_app_name)
    
    # print(traffic_data)

    logger.info("Application started")
  
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    main()