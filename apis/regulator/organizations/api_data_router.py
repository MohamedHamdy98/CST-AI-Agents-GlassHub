import os, sys, json
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from fastapi import APIRouter, Form, HTTPException, UploadFile, File
import logging
from fastapi.responses import JSONResponse
# from utils.dynamic_controls import generate_compliance_prompt, save_control_prompt, merge_all_controls
from utils.schemas import FilterTermsRequestRegulator, FileURLsRag
from utils.helper_functions import (extract_json_from_text, extract_json_objects, flatten_clauses, init_oss_bucket)
from dotenv import load_dotenv
from utils.create_instructions import process_parsed_response
from rag.knowledge_retriever import retrieve_relevant_knowledge_regulator
from rag.knowledge_ingestion import ingest_company_knowledge, download_files_from_cloud_storage
from utils.logs import setup_logger

# Load environment variables from .env file
load_dotenv()

# Logger setup


logger = setup_logger(__name__)
print(f"🔥 DEBUG: Module {__name__} logger setup complete!")

router = APIRouter(prefix="/api/v1/regulator/organization", tags=["Regulator Organization Data"])


# Alibaba cloud Connection
ACCESS_KEY_ID = os.getenv("OSS_ACCESS_KEY_ID")
ACCESS_KEY_SECRET = os.getenv("OSS_ACCESS_KEY_SECRET")
ENDPOINT = os.getenv("OSS_ENDPOINT")
BUCKET_NAME = os.getenv("OSS_BUCKET")
BUCKET = init_oss_bucket(ACCESS_KEY_ID, ACCESS_KEY_SECRET, ENDPOINT, BUCKET_NAME)

# Qwen3 LLM Endpoint
QWEN3_ENDPOINT = os.getenv('QWEN3_ENDPOINT')
QWEN3_ENDPOINT_CHAT = os.getenv('QWEN3_ENDPOINT_CHAT')


@router.post("/using_rag_system")
def using_rag_system_reg_organizations(file_urls_json: FileURLsRag):
    Pathes = "./database/vectorstore_glasshub/regulator/organization"

    try:
        # ✅ Validate input
        if not file_urls_json:
            logger.exception("file_urls is required")
            raise HTTPException(status_code=400, detail="file_urls is required")

        file_urls = file_urls_json.urls
        logger.info(f"The URLs are {file_urls}")

        # 🧠 Ingest knowledge from files
        download_files_from_cloud_storage(json_data=file_urls, download_dir=Pathes)
        logger.info("📥 Files are downloaded and processed successfully.")

        return {
            "message": "RAG system created and files processed.",
            "success": True
        }

    except Exception as e:
        logger.exception("❌ Failed to download or process files.")
        return {
            "message": f"Failed to download or process files: {str(e)}.",
            "success": False
        }


# For RAG System
@router.post("/filter_terms", description="Search for relevant documents based on user input and company details")
async def filter_terms_reg_organizations(payload: FilterTermsRequestRegulator):
    logger.info("Semantic search initiated...")

    results = retrieve_relevant_knowledge_regulator(
        path_load="./database/vectorstore_glasshub/regulator/organization",
        license_type=payload.license_type,
        regulations=payload.regulations,
        k=payload.k,
    )

    if not results:
        raise HTTPException(status_code=404, detail="No documents found")

    js_clean_data = []
    for idx, result in enumerate(results):
        content = result.get("content", "")
        js = extract_json_from_text(content)

        if not js or not isinstance(js, list):
            logger.warning(f"Skipping result {idx}: no valid JSON array found.")
            continue

        # Loop over all elements in the JSON array
        for item in js:
            if isinstance(item, dict) and "parsed_response" in item:
                parsed = item["parsed_response"]
                if parsed:  # Only append non-empty lists
                    js_clean_data.extend(parsed)

    if not js_clean_data:
        raise HTTPException(status_code=404, detail="No valid parsed responses found")

    response = {"results": js_clean_data}
    return JSONResponse(content=response)






