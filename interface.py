import gradio as gr
from chatbot import get_chatbot_response

def chatbot_gradio(message, history, topk=5, model="llama3-70b-8192"):
    """
    Hàm xử lý chat với lịch sử cho Gradio
    history: list of [user_msg, bot_msg] pairs
    """
    try:
        # Chuyển đổi history của Gradio sang format cho chatbot
        chat_history = []
        for user_msg, bot_msg in history:
            if user_msg:
                chat_history.append({"role": "user", "content": user_msg})
            if bot_msg:
                chat_history.append({"role": "assistant", "content": bot_msg})
        
        # Lấy phản hồi từ chatbot
        answer, context_info, updated_chat_history = get_chatbot_response(
            message, chat_history, topk, model
        )
        
        return answer
    except Exception as e:
        return f"❌ Lỗi: {str(e)}"

# Tạo interface Gradio với ChatInterface
demo = gr.ChatInterface(
    fn=chatbot_gradio,
    additional_inputs=[
        gr.Slider(1, 10, value=5, step=1, label="Top K Context"),
        gr.Dropdown(["llama3-70b-8192"], value="llama3-70b-8192", label="Groq Model")
    ],
    title="🤖 ReactJS Chatbot (Gradio Version)",
    description="Ask any ReactJS question. The bot maintains conversation history and searches relevant context.",
    examples=[
        "How to create a Todo app in React?",
        "What is useState hook?",
        "How to handle forms in React?",
        "Explain useEffect with examples"
    ],
    retry_btn="🔄 Thử lại",
    undo_btn="↩️ Hoàn tác",
    clear_btn="🗑️ Xóa lịch sử"
)

def main():
    demo.launch(share=True)

if __name__ == "__main__":
    main()
