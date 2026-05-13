import streamlit as st
from openai import OpenAI
import os, json, base64
from PyPDF2 import PdfReader
from docx import Document # For .docx files
from dotenv import load_dotenv
import pandas as pd
import io

import streamlit as st

# --- PASTE THIS EXACTLY AS IS ---
st.markdown("""
<style>
    /* This targets the container for each chat message */
    [data-testid="stChatMessage"] {
        border-radius: 20px;
        padding: 15px;
        margin-bottom: 10px;
        width: fit-content;
        max-width: 85%;
    }

    /* Style for the Assistant/Agent */
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) {
        background-color: #f0f2f6; /* Soft Grey */
        border-bottom-left-radius: 2px;
    }

    /* Style for the User */
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
        background-color: #007AFF; /* Modern Blue */
        color: white;
        margin-left: auto; /* Pushes user bubble to the right */
        border-bottom-right-radius: 2px;
    }

    /* Fix text color for user messages so markdown is readable */
    [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) p {
        color: white;
    }
    
    /* Hide the default avatar icons if you want a super clean look (Optional) */
    /* [data-testid="stChatMessageAvatarUser"], [data-testid="stChatMessageAvatarAssistant"] {
        display: none;
    } */
</style>
""", unsafe_allow_html=True)

load_dotenv()

st.set_page_config(page_title="Universal AI Agent", page_icon="📎")
import streamlit as st

# --- STEP 1: DEFINE STYLES ---
def local_css():
    st.markdown("""
    <style>
    .chat-bubble {
        padding: 12px 16px;
        border-radius: 15px;
        margin-bottom: 10px;
        max-width: 80%;
        font-family: sans-serif;
        line-height: 1.5;
    }
    .user-bubble {
        background-color: #007AFF; /* Blue */
        color: white;
        margin-left: auto; /* Pushes to right */
        border-bottom-right-radius: 2px;
    }
    .agent-bubble {
        background-color: #f0f2f6; /* Light Grey */
        color: #31333F;
        margin-right: auto; /* Pushes to left */
        border-bottom-left-radius: 2px;
    }
    </style>
    """, unsafe_allow_html=True)

local_css()
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
    
    # 5. Handle CSV and Excel (Tabular Data)
    elif name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
        # Convert the first few rows to a string for the AI to analyze
        return df.to_string(index=False)
    
    #6. Handle Excel files
    elif name.endswith('.xlsx'):
        df = pd.read_excel(uploaded_file)
        return df.to_string(index=False)
    
    return None

# --- INITIALIZATION ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- SIDEBAR: SINGLE UPLOAD SECTION ---
with st.sidebar:
    st.header("Attachments")
    uploaded_file = st.file_uploader("Upload any file (PDF, Image, Word, TXT, CSV, Excel)", 
                                     type=["pdf", "jpg", "png", "jpeg", "docx", "txt", "csv", "xlsx"])
    
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
# --- STEP 2: USE THE BUBBLES ---
for message in st.session_state.messages:
    role = message["role"]
    content = message["content"]
    
    if role == "user":
        st.markdown(f'<div class="chat-bubble user-bubble">{content}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="chat-bubble agent-bubble">{content}</div>', unsafe_allow_html=True)

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
    st.warning("To get started, please upload a document in PDF, Image, Word,Text, CSV or Excel format. Once your file is attached, you can begin chatting with the AI about its contents.")