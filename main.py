import os
from automation.auto_placer import main
from utils.metrics_fetcher import MetricsFetcher

if __name__ == "__main__":
    os.makedirs('data', exist_ok=True)
    fetcher = MetricsFetcher()

    fly_app_name = os.environ.get('FLY_APP_NAME')
    
    if not fly_app_name:
        raise ValueError("FLY_APP_NAME not set in environment variables")
    
    traffic_data = fetcher.fetch_region_traffic(fly_app_name)
    
    print(traffic_data)

    # main()