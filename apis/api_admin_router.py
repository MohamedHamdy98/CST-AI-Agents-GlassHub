import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from fastapi import APIRouter, HTTPException
import logging
from utils.schemas import FileURLs
from dotenv import load_dotenv
from rag.knowledge_ingestion import ingest_company_knowledge

# Load environment variables from .env file
load_dotenv()

# Logger setup
logger = logging.getLogger("report_router")
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
handler.stream.reconfigure(encoding='utf-8')  
logger.addHandler(handler)
logger.setLevel(logging.INFO)

router = APIRouter(prefix="/api/v1", tags=["admin"])


# Alibaba cloud Connection
ACCESS_KEY_ID = os.getenv("OSS_ACCESS_KEY_ID")
ACCESS_KEY_SECRET = os.getenv("OSS_ACCESS_KEY_SECRET")
ENDPOINT = os.getenv("OSS_ENDPOINT")
BUCKET_NAME = os.getenv("OSS_BUCKET")


# Qwen3 LLM Endpoint
QWEN3_ENDPOINT = os.getenv('QWEN3_ENDPOINT')
QWEN3_ENDPOINT_CHAT = os.getenv('QWEN3_ENDPOINT_CHAT')


# For RAG System
@router.post("/create_rag_system")
def create_rag_system(file_urls_json: FileURLs):
    """
    Endpoint to create a Retrieval-Augmented Generation (RAG) system using provided document URLs.

    This endpoint accepts a list of document URLs, downloads and processes them to ingest knowledge 
    into the system, and then cleans up temporary files.

    Args:
        file_urls_json (FileURLs): A Pydantic model containing a list of document URLs to process.

    Returns:
        dict: A response indicating whether the operation succeeded, along with a descriptive message.

    Raises:
        HTTPException: If the input is invalid or an error occurs during file processing.
    """

    DOCX_DIRECTORY = "./database/glasshub_files"

    try:
        # ✅ Validate input
        if not file_urls_json:
            logger.exception("file_urls is required")
            raise HTTPException(status_code=400, detail="file_urls is required")

        file_urls = file_urls_json.urls
        logger.info(f"The URLs are {file_urls}")

        # 🧠 Ingest knowledge from files
        ingest_company_knowledge(file_urls)
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

    finally:
        # 🧹 Clean up temporary .docx files from local storage
        try:
            for file in os.listdir(DOCX_DIRECTORY):
                if file.endswith(".docx"):
                    full_path = os.path.join(DOCX_DIRECTORY, file)
                    if os.path.exists(full_path):
                        os.remove(full_path)
                        logger.info(f"🧹 Deleted temp file: {full_path}")
        except Exception as cleanup_err:
            logger.warning(f"⚠️ Cleanup failed: {cleanup_err}")

