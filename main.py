from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI, UploadFile, File, HTTPException, Request, Depends, status
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from typing import Annotated
import uvicorn
from datetime import timedelta

from models import ChatRequest, ChatResponse, FileUploadResponse
from parsers import parse_csv, parse_pdf
from vdb import store_transactions_in_vdb, clear_vdb_for_user
from ai_service import chat_with_granite
from auth import (
    create_access_token, 
    get_current_user_id,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    oauth,
    SECRET_KEY
)

app = FastAPI(title="Personal Finance Assistant API")

# Add SessionMiddleware for OAuth state
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

# Setup static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/")
def serve_dashboard(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# --- GitHub Auth Endpoints (Stateless) ---

@app.get("/login/github")
async def login_github(request: Request):
    redirect_uri = request.url_for('auth_github_callback')
    return await oauth.github.authorize_redirect(request, str(redirect_uri))

@app.get("/auth/callback/github")
async def auth_github_callback(request: Request):
    token = await oauth.github.authorize_access_token(request)
    resp = await oauth.github.get('user', token=token)
    profile = resp.json()
    
    github_id = str(profile.get('id'))
    username = profile.get('login')
    
    # Issue JWT with GitHub ID as the 'sub' (subject)
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": github_id}, expires_delta=access_token_expires
    )
    
    return templates.TemplateResponse("auth_success.html", {
        "request": request,
        "token": access_token,
        "username": username
    })

# --- Protected Data Endpoints ---

@app.post("/clear")
async def clear_data(current_user_id: Annotated[str, Depends(get_current_user_id)]):
    success = clear_vdb_for_user(current_user_id)
    if success:
        return {"status": "success", "message": "Your transaction data has been deleted."}
    raise HTTPException(status_code=500, detail="Failed to clear your data.")

@app.post("/upload/file", response_model=FileUploadResponse)
async def upload_file(
    current_user_id: Annotated[str, Depends(get_current_user_id)],
    file: UploadFile = File(...)
):
    content = await file.read()
    filename = file.filename.lower()
    
    transactions = []
    
    try:
        if filename.endswith(".csv"):
             transactions = parse_csv(content)
        elif filename.endswith(".pdf"):
             transactions = parse_pdf(content)
        else:
             raise HTTPException(status_code=400, detail="Unsupported format. Use CSV or PDF.")
             
        if not transactions:
            return FileUploadResponse(status="success", message="No transactions found.", num_transactions=0)
            
        # Tag transactions with current user's GitHub ID
        for tx in transactions:
            tx.user_id = current_user_id
            
        store_transactions_in_vdb(transactions)
        
        return FileUploadResponse(
            status="success",
            message=f"Stored {len(transactions)} transactions.",
            num_transactions=len(transactions)
        )
    except Exception as e:
         raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user_id: Annotated[str, Depends(get_current_user_id)]
):
    try:
        reply_text, updated_history = await chat_with_granite(request.messages, current_user_id)
        return ChatResponse(reply=reply_text, history=updated_history)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=7356, reload=True)
