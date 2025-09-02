from fastapi import FastAPI, HTTPException, Form, UploadFile, File
from pydantic import BaseModel
from chatbot import get_chatbot_response, remove_think_tags
import re
import os
from fastapi.middleware.cors import CORSMiddleware

# Initialize FastAPI app
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Hoặc thay "*" bằng danh sách các origin cụ thể
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Debug: print environment variables for keys
print("[DEBUG] GEMINI_API_KEY:", os.getenv("GEMINI_API_KEY"))
print("[DEBUG] MONGODB_URI:", os.getenv("MONGODB_URI"))
print("[DEBUG] CEREBRAS_API_KEY:", os.getenv("CEREBRAS_API_KEY"))

# Define response model
class ChatResponse(BaseModel):
    answer: str
    context: str
    chat_history: list[dict]

def minify_code(code: str) -> str:
    """Remove blank lines and comments from code."""
    # Remove single-line comments (// ...)
    code = re.sub(r'//.*', '', code)
    # Remove multi-line comments (/* ... */)
    code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
    # Remove blank lines
    code = '\n'.join([line for line in code.splitlines() if line.strip()])
    return code

@app.post("/api/chat", response_model=ChatResponse)
async def chat(
    question: str = Form(...),
    file: UploadFile = File(None)
):
    try:
        # Debug: print incoming question and file info
        print(f"[DEBUG] Received question: {question}")
        if file:
            print(f"[DEBUG] Received file: {file.filename}, size: {file.size if hasattr(file, 'size') else 'unknown'}")
        # Process file if provided
        file_content = None
        if file:
            if file.size > 5 * 1024:  # Limit file size to 5KB
                print("[DEBUG] File too large!")
                raise HTTPException(status_code=400, detail="File exceeds 5KB.")
            try:
                file_content = await file.read()
                file_content = file_content.decode("utf-8")
                file_content = minify_code(file_content)
                print(f"[DEBUG] Minified file content: {file_content[:100]}...")
            except UnicodeDecodeError:
                print("[DEBUG] File encoding not supported.")
                raise HTTPException(status_code=400, detail="File encoding not supported. Please upload a UTF-8 encoded file.")
            except Exception as e:
                print(f"[DEBUG] Could not read file: {e}")
                raise HTTPException(status_code=400, detail=f"Could not read file: {e}")

        # Combine question and file content if file is provided
        combined_input = question
        if file_content:
            combined_input += f"\n\n[Minified file content from {file.filename}:]\n{file_content}"
        print(f"[DEBUG] Combined input: {combined_input[:200]}...")

        # Get chatbot response
        answer, context, updated_chat_history = get_chatbot_response(
            question=combined_input
        )
        # Remove <think> tags from the answer
        answer = remove_think_tags(answer)
        print(f"[DEBUG] Chatbot answer: {answer[:200]}...")
        return ChatResponse(
            answer=answer, context=context, chat_history=updated_chat_history
        )
    except HTTPException as e:
        print(f"[DEBUG] HTTPException: {e.detail}")
        raise e
    except Exception as e:
        print(f"[DEBUG] Internal Server Error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {e}")

@app.get("/health")
async def health_check():
    return {"status": "ok"}