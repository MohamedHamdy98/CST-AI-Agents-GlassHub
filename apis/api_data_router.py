import os, sys, json
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from fastapi import APIRouter, Form, HTTPException, UploadFile, File
import logging
from fastapi.responses import JSONResponse
# from utils.dynamic_controls import generate_compliance_prompt, save_control_prompt, merge_all_controls
from utils.schemas import ControlsRequest, FileURLsRag
from utils.helper_functions import (extract_clauses_with_system_message, extract_json_objects, flatten_clauses, init_oss_bucket)
from dotenv import load_dotenv
from utils.create_instructions import process_parsed_response
from rag.knowledge_retriever import retrieve_relevant_knowledge
from rag.knowledge_ingestion import ingest_company_knowledge, download_files_from_cloud_storage


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
def using_rag_system(file_urls_json: FileURLsRag):
    """ 
    You can use this all time:
    {
        "urls":
        [
            "https://glasshub-files-staging.oss-me-central-1.aliyuncs.com/cst_rag/index.faiss",
            "https://glasshub-files-staging.oss-me-central-1.aliyuncs.com/cst_rag/index.pkl"
        ]
    }
    """
    Pathes = "./database/vectorstore_glasshub/"

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
        return JSONResponse(content=results)
        # # convert the result to json
        # content = results[0]['content']
        # source = results[0]['source']
        # page = results[0].get('page', "Page not specified")
        # json_blocks = extract_json_objects(content)

        # data_js = []
        # for block in json_blocks:
        #     try:
        #         data_js.append(json.loads(block))
        #     except Exception as e:
        #         print("Error loading block:", e)

        # flattened = flatten_clauses(data_js, source, page)

        # terms = extract_clauses_with_system_message(QWEN3_ENDPOINT_CHAT, flattened, 6000, False)
        # terms = terms.get('response')

        # print("Json Terms:", terms)
        # print("Type of Terms:", type(terms))

        # terms_dict = json.loads(terms)
        # flattened_terms = terms_dict["flattened"]
        # print("Type of flattened_terms:", type(flattened_terms))
        # parsed_response = [item for item in flattened_terms if len(item.get("description", "")) >= 50]

        # # json_parsed_response = dict(parsed_response)
        # # filtered_terms = filter_terms_js(terms)
        # json_parsed_response = process_parsed_response(parsed_response)
        # logger.info(json_parsed_response)
        # return {
        #     "parsed_response": json_parsed_response
        #     }

    except Exception as e:
        logger.exception("Semantic search failed.")
        raise HTTPException(status_code=500, detail=str(e))





