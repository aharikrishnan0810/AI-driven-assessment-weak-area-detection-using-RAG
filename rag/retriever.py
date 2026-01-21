from rag.embedder import embed_texts
from rag.chroma_store import get_company_collection

def retrieve_context(company: str, query: str, k: int = 5):
    collection = get_company_collection(company)
    query_embedding = embed_texts([query])[0]

    result = collection.query(
        query_embeddings=[query_embedding],
        n_results=k
    )

    return result["documents"][0]
