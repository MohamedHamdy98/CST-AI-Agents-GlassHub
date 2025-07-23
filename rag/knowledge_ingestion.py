import os
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import UnstructuredFileLoader  
from utils.helper_functions import download_from_alibaba_oss, download_from_url
from dotenv import load_dotenv
from typing import List
import urllib.parse
# Load environment variables from .env file
load_dotenv()

def create_path_directory(path: str) -> str:
    directory = os.path.join(os.getcwd(), path)
    os.makedirs(directory, exist_ok=True)
    return directory

# Directory where your uploaded DOCX files are stored
DOCX_DIRECTORY = create_path_directory("./database/glasshub_files")
VECTORSTORE_DIRECTORY = create_path_directory("./database/vectorstore_glasshub")

# PDF_DIRECTORY = create_path_directory("./database/glasshub_files")

# Download files from cloud storage
# def download_files_from_cloud_storage(urls):
#     for url in urls:
#         filename = os.path.basename(url.split("?")[0])
#         local_path = os.path.join("./database/glasshub_files", filename)
#         download_from_alibaba_oss(url, local_path)

def download_files_from_cloud_storage(json_data: List[str], download_dir="./database/glasshub_files"):
    os.makedirs(download_dir, exist_ok=True)

    for url in json_data:
        filename = urllib.parse.unquote(os.path.basename(url))
        local_path = os.path.join(download_dir, filename)
        download_from_url(url, local_path)

# Step 1: Load all DOCX files
def load_documents():
    documents = []
    for filename in os.listdir(DOCX_DIRECTORY):
        if filename.endswith(".docx"):
            file_path = os.path.join(DOCX_DIRECTORY, filename)
            loader = UnstructuredFileLoader(file_path)
            pages = loader.load()

            for i, doc in enumerate(pages):
                doc.metadata["source"] = filename
                doc.metadata["page_number"] = i + 1
                documents.append(doc)
    return documents


# Step 2: Split documents into chunks
def split_documents(documents):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )
    return splitter.split_documents(documents)

# Step 3: Embed documents sentence-transformers/all-MiniLM-L6-v2
def embed_documents(chunks):
    print("Chunks:", chunks)
    print("Number of chunks:", len(chunks))
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    db = FAISS.from_documents(chunks, embeddings)
    return db

# Step 4: Save the vector database
def save_vectorstore(db):
    if not os.path.exists(VECTORSTORE_DIRECTORY):
        os.makedirs(VECTORSTORE_DIRECTORY)
    db.save_local(VECTORSTORE_DIRECTORY)

# Main function to ingest knowledge
def ingest_company_knowledge(url):
    print("Download all files for RAG System from cloud storage...")
    download_files_from_cloud_storage(url)
    print(f"✅ Files downloaded.")

    print("📚 Loading documents...")
    documents = load_documents()
    print(f"✅ Loaded {len(documents)} documents.")

    print("✂️ Splitting into chunks...")
    chunks = split_documents(documents)
    print(f"✅ Split into {len(chunks)} chunks.")

    print("🧠 Embedding chunks...")
    db = embed_documents(documents)

    print("💾 Saving vector database...")
    save_vectorstore(db)

    print("🚀 Knowledge ingestion completed!")

    

# Run when script is executed
if __name__ == "__main__":
    ingest_company_knowledge()
