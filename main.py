from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import your logging utility
from utils.logs import setup_logger

# Set up logger for this module
logger = logger = setup_logger(__name__)
print(f"🔥 DEBUG: Module {__name__} logger setup complete!")

# Import routers
from apis.regulator.organizations.api_main_process_router import router as main_process_reg_org
from apis.regulator.organizations.api_admin_router import router as admin_reg_org
from apis.regulator.organizations.api_chat_router import router as chat_reg_org
from apis.regulator.organizations.api_data_router import router as data_reg_org

from apis.regulator.licenses.api_main_process_router import router as main_process_reg_lic
from apis.regulator.licenses.api_admin_router import router as admin_reg_lic
from apis.regulator.licenses.api_chat_router import router as chat_reg_lic
from apis.regulator.licenses.api_data_router import router as data_reg_lic

from apis.enterprise.organizations.api_main_process_router import router as main_process_enterprise_org
from apis.enterprise.organizations.api_admin_router import router as admin_enterprise_org
from apis.enterprise.organizations.api_chat_router import router as chat_enterprise_org
from apis.enterprise.organizations.api_data_router import router as data_enterprise_org

from apis.enterprise.licenses.api_main_process_router import router as main_process_enterprise_lic
from apis.enterprise.licenses.api_admin_router import router as admin_enterprise_lic
from apis.enterprise.licenses.api_chat_router import router as chat_enterprise_lic
from apis.enterprise.licenses.api_data_router import router as data_enterprise_lic

from rag.knowledge_retriever import load_vectorstore

# Global variables - Dictionary to store multiple vector stores
vector_stores = {
    "regulator_organizations": None,
    "regulator_licenses": None,
    "enterprise_organizations": None,
    "enterprise_licenses": None
}

# Vector store paths configuration
VECTOR_STORE_PATHS = {
    "regulator_organizations": "./database/vectorstore_glasshub/regulator/organization",
    "regulator_licenses": "./database/vectorstore_glasshub/regulator/licenses", 
    "enterprise_organizations": "./database/vectorstore_glasshub/enterprise/organization",
    "enterprise_licenses": "./database/vectorstore_glasshub/enterprise/licenses"
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global vector_stores
    
    logger.info("🚀 Starting up GlassHub Agent...")
    logger.info("⏳ Loading Vector Stores at startup...")
    
    loaded_count = 0
    failed_count = 0
    
    for store_name, path in VECTOR_STORE_PATHS.items():
        try:
            logger.info(f"📂 Loading {store_name} from {path}...")
            vector_stores[store_name] = load_vectorstore(path_load=path)
            
            if vector_stores[store_name]:
                logger.info(f"✅ {store_name} loaded successfully!")
                print(f"✅ {store_name} loaded successfully!")
                loaded_count += 1
            else:
                logger.warning(f"⚠️ {store_name} not found at {path}")
                print(f"⚠️ {store_name} not found at {path}")
                failed_count += 1
                
        except Exception as e:
            logger.error(f"❌ Failed to load {store_name}: {str(e)}")
            print(f"❌ Failed to load {store_name}: {str(e)}")
            vector_stores[store_name] = None
            failed_count += 1
    
    logger.info(f"📊 Vector Store Loading Summary: {loaded_count} loaded, {failed_count} failed")
    print(f"📊 Vector Store Loading Summary: {loaded_count} loaded, {failed_count} failed")

    yield  # Application is running
    
    # Shutdown
    logger.info("🛑 App shutting down...")
    print("🛑 App shutting down...")

# Create FastAPI app with lifespan
app = FastAPI(
    title="GlassHub Agent API",
    description="API for Enterprise and Regulator Compliance",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"], 
)

# Include routers - Regulator Organizations
app.include_router(admin_reg_org)
app.include_router(data_reg_org)
app.include_router(main_process_reg_org)
app.include_router(chat_reg_org)

# Include routers - Regulator Licenses
app.include_router(admin_reg_lic)
app.include_router(data_reg_lic)
app.include_router(main_process_reg_lic)
app.include_router(chat_reg_lic)

# Include routers - Enterprise Organizations
app.include_router(admin_enterprise_org)
app.include_router(data_enterprise_org)
app.include_router(main_process_enterprise_org)
app.include_router(chat_enterprise_org)

# Include routers - Enterprise Licenses
app.include_router(admin_enterprise_lic)
app.include_router(data_enterprise_lic)
app.include_router(main_process_enterprise_lic)
app.include_router(chat_enterprise_lic)

@app.get("/", tags=["Health"])
def home():
    """Welcome endpoint"""
    logger.info("Home endpoint accessed")
    
    # Count loaded vector stores
    loaded_stores = sum(1 for store in vector_stores.values() if store is not None)
    total_stores = len(vector_stores)
    
    return {
        "message": "Welcome to the GlassHub Agent for Enterprise and Regulator Compliance!",
        "status": "running",
        "vector_stores_loaded": f"{loaded_stores}/{total_stores}",
        "vector_stores_status": {
            name: "loaded" if store is not None else "not_loaded" 
            for name, store in vector_stores.items()
        }
    }

@app.get("/health", tags=["Health"])
def health_check():
    """Health check endpoint"""
    loaded_stores = sum(1 for store in vector_stores.values() if store is not None)
    total_stores = len(vector_stores)
    
    return {
        "status": "healthy",
        "vector_stores_loaded": f"{loaded_stores}/{total_stores}",
        "vector_stores_status": {
            name: "loaded" if store is not None else "not_loaded" 
            for name, store in vector_stores.items()
        }
    }

@app.get("/vector-stores/status", tags=["Vector Stores"])
def get_vector_stores_status():
    """Get detailed status of all vector stores"""
    status_details = {}
    
    for name, store in vector_stores.items():
        path = VECTOR_STORE_PATHS[name]
        status_details[name] = {
            "loaded": store is not None,
            "path": path,
            "path_exists": os.path.exists(path),
            "store_type": type(store).__name__ if store else None
        }
    
    loaded_count = sum(1 for details in status_details.values() if details["loaded"])
    
    return {
        "summary": {
            "total_stores": len(status_details),
            "loaded_stores": loaded_count,
            "failed_stores": len(status_details) - loaded_count
        },
        "details": status_details
    }

@app.get("/logs/list", tags=["Logging"])
def list_all_logs():
    """List all available log files"""
    log_dir = "./database/logs/"  # Your LOG_DIR from utils.logs
    
    if not os.path.exists(log_dir):
        return {"log_files": [], "message": "Log directory not found"}
    
    try:
        # Get all .log files in the directory
        log_files = []
        for file in os.listdir(log_dir):
            if file.endswith('.log'):
                file_path = os.path.join(log_dir, file)
                file_size = os.path.getsize(file_path)
                file_modified = os.path.getmtime(file_path)
                
                log_files.append({
                    "filename": file,
                    "path": file_path,
                    "size_bytes": file_size,
                    "last_modified": file_modified,
                    "readable_size": f"{file_size / 1024:.2f} KB" if file_size < 1024*1024 else f"{file_size / (1024*1024):.2f} MB"
                })
        
        # Sort by last modified (newest first)
        log_files.sort(key=lambda x: x["last_modified"], reverse=True)
        
        return {
            "log_files": log_files,
            "total_files": len(log_files),
            "log_directory": log_dir
        }
        
    except Exception as e:
        logger.error(f"Error listing log files: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error listing log files: {str(e)}")

@app.get("/logs/view", tags=["Logging"])
def view_specific_log(log_path: str):
    """
    View contents of a specific log file
    
    Args:
        log_path: Path to the log file (can be filename or full path)
        lines: Number of latest lines to return (optional, returns all if not specified)
    """
    log_dir = "./database/logs/"
    
    # If only filename is provided, construct full path
    if not log_path.startswith(log_dir) and not os.path.dirname(log_path):
        full_path = os.path.join(log_dir, log_path)
    else:
        full_path = log_path
    
    # Security check - ensure the path is within the logs directory
    full_path = os.path.abspath(full_path)
    log_dir_abs = os.path.abspath(log_dir)
    
    if not full_path.startswith(log_dir_abs):
        raise HTTPException(status_code=403, detail="Access denied: Path outside of logs directory")
    
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail=f"Log file not found: {full_path}")
    
    if not full_path.endswith('.log'):
        raise HTTPException(status_code=400, detail="Only .log files are allowed")
    
    try:
        with open(full_path, "r", encoding="utf-8") as f:
            log_content = f.readlines()

        file_info = {
            "filename": os.path.basename(full_path),
            "path": full_path,
            "size_bytes": os.path.getsize(full_path),
            "total_lines": len(log_content),
            "lines_returned": len(log_content)
        }
        
        return {
            "file_info": file_info,
            "logs": log_content
        }
        
    except Exception as e:
        logger.error(f"Error reading log file {full_path}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error reading log file: {str(e)}")

@app.delete("/logs/clear", tags=["Logging"])
def clear_specific_log(log_path: str):
    """
    Clear contents of a specific log file
    
    Args:
        log_path: Path to the log file (can be filename or full path)
    """
    log_dir = "./database/logs/"
    
    # If only filename is provided, construct full path
    if not log_path.startswith(log_dir) and not os.path.dirname(log_path):
        full_path = os.path.join(log_dir, log_path)
    else:
        full_path = log_path
    
    # Security check - ensure the path is within the logs directory
    full_path = os.path.abspath(full_path)
    log_dir_abs = os.path.abspath(log_dir)
    
    if not full_path.startswith(log_dir_abs):
        raise HTTPException(status_code=403, detail="Access denied: Path outside of logs directory")
    
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail=f"Log file not found: {full_path}")
    
    if not full_path.endswith('.log'):
        raise HTTPException(status_code=400, detail="Only .log files are allowed")
    
    try:
        with open(full_path, "w", encoding="utf-8") as f:
            f.truncate(0)
        
        logger.info(f"Log file cleared successfully: {full_path}")
        return {
            "message": "Log file cleared successfully",
            "file_path": full_path,
            "filename": os.path.basename(full_path)
        }
        
    except Exception as e:
        logger.error(f"Error clearing log file {full_path}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error clearing log file: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    logger.info("🚀 Starting GlassHub Agent server...")
    uvicorn.run(
        "main:app", 
        port=80, 
        host="0.0.0.0", 
        reload=True,
        log_level="info"
    )