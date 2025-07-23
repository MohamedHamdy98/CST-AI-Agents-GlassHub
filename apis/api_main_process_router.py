import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
import logging, shutil, json
from agent.reports import Reports
from utils.helper_functions import (download_blob_from_url, download_image_gathering)
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv
from typing import Dict
from urllib.parse import urlparse
import httpx, asyncio

# Load environment variables from .env file
load_dotenv()

# Logger setup
logger = logging.getLogger("report_router")
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
handler.stream.reconfigure(encoding='utf-8')  
logger.addHandler(handler)
logger.setLevel(logging.INFO)

router = APIRouter(prefix="/api/v1", tags=["main_process"])

# Azure Connection
AZURE_CONNECTION_STRING = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
CONTAINER_NAME = "cst"
blob_service_client = BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)

# Alibaba cloud Connection
ACCESS_KEY_ID = os.getenv("OSS_ACCESS_KEY_ID")
ACCESS_KEY_SECRET = os.getenv("OSS_ACCESS_KEY_SECRET")
ENDPOINT = os.getenv("OSS_ENDPOINT")
BUCKET_NAME = os.getenv("OSS_BUCKET")


# Qwen3 LLM Endpoint
QWEN3_ENDPOINT = os.getenv('QWEN3_ENDPOINT')
QWEN3_ENDPOINT_CHAT = os.getenv('QWEN3_ENDPOINT_CHAT')

# for supplier compliance controls
@router.post("/generate_report")
async def generate_report(
    control_blob_url: str = Form(..., description="URL to the .py file on Azure Blob Storage"),  
    json_file: UploadFile = File(..., description="JSON file containing control_number and image URLs from the supplier"),
):
    """
    Accepts:
    - control_blob_url (str): URL to a .py file on Azure Blob Storage
    - json_file (.json): Contains control_number and image URLs
    """
    temp_dir = os.path.join("./temp_uploads")
    os.makedirs(temp_dir, exist_ok=True)

    try:
        logger.info("Starting report generation from Azure Blob control file...")

        # ✅ Download .py from Azure
        if not control_blob_url.startswith("https"):
            raise HTTPException(status_code=400, detail="Control blob URL must be a valid HTTPS URL")
        
        parsed_url = urlparse(control_blob_url)
        blob_filename = os.path.basename(parsed_url.path)
        local_control_path = os.path.join(temp_dir, blob_filename)
        download_blob_from_url(control_blob_url, local_control_path, AZURE_CONNECTION_STRING)

        with open(local_control_path, "r", encoding="utf-8") as f:
            controls_content = f.read()

        # ✅ Load JSON control data
        if not json_file.filename.endswith(".json"):
            raise HTTPException(status_code=400, detail="Uploaded json_file must be a .json file")

        control_data = json.loads(await json_file.read())

        if "controls" not in control_data:
            raise HTTPException(status_code=400, detail="'controls' key missing in JSON")

        all_results: Dict[str, dict] = {}

        for control in control_data["controls"]:
            control_number = control.get("control_number")
            image_urls = control.get("Images", [])

            if not control_number or not image_urls:
                logger.warning(f"Skipping control with missing data: {control}")
                all_results[control_number or "unknown"] = {"error": "Missing control_number or Images"}
                continue

            logger.info(f"Processing control: {control_number} with {len(image_urls)} images")

            image_paths = []
            async with httpx.AsyncClient(timeout=10) as client:
                tasks = [download_image_gathering(client, url, temp_dir) for url in image_urls]
                results = await asyncio.gather(*tasks)
                image_paths = [res for res in results if res]

            if not image_paths:
                logger.warning(f"No valid images for control {control_number}")
                all_results[control_number] = {"error": "No valid images downloaded"}
                continue

            # ✅ Run report logic
            try:
                report_generator = Reports(
                    control_number=control_number,
                    list_image_paths=image_paths,
                    controls_content=controls_content
                )
                result = report_generator.final_output_handling_parsing()
                all_results[f"control_{control_number}"] = result
                logger.info(f"Successfully generated report for {control_number}")
            except Exception as e:
                logger.exception(f"Failed to generate report for {control_number}")
                all_results[f"control_{control_number}"] = {"error": str(e)}

        return all_results

    except Exception as e:
        logger.exception("Critical error in processing report generation.")
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
        logger.info(f"Temp directory cleaned: {temp_dir}")





@router.get("/get_logs")
def get_logs():
    log_file = "./database/logs/app.log"
    if not os.path.exists(log_file):
        raise HTTPException(status_code=404, detail="Log file not found")
    with open(log_file, "r") as f:
        logs = f.readlines()
    return {"logs": logs}

@router.get("/")
def home():
    return {"message": "Welcome to the GlassHub Agent for Enterprise and Supplier Compliance!"}



