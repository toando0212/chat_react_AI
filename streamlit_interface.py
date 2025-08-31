import os
# Disable GCP metadata service to prevent MongoDB driver from calling Google Compute metadata
os.environ['GCE_METADATA_HOST'] = ''
os.environ['GCE_METADATA_ROOT'] = ''
os.environ['DISABLE_GCE_METADATA_SERVICE'] = 'true'
import streamlit as st
from chatbot import get_chatbot_response
import json

# Cấu hình trang
st.set_page_config(
    page_title="ReactJS Chatbot", 
    page_icon="🤖",
    layout="wide"
)

# Sử dụng giao diện chat hiện đại với Streamlit Chat API

# Khởi tạo session state
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "display_messages" not in st.session_state:
    st.session_state.display_messages = []

if "context_history" not in st.session_state:
    st.session_state.context_history = []


# Sidebar: chọn model và xóa lịch sử
with st.sidebar:
    st.header("Tùy chọn")
    model = st.selectbox("Chọn mô hình", ["llama3-70b-8192", "gemma2-9b-it", "openai/gpt-oss-120b", "qwen/qwen3-32b"],  index=0)
    if st.button("🗑️ Xóa lịch sử chat"):
        st.session_state.chat_history = []
        st.session_state.display_messages = []
        st.session_state.context_history = []
        st.rerun()

# Main chat interface hiện đại
st.markdown("""
<style>
.chat-window {
    max-height: 70vh;
    overflow-y: auto;
    padding: 1rem;
    background: #f8fafc;
    border-radius: 12px;
    border: 1px solid #e0e0e0;
    margin-bottom: 1rem;
}
.chat-input-row {
    display: flex;
    gap: 0.5rem;
    align-items: center;
}
.chat-input-box {
    flex: 1;
    border-radius: 8px;
    border: 1px solid #ccc;
    padding: 0.75rem;
    font-size: 1rem;
}
.send-btn {
    background: #2196f3;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 0.75rem 1.2rem;
    font-size: 1rem;
    cursor: pointer;
    transition: background 0.2s;
}
.send-btn:hover {
    background: #1769aa;
}
</style>
""", unsafe_allow_html=True)

st.title("🤖 ReactJS Chatbot")

# Hiển thị lịch sử chat với st.chat_message
for msg in st.session_state.display_messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# Input chat với st.chat_input, gửi trên Enter
user_input = st.chat_input("Hãy hỏi bất cứ điều gì về ReactJS...")
if user_input:
    # Giới hạn số từ
    if len(user_input.split()) > 100:
        st.error("Giới hạn 100 từ cho mỗi câu hỏi.")
    else:
        # Hiển thị tin nhắn user
        st.chat_message("user").write(user_input)
        # Xử lý và hiển thị trả lời
        with st.chat_message("assistant"):
            with st.spinner("🤖 Đang trả lời..."):
                try:
                    answer, context_info, updated_chat_history = get_chatbot_response(
                        user_input,
                        st.session_state.chat_history,
                        5,
                        model
                    )
                    st.write(answer)
                    # Cập nhật lịch sử
                    st.session_state.chat_history = updated_chat_history
                    st.session_state.display_messages.append({"role": "user", "content": user_input})
                    st.session_state.display_messages.append({"role": "assistant", "content": answer})
                    st.session_state.context_history.append(context_info)
                except Exception as e:
                    st.error(f"❌ Lỗi: {str(e)}")

