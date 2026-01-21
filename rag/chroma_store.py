import chromadb

chroma_client = chromadb.Client()

def get_company_collection(company: str):
    return chroma_client.get_or_create_collection(
        name=f"{company.lower()}_collection"
    )
