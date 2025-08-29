import streamlit as st
from chatbot import get_chatbot_response
import json

# Cấu hình trang
st.set_page_config(
    page_title="ReactJS Chatbot", 
    page_icon="🤖",
    layout="wide"
)

# CSS tùy chỉnh
st.markdown("""
<style>
.user-message {
    background-color: #e1f5fe;
    padding: 10px;
    border-radius: 10px;
    margin: 5px 0;
    border-left: 4px solid #2196f3;
}
.bot-message {
    background-color: #f3e5f5;
    padding: 10px;
    border-radius: 10px;
    margin: 5px 0;
    border-left: 4px solid #9c27b0;
}
.context-info {
    background-color: #fff3e0;
    padding: 10px;
    border-radius: 5px;
    font-size: 12px;
    margin: 5px 0;
}
.debug-info {
    background-color: #f5f5f5;
    padding: 8px;
    border-radius: 5px;
    font-size: 11px;
    color: #666;
}
</style>
""", unsafe_allow_html=True)

# Khởi tạo session state
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "display_messages" not in st.session_state:
    st.session_state.display_messages = []

if "context_history" not in st.session_state:
    st.session_state.context_history = []

# Header
st.title("🤖 ReactJS Chatbot")

# Sidebar cho settings
with st.sidebar:
    st.header("Cài đặt")
    topk = st.slider("Top K Context", 1, 10, 5)
    model = st.selectbox("Groq Model", ["llama3-70b-8192"], index=0)
    
    st.header("Debug Info")
    st.write(f"Số tin nhắn trong lịch sử: {len(st.session_state.chat_history)}")
    st.write(f"Số tin nhắn hiển thị: {len(st.session_state.display_messages)}")
    
    if st.button("Delete history"):
        st.session_state.chat_history = []
        st.session_state.display_messages = []
        st.session_state.context_history = []
        st.rerun()

# Main chat interface
col1, col2 = st.columns([2, 1])

with col1:
    st.header("💬 Cuộc hội thoại")
    
    # Hiển thị lịch sử chat
    chat_container = st.container()
    with chat_container:
        for i, msg in enumerate(st.session_state.display_messages):
            if msg["role"] == "user":
                st.markdown(f'<div class="user-message"><b>👤 You:</b> {msg["content"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="bot-message"><b>🤖 Bot:</b> {msg["content"]}</div>', unsafe_allow_html=True)
                
                # Hiển thị context info nếu có
                if i < len(st.session_state.context_history):
                    with st.expander(f"📋 Context đã sử dụng (tin nhắn {i//2 + 1})", expanded=False):
                        st.text(st.session_state.context_history[i//2])
    
    # Input mới
    user_input = st.text_input("💭 Ask chat DDT:", key="user_input")
    
    # Đếm số từ trong input
    input_word_count = len(user_input.split()) if user_input else 0
    if input_word_count > 100:
        st.warning(f"Limit is 100 words.")
    
    if st.button("Send") or (user_input and st.session_state.get("last_input") != user_input):
        if user_input:
            if input_word_count > 100:
                st.error(f"words reach limit")
            else:
                st.session_state.last_input = user_input
                with st.spinner("🔍 Processing.."):
                    try:
                        # Gọi chatbot
                        answer, context_info, updated_chat_history = get_chatbot_response(
                            user_input, 
                            st.session_state.chat_history, 
                            topk, 
                            model
                        )
                        # Cập nhật session state
                        st.session_state.chat_history = updated_chat_history
                        st.session_state.display_messages.append({"role": "user", "content": user_input})
                        st.session_state.display_messages.append({"role": "assistant", "content": answer})
                        st.session_state.context_history.append(context_info)
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Lỗi: {str(e)}")

with col2:
    st.header("🔍 Context & Debug")
    
    if st.session_state.context_history:
        st.subheader("📋 Context gần nhất")
        with st.expander("Xem chi tiết context", expanded=True):
            current_context = st.session_state.context_history[-1] if st.session_state.context_history else "Chưa có context"
            st.text(current_context)
            # Thống kê số context và số token
            num_context = current_context.count('--- Context #')
            num_tokens = len(current_context.split())
            st.info(f"Số context: {num_context} | Số từ (ước lượng token): {num_tokens}")
    
    st.subheader("🐛 Debug Info")
    st.markdown(f"""
    <div class="debug-info">
    <b>Chat History Length:</b> {len(st.session_state.chat_history)}<br>
    <b>Display Messages:</b> {len(st.session_state.display_messages)}<br>
    <b>Context Records:</b> {len(st.session_state.context_history)}<br>
    <b>Top K:</b> {topk}<br>
    <b>Model:</b> {model}
    </div>
    """, unsafe_allow_html=True)
    
    # Xuất chat history dưới dạng JSON để debug
    if st.button("📄 Xuất Chat History"):
        if st.session_state.chat_history:
            st.download_button(
                label="💾 Tải về chat_history.json",
                data=json.dumps(st.session_state.chat_history, indent=2, ensure_ascii=False),
                file_name="chat_history.json",
                mime="application/json"
            )

# Footer
st.markdown("---")

