import os
import sys
import threading
import time
import asyncio
from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import json
from automation import auto_placer
from utils.config_loader import Config
import uvicorn

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def watch_config(server):
    config_filepath = 'config.yaml'
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
    return {"status": "healthy"}

@app.post("/trigger")
async def trigger():
    try:
        result = auto_placer.main()
        # Return the result as JSON
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Error triggering auto-placer: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"message": "An error occurred while triggering the auto-placer"}
        )
    
# Modify run_server to be an async function
async def run_server(host, port):
    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level="info",
        reload=False  # Disable auto-reload
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
    host = "0.0.0.0"  # or your preferred host
    port = 8000  # or your preferred port

    while True:
        await run_server(host, port)
        logger.info("Server has shut down")
        logger.info("Restarting server in 1 second...")
        await asyncio.sleep(1)  # Brief pause before restarting

if __name__ == "__main__":
    asyncio.run(main())