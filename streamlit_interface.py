import os
# Disable GCP metadata service to prevent MongoDB driver from calling Google Compute metadata
os.environ['GCE_METADATA_HOST'] = ''
os.environ['GCE_METADATA_ROOT'] = ''
os.environ['DISABLE_GCE_METADATA_SERVICE'] = 'true'
import streamlit as st
from dotenv import load_dotenv
load_dotenv()
from chatbot import get_chatbot_response
import json
import re
import tiktoken

# Cấu hình trang
st.set_page_config(
    page_title="ReactJS Chatbot", 
    page_icon="",
    layout="wide"
)


# Khởi tạo session state
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "display_messages" not in st.session_state:
    st.session_state.display_messages = []

if "context_history" not in st.session_state:
    st.session_state.context_history = []


# Sidebar: model selection and clear history
with st.sidebar:
    st.header("Options")
    model = st.selectbox("Choose model", ["gpt-oss-120b", "llama-3.3-70b", "qwen-3-235b-a22b-instruct-2507"],  index=0)
    if st.button("Clear chat history"):
        st.session_state.chat_history = []
        st.session_state.display_messages = []
        st.session_state.context_history = []
        st.session_state.pop("uploaded_file", None)
        st.session_state.pop("file_content", None)
        st.rerun()

# English UI for chat
st.title(" ReactJS Chatbot")

# Show chat history (scrollable)
with st.container():
    for msg in st.session_state.display_messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

def minify_code(code: str, filetype: str) -> str:
    """Remove blank lines and comments from code (supports js/ts/tsx/jsx/css/html)."""
    # Remove single-line comments (// ...)
    code = re.sub(r'//.*', '', code)
    # Remove multi-line comments (/* ... */)
    code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
    # Remove blank lines
    code = '\n'.join([line for line in code.splitlines() if line.strip()])
    return code

def count_tokens(text: str, model_name: str = "gpt-3.5-turbo") -> int:
    try:
        enc = tiktoken.encoding_for_model(model_name)
    except Exception:
        enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text))

def local_debug_token_count(answer, model_name="gpt-3.5-turbo"):
    token_count = count_tokens(answer, model_name)
    # st.info(f"[Local debug] Answer tokens: {token_count}")

# File upload
with st.container():
    uploaded_file = st.file_uploader(
        "Upload FE file (js, ts, tsx, jsx, css, html) - max 5KB:",
        type=["js", "ts", "tsx", "jsx", "css", "html"],
        key="file_upload"
    )

# --- Cố định uploader ở góc trên trái ---
st.markdown(
    """
    <style>
    .fixed-uploader {
        position: fixed;
        top: 10px;
        left: 10px;
        z-index: 999;
        background: white;
        padding: 10px;
        border-radius: 5px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    </style>
    <div class="fixed-uploader">
    </div>
    """,
    unsafe_allow_html=True
)

file_content = None
minified_content = None
file_token_count = 0
minified_token_count = 0
if uploaded_file is not None:
    if uploaded_file.size > 5 * 1024:
        st.error("File exceeds 5KB.")
    else:
        try:
            file_content = uploaded_file.getvalue().decode("utf-8")
        except UnicodeDecodeError:
            st.error("File encoding not supported. Please upload a UTF-8 encoded file.")
            file_content = None
        except Exception as e:
            st.error(f"Could not read file: {e}")
            file_content = None
        if file_content is not None:
            minified_content = minify_code(file_content, "")
            file_token_count = count_tokens(file_content)
            minified_token_count = count_tokens(minified_content)
            st.info(f"[Local debug] File tokens: {file_token_count}, Minified tokens: {minified_token_count}")

# Chat input fixed at bottom via default st.chat_input
user_input = st.chat_input("Ask about ReactJS or upload a file... (max 100 words)")
if user_input:
    if len(user_input.split()) > 100:
        st.error("Limit is 100 words.")
    else:
        combined_input = user_input
        if minified_content:
            combined_input += f"\n\n[Minified file content from {uploaded_file.name}:]\n{minified_content}"
        st.chat_message("user").write(user_input)
        with st.chat_message("assistant"):
            with st.spinner(" Generating answer..."):
                try:
                    answer, context_info, updated_chat_history = get_chatbot_response(
                        combined_input,
                        st.session_state.chat_history,
                        5,
                        model
                    )
                    st.write(answer)
                    # Local debug: show token count of answer
                    local_debug_token_count(answer, model_name=model)
                    # update history
                    st.session_state.chat_history = updated_chat_history
                    st.session_state.display_messages.extend([
                        {"role": "user", "content": user_input},
                        {"role": "assistant", "content": answer}
                    ])
                except Exception as e:
                    st.error(f"❌ Error: {e}")
    st.markdown("</div>", unsafe_allow_html=True)

