import streamlit as st
from openai import OpenAI
import os, json, base64
from PyPDF2 import PdfReader
from docx import Document # For .docx files
from dotenv import load_dotenv
import pandas as pd
import io
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.units import inch

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
    background-color: #f0f2f6;
    border-bottom-left-radius: 2px;
    line-height: 1.6; /* Adds breathing room between rules */
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
    import streamlit as st

st.markdown("""
    <style>
        /* 1. Style for USER messages (Blue) */
        [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
            background-color: #0078FF !important;
            color: white !important;
            flex-direction: row-reverse; /* Optional: moves user avatar to the right */
        }

        /* 2. Style for ASSISTANT messages (Gray) */
        [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) {
            background-color: #F0F2F6 !important;
            color: black !important;
        }

        /* Ensure text inside bubbles inherits the correct color */
        [data-testid="stChatMessage"] p {
            color: inherit !important;
        }
    </style>
""", unsafe_allow_html=True)

local_css()
st.title("📎 Universal AI Agent")

client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.getenv("GROQ_API_KEY")
)

# --- PDF GENERATOR ---
def generate_chat_pdf(messages):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor='#000080',
        spaceAfter=12,
    )
    user_style = ParagraphStyle(
        'UserBubble',
        parent=styles['Normal'],
        backColor='#0078FF',
        textColor='white',
        borderPadding=(8, 8, 8, 8),
        leftIndent=120,
        rightIndent=0,
        spaceBefore=6,
        spaceAfter=6,
    )
    assistant_style = ParagraphStyle(
        'AssistantBubble',
        parent=styles['Normal'],
        backColor='#F0F2F6',
        textColor='#1F2937',
        borderPadding=(8, 8, 8, 8),
        leftIndent=0,
        rightIndent=120,
        spaceBefore=6,
        spaceAfter=6,
    )

    story = [Paragraph("Chat History", title_style), Spacer(1, 0.2*inch)]
    
    for msg in messages:
        role = msg['role'].upper()
        content = msg['content'].replace('\n', '<br/>')[:2000]
        style = assistant_style if msg['role'] == 'assistant' else user_style
        story.append(Paragraph(f"<b>{role}:</b> {content}", style))
        story.append(Spacer(1, 0.1*inch))
    
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

# --- FILE PROCESSOR ROUTER ---
def process_file(uploaded_file):

    MAX_FILE_SIZE = 2 * 1024 * 1024  # 2MB Limit
    if uploaded_file.size > MAX_FILE_SIZE:
        st.error("⚠️ File is too large. Please upload a file under 2MB.")
        return None
    
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
        return {"type": "text", "content": df.to_string(index=False)}
    
    #6. Handle Excel files
    elif name.endswith('.xlsx'):
        df = pd.read_excel(uploaded_file)
        return {"type": "text", "content": df.to_string(index=False)}
    
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
        if file_data:
            st.success(f"Loaded: {uploaded_file.name}")
            if file_data["type"] == "image":
                # Display image from base64 data instead of file object
                import base64
                from PIL import Image
                image_bytes = base64.b64decode(file_data['content'])
                st.image(Image.open(io.BytesIO(image_bytes)))
        else:
            st.error("Unsupported file type. Please upload PDF, Image, Word, TXT, CSV, or Excel.")

    st.divider()
    
    # Download Chat History
    if st.session_state.messages:
        pdf_data = generate_chat_pdf(st.session_state.messages)
        st.download_button(
            label="📥 Download PDF",
            data=pdf_data,
            file_name="chat_history.pdf",
            mime="application/pdf"
        )
    
    if st.button("🗑️ Clear Chat"):
        st.session_state.messages = []
        st.rerun()

# --- CHAT INTERFACE ---
for message in st.session_state.messages:
    # This 'role' variable determines which CSS style above gets applied
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if file_data:
    if prompt := st.chat_input("Ask about your file..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)

        # Building the AI request
        context_text = ""
        image_payload = None

        if file_data["type"] == "text":
            # Limit file content to 8000 characters to avoid context length exceeded error
            file_content = file_data['content'][:8000]
            if len(file_data['content']) > 8000:
                file_content += "\n\n[Content truncated due to length...]"
            context_text = f"File Content: {file_content}\n\n"
        else:
            image_payload = file_data["content"]

        # Constructing the message payload
        user_content = [{"type": "text", "text": f"{context_text}User Question: {prompt}"}]
        if image_payload:
            user_content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_payload}"}})

        with st.chat_message("assistant"):
            try:
                response = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[{"role": "user", "content": user_content}],
                    timeout=60
                )
                reply = response.choices[0].message.content
                st.markdown(reply)
                st.session_state.messages.append({"role": "assistant", "content": reply})
            except Exception as e:
                error_msg = str(e)
                if "context_length_exceeded" in error_msg.lower() or "400" in error_msg:
                    st.error("File content too large. Try uploading a smaller file or ask a more specific question.")
                elif "timeout" in error_msg.lower():
                    st.error("Request timed out. Please check your internet connection or try again later.")
                elif "api key" in error_msg.lower():
                    st.error("API key error. Check your GROQ_API_KEY in .env file.")
                else:
                    st.error(f"Error: {error_msg}")
else:
    st.warning("To get started, please upload a document in PDF, Image, Word,Text, CSV or Excel format. Once your file is attached, you can begin chatting with the AI about its contents.")