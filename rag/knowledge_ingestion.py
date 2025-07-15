import os
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import UnstructuredFileLoader  # Support for DOCX

def create_path_directory(path: str) -> str:
    directory = os.path.join(os.getcwd(), path)
    os.makedirs(directory, exist_ok=True)
    return directory

# Directory where your uploaded DOCX files are stored
DOCX_DIRECTORY = create_path_directory("./database/glasshub_files")
VECTORSTORE_DIRECTORY = create_path_directory("./database/vectorstore_glasshub")

# Step 1: Load all DOCX files
def load_documents():
    documents = []
    for filename in os.listdir(DOCX_DIRECTORY):
        if filename.endswith(".docx"):
            file_path = os.path.join(DOCX_DIRECTORY, filename)
            loader = UnstructuredFileLoader(file_path)
            docs = loader.load()

            # إضافة اسم الملف إلى metadata
            for doc in docs:
                doc.metadata["source"] = filename

            documents.extend(docs)
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
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    db = FAISS.from_documents(chunks, embeddings)
    return db

# Step 4: Save the vector database
def save_vectorstore(db):
    if not os.path.exists(VECTORSTORE_DIRECTORY):
        os.makedirs(VECTORSTORE_DIRECTORY)
    db.save_local(VECTORSTORE_DIRECTORY)

# Main function to ingest knowledge
def ingest_company_knowledge():
    print("📚 Loading documents...")
    documents = load_documents()
    print(f"✅ Loaded {len(documents)} documents.")

    print("✂️ Splitting into chunks...")
    chunks = split_documents(documents)
    print(f"✅ Split into {len(chunks)} chunks.")

    print("🧠 Embedding chunks...")
    db = embed_documents(chunks)

    print("💾 Saving vector database...")
    save_vectorstore(db)

    print("🚀 Knowledge ingestion completed!")

# Run when script is executed
if __name__ == "__main__":
    ingest_company_knowledge()
