import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
import logging
from utils.dynamic_controls import generate_compliance_prompt, save_control_prompt, merge_all_controls
from utils.schemas import ControlsRequest
from utils.helper_functions import (upload_to_azure_blob, delete_files, extract_clauses_with_system_message, extract_json_objects, flatten_clauses)
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv
from rag.knowledge_retriever import retrieve_relevant_knowledge

# Load environment variables from .env file
load_dotenv()

# Logger setup
logger = logging.getLogger("report_router")
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
handler.stream.reconfigure(encoding='utf-8')  
logger.addHandler(handler)
logger.setLevel(logging.INFO)

router = APIRouter(prefix="/api/v1", tags=["data"])

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



# For RAG System
@router.post("/filter_terms", description="Search for relevant documents based on user input and company details")
async def filter_terms(
    user_question: str = Form(..., description="User's question"),
    is_licensed: str = Form(..., description="Is the company licensed? (yes/no)"),
    license_type: str = Form(..., description="What is the license type?"),
    regulations: str = Form(..., description="What are the regulations?"),
    service_type: str = Form(..., description="What is the service type?"),
    k: int = Form(4, description="Number of top documents to retrieve"),
):
    try:
        
        if not is_licensed or not license_type or not regulations or not service_type or not user_question:
            raise HTTPException(status_code=400, detail="All fields are required")

        logger.info("Semantic search initiated...")

        results = retrieve_relevant_knowledge(
            user_question=user_question,
            is_licensed=is_licensed,
            license_type=license_type,
            service_type=service_type,
            regulations=regulations,
            k=k
        )

        # convert the result to json
        content = results[0]['content']
        source = results[0]['source']
        page = results[0].get('page', "Page not specified")
        json_blocks = extract_json_objects(content)

        data_js = []
        for block in json_blocks:
            try:
                data_js.append(json.loads(block))
            except Exception as e:
                print("Error loading block:", e)

        flattened = flatten_clauses(data_js, source, page)

        terms = extract_clauses_with_system_message(QWEN3_ENDPOINT_CHAT, flattened, 2000, False)
        terms = terms.get('response')

        print("Json Terms:", terms)
        print("Type of Terms:", type(terms))

        terms_dict = json.loads(terms)
        flattened_terms = terms_dict["flattened"]
        print("Type of flattened_terms:", type(flattened_terms))
        parsed_response = [item for item in flattened_terms if len(item.get("description", "")) >= 50]

        # filtered_terms = filter_terms_js(terms)
        
        return {
            "parsed_response":parsed_response
            }

    except Exception as e:
        logger.exception("Semantic search failed.")
        raise HTTPException(status_code=500, detail=str(e))
