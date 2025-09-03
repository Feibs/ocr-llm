import streamlit as st
import os
import base64
import time
import requests
from mistralai import Mistral

from dotenv import load_dotenv
load_dotenv()

# === Environment variables ===
LLM_API_KEY = os.getenv('LLM_API_KEY')
LLM_API_ENDPOINT = os.getenv('LLM_API_ENDPOINT')
MODEL_ID = os.getenv('MODEL_ID')
MISTRAL_API_KEY = os.getenv('MISTRAL_API_KEY')

# === Streamlit page setup ===
st.set_page_config(layout="wide", page_title="Financial Statement Extractor", page_icon="🖥️")
st.title("Financial Statement Extractor")
st.markdown("<h3 style='color: white;'>Mistral OCR + OpenAI LLM</h3>", unsafe_allow_html=True)
with st.expander("Expand Me"):
    st.markdown("""
    This application extracts information from document using Mistral OCR
    and processes the results with an LLM from OpenWebUI.
    """)

api_key = MISTRAL_API_KEY

# === Session state ===
if "ocr_result" not in st.session_state:
    st.session_state["ocr_result"] = []
if "preview_src" not in st.session_state:
    st.session_state["preview_src"] = []
if "image_bytes" not in st.session_state:
    st.session_state["image_bytes"] = []

# === File upload ===
file_type = st.radio("Select file type", ("PDF", "Image"))
uploaded_files = st.file_uploader("Upload one or more files",
                                   type=["pdf", "jpg", "jpeg", "png"],
                                   accept_multiple_files=True)

# === Helper: Extract filename ===
def extract_filename(filepath):
    return os.path.splitext(os.path.basename(filepath))[0]

# === Helper: Send OCR text to OpenWebUI ===
def send_to_openwebui(document):
    try:
        payload = {
            "model": MODEL_ID,
            "messages": [{"role": "user", "content": f"{document}"}],
        }
        headers = {
            "Authorization": f"Bearer {LLM_API_KEY}",
            "Content-Type": "application/json",
        }
        response = requests.post(
            f"{LLM_API_ENDPOINT}/api/chat/completions",
            json=payload,
            headers=headers,
        )
        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"]
        else:
            return f"Error owui {response.status_code}: {response.text}"
    except Exception as e:
        return f"Error sending to OpenWebUI: {str(e)}"

# === OCR Processing ===
if st.button("Process"):
    if not uploaded_files:
        st.error("Please upload at least one file.")
    else:
        client = Mistral(api_key=api_key)
        st.session_state["ocr_result"] = []
        st.session_state["preview_src"] = []
        st.session_state["image_bytes"] = []

        for source in uploaded_files:
            if file_type == "PDF":
                file_bytes = source.read()
                encoded_pdf = base64.b64encode(file_bytes).decode("utf-8")
                document = {
                    "type": "document_url",
                    "document_url": f"data:application/pdf;base64,{encoded_pdf}"
                }
                preview_src = f"data:application/pdf;base64,{encoded_pdf}"
            else:
                file_bytes = source.read()
                mime_type = source.type
                encoded_image = base64.b64encode(file_bytes).decode("utf-8")
                document = {
                    "type": "image_url",
                    "image_url": f"data:{mime_type};base64,{encoded_image}"
                }
                preview_src = f"data:{mime_type};base64,{encoded_image}"
                st.session_state["image_bytes"].append(file_bytes)

            with st.spinner(f"Processing {source.name}..."):
                try:
                    filename = extract_filename(source.name)
                    ocr_response = client.ocr.process(
                        model="mistral-ocr-latest",
                        document=document,
                        include_image_base64=False
                    )
                    time.sleep(1)
                    pages = ocr_response.pages if hasattr(ocr_response, "pages") else []
                    result_text = "\n\n".join(page.markdown for page in pages) or "No result found."
                   
                except Exception as e:
                    result_text = f"Error extracting result: {e}"

                st.session_state["ocr_result"].append(result_text)
                st.session_state["preview_src"].append(preview_src)

# === Display results ===
if st.session_state["ocr_result"]:
    for idx, result in enumerate(st.session_state["ocr_result"]):
        filename = extract_filename(uploaded_files[idx].name)
        col1, col2 = st.columns(2)

        with col1:
            st.subheader(f"Input Document")
            if file_type == "PDF":
                pdf_embed_html = f'<iframe src="{st.session_state["preview_src"][idx]}" width="100%" height="800" frameborder="0" style="border: none; box-shadow: 0 0 10px rgba(0,0,0,0.2); border-radius: 8px;"></iframe>'
                st.markdown(pdf_embed_html, unsafe_allow_html=True)
            else:
                st.image(st.session_state["image_bytes"][idx])

        with col2:
            st.subheader("Processed Result")

            with st.spinner("Processing with OpenWebUI..."):
                processed_text = send_to_openwebui(result)

                processed_b64 = base64.b64encode(processed_text.encode()).decode()
                processed_href = f'<a href="data:text/markdown;base64,{processed_b64}" download="{filename}_processed.md">📥 Download</a>'
                st.markdown(processed_href, unsafe_allow_html=True)

                st.markdown(processed_text)