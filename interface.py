import gradio as gr
from chatbot import ask_groq, build_context, find_top_k, get_embedding, resize_embedding, read_env_key
from pymongo import MongoClient

# Setup MongoDB connection once
MONGODB_URI = read_env_key("MONGODB_URI")
client = MongoClient(MONGODB_URI)
db = client.get_default_database()
collection = db["normalized"]

def chatbot_gradio(question, topk=5, model="llama3-70b-8192"):
    query_emb = get_embedding(question)
    query_emb = resize_embedding(query_emb, 1024)
    results = find_top_k(query_emb, collection, k=topk)
    context = build_context(results)
    answer = ask_groq(question, context, model=model)
    # Show top context for transparency, including type
    context_display = "\n\n".join([
        f"--- Context #{i+1} (type={doc.get('type','?')}, similarity={score:.3f}) ---\nExplanation: {doc.get('explanation')}\nCode: {doc.get('code')}\nLink: {doc.get('link')}"
        for i, (score, doc) in enumerate(results)
    ])
    return answer, context_display

demo = gr.Interface(
    fn=chatbot_gradio,
    inputs=[
        gr.Textbox(label="Your question", lines=2),
        gr.Slider(1, 10, value=5, step=1, label="Top K context"),
        gr.Dropdown(["llama3-70b-8192"], value="llama3-70b-8192", label="Groq Model")
    ],
    outputs=[
        gr.Textbox(label="Chatbot Answer", lines=8),
        gr.Textbox(label="Top Contexts", lines=10)
    ],
    title="ReactJS Chatbot (Groq + Gemini + MongoDB)",
    description="Ask any ReactJS/StackOverflow question. The bot will search the most relevant code/context and answer using Groq LLM."
)

def main():
    demo.launch(share=True)

if __name__ == "__main__":
    main()
