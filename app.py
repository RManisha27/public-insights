import streamlit as st
import os
import re
import io
import requests
from PyPDF2 import PdfReader
from bs4 import BeautifulSoup
from langchain_groq import ChatGroq

# =========================
# STREAMLIT CONFIG
# =========================
st.set_page_config(
    page_title="Public Policy Insight & Impact Analyzer (PPIIA)",
    layout="wide"
)

st.title("🏛️ Public Policy Insight & Impact Analyzer (PPIIA)")

# =========================
# GET API KEY (STREAMLIT CLOUD SAFE)
# =========================
try:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except Exception:
    st.error("❌ GROQ_API_KEY not found. Please add it in Streamlit Secrets.")
    st.stop()

# =========================
# SESSION STATE
# =========================
if "analysis" not in st.session_state:
    st.session_state.analysis = None

# =========================
# BILL VALIDATION
# =========================
BILL_KEYWORDS = [
    "bill", "act", "parliament", "lok sabha",
    "rajya sabha", "statement of objects",
    "introduced", "passed", "minister"
]

def is_valid_bill(text: str) -> bool:
    text = text.lower()
    hits = sum(1 for k in BILL_KEYWORDS if k in text)
    return len(text) > 500 and hits >= 4

# =========================
# TEXT EXTRACTION
# =========================
def extract_pdf(file):
    reader = PdfReader(file)
    text = ""
    for page in reader.pages:
        if page.extract_text():
            text += page.extract_text() + "\n"
    return text

def extract_from_url(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers, timeout=20)

    if "application/pdf" in r.headers.get("Content-Type", "").lower():
        reader = PdfReader(io.BytesIO(r.content))
        text = ""
        for page in reader.pages:
            if page.extract_text():
                text += page.extract_text() + "\n"
        return text

    soup = BeautifulSoup(r.text, "html.parser")
    return soup.get_text(separator="\n")

# =========================
# LLM CALL
# =========================
def ask_llm(prompt):
    llm = ChatGroq(
        groq_api_key=GROQ_API_KEY,
        model_name="llama-3.3-70b-versatile",
        temperature=0.1,
        max_tokens=3000
    )
    return llm.invoke(prompt).content

# =========================
# USER INPUT
# =========================
input_type = st.radio("Select Input Type", ["PDF Upload", "URL"])

bill_text = ""

if input_type == "PDF Upload":
    file = st.file_uploader("Upload Government Bill PDF", type=["pdf"])
    if file:
        bill_text = extract_pdf(file)

elif input_type == "URL":
    url = st.text_input("Enter Government Bill URL")
    if url:
        bill_text = extract_from_url(url)

# =========================
# ANALYSIS
# =========================
if bill_text:

    if not is_valid_bill(bill_text):
        st.error("❌ This does not appear to be a valid government bill.")
        st.stop()

    st.success("✅ Valid Government Bill Detected")

    with st.expander("📜 Preview"):
        st.text_area("Bill Text", bill_text[:3000], height=250)

    if st.button("🔍 Generate Analysis"):
        with st.spinner("Analyzing..."):

            PROMPT = f"""
You are a Public Policy Analyst.

Generate analysis using EXACT headers:

SECTOR:
SUMMARY:
IMPACT:
POSITIVES:
RISKS:
BENEFICIARIES:

BILL TEXT:
{bill_text[:12000]}
"""

            result = ask_llm(PROMPT)
            st.session_state.analysis = result

# =========================
# DISPLAY
# =========================
if st.session_state.analysis:
    st.markdown("## 📊 Policy Analysis Report")
    st.write(st.session_state.analysis)
