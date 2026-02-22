from pydantic import BaseModel, Field
from typing import List, Optional, Any
from datetime import date

class Transaction(BaseModel):
    date: str = Field(..., description="The date of the transaction (YYYY-MM-DD or equivalent)")
    description: str = Field(..., description="Description of the transaction")
    amount: float = Field(..., description="The amount of the transaction. Positive for income, negative for expenses.")
    category: Optional[str] = Field(default="Uncategorized", description="Category of the transaction")
    
    # We store the raw text to be easily embedded and passed to the LLM
    def to_document_string(self) -> str:
        return f"Date: {self.date}, Description: {self.description}, Amount: ₦{self.amount:.2f}, Category: {self.category}"

class ToolCallRequest(BaseModel):
    name: str
    arguments: dict[str, Any]

class ChatRequest(BaseModel):
    messages: List[dict] = Field(..., description="List of discussion messages, where each message has a 'role' and 'content'")

class FileUploadResponse(BaseModel):
    status: str
    message: str
    num_transactions: int

class ChatResponse(BaseModel):
    reply: str
    history: Optional[List[dict]] = None
