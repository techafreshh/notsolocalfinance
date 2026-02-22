import os
import uuid
import ollama
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from typing import List
from models import Transaction

# Connection to Qdrant Vector DB
QDRANT_HOST = os.environ.get("QDRANT_HOST", "qdrant")
QDRANT_PORT = int(os.environ.get("QDRANT_PORT", 6333))
COLLECTION_NAME = "transactions"

# Connection to Ollama for Embbendings
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://host.docker.internal:11434")
OLLAMA_EMBEDDING_MODEL = "nomic-embed-text-v2-moe"

# Initialization
try:
    ollama_client = ollama.Client(host=OLLAMA_HOST)
except Exception as e:
    print(f"Warning: Could not connect to Ollama during init: {e}")

try:
    qdrant_client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    
    # Ensure collection exists
    if not qdrant_client.collection_exists(collection_name=COLLECTION_NAME):
        qdrant_client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=768, distance=Distance.COSINE), # nomic-embed-text-v2-moe size is 768
        )
except Exception as e:
    print(f"Warning: Could not connect to Qdrant during init: {e}")

def get_embedding(text: str) -> List[float]:
    """Generate an embedding for the given text using Ollama."""
    try:
        response = ollama_client.embeddings(model=OLLAMA_EMBEDDING_MODEL, prompt=text)
        return response['embedding']
    except Exception as e:
        print(f"Error generating embedding: {e}")
        return []

def store_transactions_in_vdb(transactions: List[Transaction]):
    """Embed and store a list of transactions in Qdrant."""
    if not transactions:
        return
        
    points = []
    for tx in transactions:
        tx_string = tx.to_document_string()
        vector = get_embedding(tx_string)
        
        if not vector:
             continue
             
        points.append(PointStruct(
            id=str(uuid.uuid4()),
            vector=vector,
            payload=tx.model_dump()
        ))
        
        qdrant_client.upsert(
            collection_name=COLLECTION_NAME,
            points=points
        )

def clear_vdb():
    """Wipes all transactions from the vector database by recreating the collection."""
    try:
        qdrant_client.delete_collection(collection_name=COLLECTION_NAME)
        qdrant_client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=768, distance=Distance.COSINE),
        )
        return True
    except Exception as e:
        print(f"Failed to clear Qdrant collection: {e}")
        return False

def query_transactions(query: str, limit: int = 10) -> List[Transaction]:
    """Retrieve relevant transactions based on a semantic query."""
    query_vector = get_embedding(query)
    
    if not query_vector:
         return []
         
    search_result = qdrant_client.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_vector,
        limit=limit
    )
    
    return [Transaction(**hit.payload) for hit in search_result]

def get_all_transactions() -> List[Transaction]:
    """A helper to fetch all stored transactions (up to a limit) for pure analytical tools."""
    try:
        results, next_page = qdrant_client.scroll(
            collection_name=COLLECTION_NAME,
            limit=1000 # Reasonable limit for a personal statement
        )
        return [Transaction(**hit.payload) for hit in results]
    except Exception:
         return []
