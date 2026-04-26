from dotenv import load_dotenv
load_dotenv()
import os
import uuid
from typing import List, Optional
from qdrant_client import QdrantClient, models
from models import Transaction

# Connection to Qdrant Vector DB
QDRANT_HOST = os.environ.get("QDRANT_HOST", "http://localhost")
QDRANT_PORT = int(os.environ.get("QDRANT_PORT", 6333))
COLLECTION_NAME = "finance_v2" # Using a fresh name

# Initialize Qdrant client
print(f"DEBUG: Connecting to Qdrant at {QDRANT_HOST}:{QDRANT_PORT}...")
try:
    if QDRANT_HOST.startswith(("http://", "https://")):
        url = f"{QDRANT_HOST}:{QDRANT_PORT}" if ":" not in QDRANT_HOST[8:] else QDRANT_HOST
        qdrant_client = QdrantClient(url=url, timeout=60)
    else:
        qdrant_client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT, timeout=60)
    
    # Test connection
    qdrant_client.get_collections()
    print("DEBUG: Successfully connected to Qdrant.")
except Exception as e:
    print(f"CRITICAL: Could not connect to Qdrant: {e}")
    qdrant_client = None


def store_transactions_in_vdb(transactions: List[Transaction]):
    """
    Store transactions in Qdrant using the high-level .add() method.
    """
    if not transactions:
        print("DEBUG: No transactions to store.")
        return
    if qdrant_client is None:
        print("DEBUG: Cannot store - qdrant_client is None!")
        return

    print(f"DEBUG: Beginning storage of {len(transactions)} transactions...")
    documents = [tx.to_document_string() for tx in transactions]
    metadatas = [tx.model_dump() for tx in transactions]
    ids = [str(uuid.uuid4()) for _ in transactions]

    try:
        print(f"DEBUG: Running qdrant_client.add() (parallel=0)...")
        qdrant_client.add(
            collection_name=COLLECTION_NAME,
            documents=documents,
            metadata=metadatas,
            ids=ids,
            parallel=0
        )
        print(f"✅ SUCCESS: Stored {len(transactions)} transactions in '{COLLECTION_NAME}'")
    except Exception as e:
        print(f"❌ ERROR in store_transactions_in_vdb: {e}")


def clear_vdb_for_user(user_id: str):
    """Wipes transactions belonging to a specific user."""
    if qdrant_client is None:
        return False

    try:
        qdrant_client.delete(
            collection_name=COLLECTION_NAME,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="user_id",
                            match=models.MatchValue(value=user_id),
                        )
                    ]
                )
            ),
        )
        print(f"Deleted transactions for user: {user_id}")
        return True
    except Exception as e:
        print(f"Failed to clear user transactions: {e}")
        return False


def query_transactions(query: str, user_id: str, limit: int = None) -> List[Transaction]:
    """
    Retrieve relevant transactions for a specific user.
    """
    if qdrant_client is None:
        return []

    search_limit = limit if limit is not None else 1000

    try:
        results = qdrant_client.query(
            collection_name=COLLECTION_NAME,
            query_text=query,
            query_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="user_id",
                        match=models.MatchValue(value=user_id),
                    )
                ]
            ),
            limit=search_limit
        )
        
        # Note: metadata has the model_dump data from the Transaction object
        return [Transaction(**res.metadata) for res in results]
    except Exception as e:
        print(f"Error querying Qdrant: {e}")
        return []


def get_all_transactions_for_user(user_id: str) -> List[Transaction]:
    """Fetch all stored transactions for a specific user."""
    if qdrant_client is None:
        return []

    try:
        # Use scroll to get all points (with the filter)
        results, next_page = qdrant_client.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="user_id",
                        match=models.MatchValue(value=user_id),
                    )
                ]
            ),
            limit=1000
        )
        # .payload is used for scroll results
        return [Transaction(**hit.payload) for hit in results]
    except Exception as e:
        print(f"Error fetching transactions for user {user_id}: {e}")
        return []
