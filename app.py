import streamlit as st
from openai import OpenAI
import os, json, base64
from PyPDF2 import PdfReader
from docx import Document # For .docx files
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Universal AI Agent", page_icon="📎")
st.title("📎 Universal AI Agent")

client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.getenv("GROQ_API_KEY")
)

# --- FILE PROCESSOR ROUTER ---
def process_file(uploaded_file):
    name = uploaded_file.name.lower()
    
    # 1. Handle Images (Vision)
    if name.endswith(('.png', '.jpg', '.jpeg')):
        return {"type": "image", "content": base64.b64encode(uploaded_file.read()).decode('utf-8')}
    
    # 2. Handle PDF
    elif name.endswith('.pdf'):
        reader = PdfReader(uploaded_file)
        text = "".join([p.extract_text() for p in reader.pages if p.extract_text()])
        return {"type": "text", "content": text}
    
    # 3. Handle Word (.docx)
    elif name.endswith('.docx'):
        doc = Document(uploaded_file)
        text = "\n".join([para.text for para in doc.paragraphs])
        return {"type": "text", "content": text}
    
    # 4. Handle Plain Text
    elif name.endswith('.txt'):
        return {"type": "text", "content": uploaded_file.read().decode('utf-8')}
    
    return None

# --- INITIALIZATION ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- SIDEBAR: SINGLE UPLOAD SECTION ---
with st.sidebar:
    st.header("Attachments")
    uploaded_file = st.file_uploader("Upload any file (PDF, Image, Word, TXT)", 
                                     type=["pdf", "jpg", "png", "jpeg", "docx", "txt"])
    
    file_data = None
    if uploaded_file:
        file_data = process_file(uploaded_file)
        st.success(f"Loaded: {uploaded_file.name}")
        if file_data["type"] == "image":
            st.image(uploaded_file)

    st.divider()
    if st.button("🗑️ Clear Chat"):
        st.session_state.messages = []
        st.rerun()

# --- CHAT INTERFACE ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]): st.markdown(msg["content"])

if file_data:
    if prompt := st.chat_input("Ask about your file..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)

        # Building the AI request
        context_text = ""
        image_payload = None

        if file_data["type"] == "text":
            context_text = f"File Content: {file_data['content']}\n\n"
        else:
            image_payload = file_data["content"]

        # Constructing the message payload for Llama 4 Scout
        user_content = [{"type": "text", "text": f"{context_text}User Question: {prompt}"}]
        if image_payload:
            user_content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_payload}"}})

        with st.chat_message("assistant"):
            try:
                response = client.chat.completions.create(
                    model="meta-llama/llama-4-scout-17b-16e-instruct",
                    messages=[{"role": "user", "content": user_content}]
                )
                reply = response.choices[0].message.content
                st.markdown(reply)
                st.session_state.messages.append({"role": "assistant", "content": reply})
            except Exception as e:
                st.error(f"Error: {e}")
else:
    st.warning("Upload a supported file before you can chat. Supported formats: PDF, Image (JPG/PNG), Word (.docx), Text (.txt).")