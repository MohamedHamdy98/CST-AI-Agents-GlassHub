from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from langchain.vectorstores import FAISS
from apis.api_main_process_router import router as main_process
from apis.api_admin_router import router as admin
from apis.api_chat_router import router as chat
from apis.api_data_router import router as data
import logging
from logging.handlers import RotatingFileHandler
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rag.knowledge_retriever import load_vectorstore

# Create logs directory
os.makedirs("./database/logs", exist_ok=True)

vector_db = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global vector_db
    print("⏳ Loading Vector DB at startup...")
    
    vector_db = load_vectorstore()
    
    if vector_db:
        print("✅ Vector DB loaded successfully!")
    else:
        print("⚠️ Vector DB not found")

    yield  # app is running

    print("🛑 App shutting down...")

app = FastAPI(lifespan=lifespan)

# Configure logging
log_file = "./database/logs/app.log"
handler = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=3)  # 5MB logs
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
handler.setFormatter(formatter)

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.addHandler(handler)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"], 
)

# Include router
app.include_router(admin)
app.include_router(data)
app.include_router(main_process)
app.include_router(chat)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", port=80, host="0.0.0.0", reload=True)
