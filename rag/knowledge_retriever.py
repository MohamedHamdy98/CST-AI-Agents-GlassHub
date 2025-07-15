import os
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings


def create_path_directory(path: str) -> str:
    directory = os.path.join(os.getcwd(), path)
    os.makedirs(directory, exist_ok=True)
    return directory

VECTORSTORE_DIRECTORY = create_path_directory("./database/vectorstore_glasshub")


# Step 1: Load the FAISS vectorstore
def load_vectorstore():
    if not os.path.isdir(VECTORSTORE_DIRECTORY):
        raise FileNotFoundError(
            f"❌ Vectorstore directory '{VECTORSTORE_DIRECTORY}' not found.\n"
            "💡 Please run the ingestion script to generate the vector store."
        )
    
    print("📦 Loading vectorstore...")
    # sentence-transformers/all-MiniLM-L6-v2
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    
    db = FAISS.load_local(
        VECTORSTORE_DIRECTORY,
        embeddings,
        allow_dangerous_deserialization=True  # Needed if pickle was used during save
    )
    print("✅ Vectorstore loaded successfully.")
    return db


# Step 2: Retrieve top-k most relevant documents
def retrieve_relevant_knowledge(
    user_question: str = "",
    is_licensed: str = "",
    license_type: str = "",
    service_type: str = "",
    regulations: str = "",
    k: int = 10
):
    db = load_vectorstore()

    # بناء الاستعلام الموسّع من إجابات المستخدم
    enriched_query = f"""
    استعلام المستخدم: {user_question}
    هل الرخصة مرخصة؟ → {is_licensed}
    نوع الترخيص → {license_type}
    نوع الخدمة → {service_type}
    التنظيمات → {regulations}
    """

    # البحث في قاعدة المعرفة (FAISS)
    results = db.similarity_search(enriched_query.strip(), k=k)

    # ربط كل نتيجة باسم المصدر
    formatted_results = []
    for doc in results:
        source = doc.metadata.get("source", "📄 ملف غير معروف")
        content = doc.page_content.strip()
        formatted_results.append(f"📄 **من الملف:** {source}\n{content}")

    return "\n\n".join(formatted_results)




# For CLI Testing
if __name__ == "__main__":
    print("🔎 Welcome to the VMinds Knowledge Retriever!")
    while True:
        question = input("\n❓ Enter your question (or type 'exit' to quit):\n> ")
        if question.strip().lower() == 'exit':
            print("👋 Exiting.")
            break
        try:
            knowledge = retrieve_relevant_knowledge(question)
            if knowledge.strip():
                print("\n📚 Retrieved Knowledge:")
                print(knowledge)
            else:
                print("⚠️ No relevant knowledge found.")
        except Exception as e:
            print(f"❌ Error: {e}")
