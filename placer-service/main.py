import os
import threading
import time
import asyncio
from fastapi import FastAPI, Request, HTTPException
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
from automation import auto_placer
from utils.config_loader import Config
from utils.metrics_fetcher import MetricsFetcher
import uvicorn
from datetime import datetime, timezone  

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def watch_config(server):
    config_filepath = os.path.join('config', 'config.yml')
    last_mtime = os.path.getmtime(config_filepath)
    while not server.should_exit:
        time.sleep(1)  # Check every second
        try:
            current_mtime = os.path.getmtime(config_filepath)
            if current_mtime != last_mtime:
                logger.info(f"{config_filepath} has changed, restarting application...")
                server.should_exit = True  # Signal the server to shut down
                break
            else:
                last_mtime = current_mtime
        except FileNotFoundError:
            logger.warning(f"{config_filepath} not found. Continuing...")
            last_mtime = 0  # Reset last_mtime if file is not found

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Perform startup operations
    config = Config.get_config()
    if not config['dry_run']:
        if not os.environ.get('FLY_APP_NAME'):
            raise ValueError("FLY_APP_NAME environment variable is not set. This is required when not in dry run mode.")
    
    logger.info("Application startup complete")
    yield
    logger.info("Application shutdown complete")

app = FastAPI(lifespan=lifespan)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def exception_handler(request: Request, exc: Exception):
    logger.error(f"An error occurred: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"message": "An internal error occurred"},
    )

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/health")
async def health_check():
    try:
        config = Config.get_config()
        return {
            "status": "healthy",
            "config_loaded": bool(config),
            "dry_run": config.get('dry_run', True)
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

@app.get("/metrics")
async def get_metrics():
    try:
        metrics_fetcher = MetricsFetcher()
        traffic_data = metrics_fetcher.fetch_region_traffic()
        return {
            "traffic_data": traffic_data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/trigger")
async def trigger_auto_placer():
    try:
        config = Config.get_config()  # Get config from Config class
        auto_placer_instance = auto_placer.AutoPlacer(config)  # Pass config here
        results = await auto_placer_instance.process_traffic_data()
        logger.info(f"Auto-placer execution completed. Results: {results}")
        return JSONResponse(content={"status": "success", "results": results})
    except Exception as e:
        logger.error(f"Error triggering auto-placer: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
# Modify run_server to be an async function
async def run_server(host, port):
    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level="info",
        reload=False,
    )
    server = uvicorn.Server(config)

    # Start the config watcher thread
    config_watcher = threading.Thread(target=watch_config, args=(server,), daemon=True)
    config_watcher.start()

    logger.info(f"Server started on {host}:{port}")
    logger.info("Autoplacer running for App: ")

    # Run the server
    await server.serve()

async def main():
    host=["::", "0.0.0.0"] # or your preferred host
    port = 8000  # or your preferred port

    logger.info(f"Starting placer server on {host}:{port}")
    while True:
        await run_server(host, port)
        logger.info("Server has shut down")
        logger.info("Restarting server in 1 second...")
        await asyncio.sleep(1)  # Brief pause before restarting

if __name__ == "__main__":
    asyncio.run(main())
