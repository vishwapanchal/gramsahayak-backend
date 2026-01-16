import os
from dotenv import load_dotenv
from typing import List

from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings, HuggingFaceEndpoint
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from app.database import db

# ==================================================
# Environment & Constants
# ==================================================
load_dotenv()

HF_TOKEN = os.getenv("HUGGINGFACEHUB_API_TOKEN")
VECTOR_DB_PATH = "./chroma_db"

if not HF_TOKEN:
    raise RuntimeError("❌ HUGGINGFACEHUB_API_TOKEN not set in .env")

# ==================================================
# Embeddings (Local – Free Tier)
# ==================================================
print("📥 Loading embedding model...")
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

# ==================================================
# LLM Configuration (HF Router)
# ==================================================
PRIMARY_MODEL = "google/gemma-2-9b-it"
FALLBACK_MODELS: List[str] = [
    "mistralai/Mistral-7B-Instruct-v0.2",
    "HuggingFaceH4/zephyr-7b-beta"
]

_llm_instance = None  # private singleton


def _router_url(model_id: str) -> str:
    return f"https://router.huggingface.co/hf-inference/models/{model_id}"


def _build_llm(model_id: str) -> HuggingFaceEndpoint:
    print(f"🤖 Initializing LLM via HF Router → {model_id}")
    return HuggingFaceEndpoint(
        endpoint_url=_router_url(model_id),
        task="text-generation",
        max_new_tokens=512,
        temperature=0.2,
        do_sample=False,
        repetition_penalty=1.05,
        huggingfacehub_api_token=HF_TOKEN
    )


def get_llm() -> HuggingFaceEndpoint:
    """
    Singleton-safe LLM loader.
    Tries primary model first, then fallbacks.
    """
    global _llm_instance

    if _llm_instance is not None:
        return _llm_instance

    try:
        _llm_instance = _build_llm(PRIMARY_MODEL)
        return _llm_instance
    except Exception as e:
        print(f"⚠️ Primary model failed: {e}")

    for model in FALLBACK_MODELS:
        try:
            _llm_instance = _build_llm(model)
            return _llm_instance
        except Exception as e:
            print(f"⚠️ Fallback model failed ({model}): {e}")

    raise RuntimeError("❌ No Hugging Face models available")


# ==================================================
# MongoDB → ChromaDB Sync
# ==================================================
async def sync_discussions_to_vector_db():
    print("🔄 Syncing MongoDB discussions to ChromaDB...")

    discussions = await db.discussions.find({}).to_list(1000)
    if not discussions:
        return {"message": "No discussions found."}

    texts = []
    metadatas = []

    for d in discussions:
        content = d.get("content", "").strip()
        if not content:
            continue

        texts.append(
            f"Category: {d.get('category', 'General')}. "
            f"Village: {d.get('village_name', 'Unknown')}. "
            f"Content: {content}. "
            f"Upvotes: {d.get('upvotes', 0)}."
        )

        metadatas.append({
            "discussion_id": str(d["_id"]),
            "village": d.get("village_name", "Unknown")
        })

    if not texts:
        return {"message": "No valid content to index."}

    vector_db = Chroma.from_texts(
        texts=texts,
        embedding=embeddings,
        metadatas=metadatas,
        persist_directory=VECTOR_DB_PATH
    )
    vector_db.persist()

    return {"message": f"✅ Indexed {len(texts)} discussions."}


# ==================================================
# RAG Query
# ==================================================
async def generate_smart_summary(query: str) -> str:
    try:
        llm = get_llm()

        vector_db = Chroma(
            persist_directory=VECTOR_DB_PATH,
            embedding_function=embeddings
        )

        retriever = vector_db.as_retriever(search_kwargs={"k": 5})

        prompt = PromptTemplate(
            input_variables=["context", "question"],
            template="""
You are an AI assistant for a Village Panchayat system.

Use ONLY the information in the context below.
If the answer is not present, say:
"I don't have enough information."

Context:
{context}

Question:
{question}

Answer (concise, bullet points if useful):
"""
        )

        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=retriever,
            chain_type_kwargs={"prompt": prompt}
        )

        result = qa_chain.invoke({"query": query})
        return result.get("result", "No response generated.")

    except Exception as e:
        return f"❌ RAG Error: {str(e)}"
