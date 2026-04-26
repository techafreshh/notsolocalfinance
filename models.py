from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Any
from datetime import date

class User(BaseModel):
    id: str  # GitHub ID or local unique ID
    username: str
    email: Optional[EmailStr] = None
    avatar_url: Optional[str] = None

class Token(BaseModel):
    access_token: str
    token_type: str

class Transaction(BaseModel):
    user_id: Optional[str] = Field(default=None, description="The ID of the user who owns this transaction")
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
