import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from utils.helper_functions import download_image_gathering
import logging, shutil, json, uuid
from agent.reports import Reports
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv
from typing import Dict, List
from urllib.parse import urlparse
import httpx, asyncio

# Load environment variables from .env file
load_dotenv()

# Logger setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ✅ prevent adding multiple handlers
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
    handler.setFormatter(formatter)
    handler.stream.reconfigure(encoding='utf-8') 
    logger.addHandler(handler)

router = APIRouter(prefix="/api/v1", tags=["main_process"])


# Alibaba cloud Connection
ACCESS_KEY_ID = os.getenv("OSS_ACCESS_KEY_ID")
ACCESS_KEY_SECRET = os.getenv("OSS_ACCESS_KEY_SECRET")
ENDPOINT = os.getenv("OSS_ENDPOINT")
BUCKET_NAME = os.getenv("OSS_BUCKET")

# Qwen3 LLM Endpoint
QWEN2_VL_ENDPOINT = os.getenv('QWEN2_VL_ENDPOINT')



@router.post("/generate_report", description="Generate report based on form inputs and uploaded images.")
async def generate_report(
    language: str = Form('ar', description="Select (ar) for Arabic or (en) for English language for results."),
    title: str = Form(..., description="Control title"),
    description_control: str = Form(..., description="Description of the control"),
    audit_instructions: str = Form(..., description="Audit instructions"),
    clause_audit_instructions: str = Form(..., description="Clause-level audit instructions"),
    images: List[UploadFile] = File(..., description="List of images")
):
    tmp_folder = f"/tmp/{uuid.uuid4()}"
    try:
        logger.info("Starting report generation...")

        os.makedirs(tmp_folder, exist_ok=True)

        image_paths = []
        for image in images:
            image_path = os.path.join(tmp_folder, image.filename)
            with open(image_path, "wb") as buffer:
                shutil.copyfileobj(image.file, buffer)
            image_paths.append(image_path)

        logger.info(f"Saved {len(image_paths)} images for processing.")

        control_data = {
            "title": title,
            "description_control": description_control,
            "audit_instructions": audit_instructions,
            "clause_audit_instructions": clause_audit_instructions,
        }

        reports_generator = Reports(
            user_message="",
            language=language,
            control_number=title,
            list_image_paths=image_paths,
            controls_content=control_data,
            api=QWEN2_VL_ENDPOINT
        )
        result = reports_generator.run_full_pipeline()

        logger.info("Report generation completed.")
        return {"result": result}

    except Exception as e:
        logger.error(f"Error in generate_report: {e}")
        return {"error": str(e)}
    
    finally:
        if os.path.exists(tmp_folder):
            shutil.rmtree(tmp_folder)



@router.get("/get_logs")
def get_logs():
    log_file = "./database/logs/app.log"
    if not os.path.exists(log_file):
        raise HTTPException(status_code=404, detail="Log file not found")
    with open(log_file, "r") as f:
        logs = f.readlines()
    return {"logs": logs}

@router.delete("/clear_log")
def clear_log():
    log_file = "./database/logs/app.log"
    if not os.path.exists(log_file):
        raise HTTPException(status_code=404, detail="Log file not found")
    # Clear the log file
    with open(log_file, "w", encoding="utf-8") as f:
        f.truncate(0)
    return {"message": "Log file cleared successfully"} 

@router.get("/")
def home():
    return {"message": "Welcome to the GlassHub Agent for Enterprise and Regulator Compliance!"}



