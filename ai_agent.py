import os
import json
from openai import OpenAI
from dotenv import load_dotenv
from PyPDF2 import PdfReader

load_dotenv()

# --- CONFIGURATION ---
MEMORY_FILE = "chat_history.json"
DATA_PATH = "data/info.pdf"

client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.getenv("GROQ_API_KEY")
)

# --- FUNCTIONS ---
def get_pdf_content(file_path):
    if not os.path.exists(file_path):
        return "No PDF data found."
    try:
        reader = PdfReader(file_path)
        return "".join([page.extract_text() for page in reader.pages if page.extract_text()])
    except Exception:
        return "Error reading PDF."

def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    return []

def save_memory(messages):
    # We don't save the massive System Message to keep the file clean
    # We only save the actual conversation
    chat_only = [m for m in messages if m["role"] != "system"]
    with open(MEMORY_FILE, "w") as f:
        json.dump(chat_only, f, indent=4)

# --- INITIALIZATION ---
pdf_text = get_pdf_content(DATA_PATH)
past_messages = load_memory()

# Define the System Identity
system_message = {
    "role": "system", 
    "content": f"You are a helpful AI teacher. Use this PDF info if needed: {pdf_text}"
}

# Combine: System Identity + Past Memory
messages = [system_message] + past_messages

print(f"--- Agent Online ({'New Session' if not past_messages else 'Memory Loaded'}) ---")

# --- MAIN LOOP ---
while True:
    user_input = input("You: ")
    if user_input.lower() in ["quit", "exit"]:
        break

    messages.append({"role": "user", "content": user_input})

    try:
        completion = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=messages
        )

        reply = completion.choices[0].message.content
        print(f"\nAgent: {reply}\n")

        messages.append({"role": "assistant", "content": reply})
        
        # Save the updated conversation to the JSON file
        save_memory(messages)
        
    except Exception as e:
        print(f"Error: {e}")