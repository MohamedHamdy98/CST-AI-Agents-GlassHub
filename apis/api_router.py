import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from typing import List
import logging, uuid, shutil, json, requests
from utils.helper_functions import compress_image_to_max_size
from agent.reports import Reports
from agent.dynamic_controls import generate_compliance_prompt, save_control_prompt, merge_all_controls, parse_classification
from agent.chat_bot import ChatBotMain, ChatBotGeneral
from utils.schemas import ControlsRequest
from utils.helper_functions import upload_to_azure_blob, delete_files, download_blob_from_url, download_image_gathering, load_python_module
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv
from typing import Dict
from urllib.parse import urlparse
import httpx, asyncio


# Load environment variables from .env file
load_dotenv()

# Logger setup
logger = logging.getLogger("report_router")
logger.setLevel(logging.INFO)

router = APIRouter()

# Azure Connection
AZURE_CONNECTION_STRING = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
CONTAINER_NAME = "glass-hub-db"
blob_service_client = BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)

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


# for enterprise compliance controls
@router.post("/generate_enterprise_controls")
async def generate_enterprise_controls(
    enterprise_name: str,
    file: UploadFile = File(..., description="JSON file containing information about enterprise controls [control_number, control_name, control_statement, control_guidelines, classification, expert_type, standard_type]")):
    """
    Accept a JSON file containing a list of controls and process each one.
    """
    try:
        if not file.filename.endswith(".json"):
            raise HTTPException(status_code=400, detail="Uploaded file must be a .json file")
        if not enterprise_name:
            raise HTTPException(status_code=400, detail="Enterprise name is required")

        contents = await file.read()
        json_data = json.loads(contents)

        data = ControlsRequest(**json_data)

        results = {}

        for control in data.controls:
            logger.info(f"Processing control: {control.control_number}")

            # 1. Generate prompt
            prompt = generate_compliance_prompt(
                control.control_number,
                control.control_name,
                control.control_statement,
                control.control_guidelines,
                control.classification,
                control.expert_type,
                control.standard_type
            )

            # 2. Save prompt
            file_path = save_control_prompt(control.control_number, prompt)
            logger.info(f"Prompt saved for {control.control_number} at {file_path}")

            results[control.control_number] = {"prompt": prompt}

        # 3. Merge all controls
        merge_file_path = merge_all_controls()
        logger.info("All control prompts merged successfully.")

        # 4. Upload merged file to Azure Blob Storage
        blob_name = f"{enterprise_name}_controls.py"
        url = upload_to_azure_blob(merge_file_path, CONTAINER_NAME, blob_name, AZURE_CONNECTION_STRING)
        logger.info(f"Merged controls uploaded to Azure Blob Storage: {url}")
        results[f"{enterprise_name}_controls_url"] = url

        return results

    except Exception as e:
        logger.exception("Failed to process JSON file.")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        delete_files("./database/saved_controls")


@router.post("/chat_main")
async def chat_main(
    user_message: str = Form(...),
    control_number_json_file: UploadFile = File(..., description="JSON file containing control_number"),
    control_blob_url: str = Form(..., description="URL of the control blob file on Azure Blob Storage"),
    report: str = Form(..., description="Report content from agent")
):
    if not control_number_json_file.filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="Uploaded control_number_json_file must be a .json file")

    if not control_blob_url.startswith("https"):
        raise HTTPException(status_code=400, detail="Control blob URL must be a valid HTTPS URL")

    # ✅ Parse control number from uploaded JSON
    control_data = json.loads(await control_number_json_file.read())
    control_number = control_data["controls"][0].get("control_number")  # e.g., "control_AC-1"
    if not control_number:
        raise HTTPException(status_code=400, detail="control_number missing in JSON")

    logger.info(f"Chat initiated for control number: {control_number} with message: {user_message}")

    # ✅ Download .py file from Azure
    temp_dir = "./temp_uploads"
    os.makedirs(temp_dir, exist_ok=True)

    parsed_url = urlparse(control_blob_url)
    blob_filename = os.path.basename(parsed_url.path)
    local_control_path = os.path.join(temp_dir, blob_filename)

    try:
        download_blob_from_url(control_blob_url, local_control_path, AZURE_CONNECTION_STRING)

        # ✅ Dynamically import the Python module
        controls_module = load_python_module(local_control_path)

        # ✅ Convert control_number to a valid Python variable name
        variable_name = control_number.replace("-", "_")  # control_AC-1 → control_AC_1

        # ✅ Extract the variable from the module
        if not hasattr(controls_module, variable_name):
            raise HTTPException(status_code=404, detail=f"Variable '{variable_name}' not found in the control file")

        control_text = getattr(controls_module, variable_name)

        # ✅ Call chatbot
        chatbot = ChatBotMain(control_text, report)
        response = chatbot.chat(user_message)

        logger.info("Chatbot responded successfully.")
        return {"response": response}

    except Exception as e:
        logger.exception("Chatbot failed to respond.")
        raise HTTPException(status_code=500, detail=str(e))



@router.post("/chat_general")
async def chat_general(
    user_message: str = Form(...),
    control_number_json_file: UploadFile = File(..., description="JSON file containing control_number"),
    control_blob_url: str = Form(..., description="URL of the control blob file on Azure Blob Storage"),
    report: str = Form(..., description="Report content from agent")
):
    if not control_number_json_file.filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="Uploaded control_number_json_file must be a .json file")

    if not control_blob_url.startswith("https"):
        raise HTTPException(status_code=400, detail="Control blob URL must be a valid HTTPS URL")

    # ✅ Parse control number from uploaded JSON
    control_data = json.loads(await control_number_json_file.read())
    control_number = control_data["controls"][0].get("control_number")  # e.g., "control_AC-1"
    if not control_number:
        raise HTTPException(status_code=400, detail="control_number missing in JSON")

    logger.info(f"Chat initiated for control number: {control_number} with message: {user_message}")

    # ✅ Download .py file from Azure
    temp_dir = "./temp_uploads"
    os.makedirs(temp_dir, exist_ok=True)

    parsed_url = urlparse(control_blob_url)
    blob_filename = os.path.basename(parsed_url.path)
    local_control_path = os.path.join(temp_dir, blob_filename)

    try:
        download_blob_from_url(control_blob_url, local_control_path, AZURE_CONNECTION_STRING)

        # ✅ Dynamically import the Python module
        controls_module = load_python_module(local_control_path)

        # ✅ Convert control_number to a valid Python variable name
        variable_name = control_number.replace("-", "_")  # control_AC-1 → control_AC_1

        # ✅ Extract the variable from the module
        if not hasattr(controls_module, variable_name):
            raise HTTPException(status_code=404, detail=f"Variable '{variable_name}' not found in the control file")

        control_text = getattr(controls_module, variable_name)

        # ✅ Call chatbot
        chatbot = ChatBotGeneral(control_text, report)
        response = chatbot.chat(user_message)

        logger.info("Chatbot responded successfully.")
        return {"response": response}

    except Exception as e:
        logger.exception("Chatbot failed to respond.")
        raise HTTPException(status_code=500, detail=str(e))



@router.get("get_logs")
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



