from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apis.api_router import router  
import logging
from logging.handlers import RotatingFileHandler
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Create logs directory
os.makedirs("./database/logs", exist_ok=True)

# Configure logging
log_file = "./database/logs/app.log"
handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=3)  # 5MB logs
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
handler.setFormatter(formatter)

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.addHandler(handler)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"], 
)

# Include router
app.include_router(router, prefix="/api/v1", tags=["report"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app=app, port=80, host="0.0.0.0")
