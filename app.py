from fastapi import FastAPI, HTTPException, Form, UploadFile, File
from pydantic import BaseModel
from chatbot import get_chatbot_response, remove_think_tags
import re

# Initialize FastAPI app
app = FastAPI()

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
        # Process file if provided
        file_content = None
        if file:
            if file.size > 5 * 1024:  # Limit file size to 5KB
                raise HTTPException(status_code=400, detail="File exceeds 5KB.")
            try:
                file_content = await file.read()
                file_content = file_content.decode("utf-8")
                file_content = minify_code(file_content)
            except UnicodeDecodeError:
                raise HTTPException(status_code=400, detail="File encoding not supported. Please upload a UTF-8 encoded file.")
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Could not read file: {e}")

        # Combine question and file content if file is provided
        combined_input = question
        if file_content:
            combined_input += f"\n\n[Minified file content from {file.filename}:]\n{file_content}"

        # Get chatbot response
        answer, context, updated_chat_history = get_chatbot_response(
            question=combined_input
        )
        # Remove <think> tags from the answer
        answer = remove_think_tags(answer)
        return ChatResponse(
            answer=answer, context=context, chat_history=updated_chat_history
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {e}")

@app.get("/health")
async def health_check():
    return {"status": "ok"}