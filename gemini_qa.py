from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Dict, List, Optional
import os
import json
from dotenv import load_dotenv
import google.genai as genai

from rag.retriever import retrieve_context
from rag.embedder import embed_texts
from rag.chroma_store import get_company_collection
from google.genai import errors as genai_errors
try:
    from langchain.text_splitter import RecursiveCharacterTextSplitter
except ImportError:
    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter
    except ImportError:
        RecursiveCharacterTextSplitter = None

# ---------------- ENV ----------------
load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise RuntimeError("GEMINI_API_KEY missing in .env file")

client = genai.Client(api_key=API_KEY)
MODEL_NAME = "models/gemini-flash-latest"

# ---------------- FASTAPI ----------------
app = FastAPI(title="MCQ Generator & Feedback API", version="3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- SCHEMAS ----------------
class MCQRequest(BaseModel):
    topic: str
    parts: Dict[str, int]

class SectionPerformance(BaseModel):
    correct: int
    total: int

class FeedbackRequest(BaseModel):
    topic: str
    total_correct: int
    total_questions: int
    sections: Dict[str, SectionPerformance]

class RAGMCQRequest(BaseModel):
    company: str
    topic: str
    parts: Dict[str, int]

# ---------------- UTILS ----------------
def safe_json_loads(text: str):
    """Clean and parse JSON from AI response."""
    # 1. Strip whitespace
    text = text.strip()
    
    # 2. Remove markdown code blocks if present
    if text.startswith("```"):
        lines = text.splitlines()
        # Remove first line if it's ```json or ```
        if lines[0].startswith("```"):
            lines = lines[1:]
        # Remove last line if it's ```
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    
    # 3. Handle potential escaping issues (stray backslashes)
    # This is a bit risky but often needed for line breaks or math symbols
    # We try parsing directly first, then try cleaning if it fails.
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to fix common issues: unescaped backslashes
        import re
        # Replace single backslashes that aren't part of a valid escape sequence
        # This is a simplified approach
        text_cleaned = re.sub(r'\\(?![ux"\\/bfnrt])', r'\\\\', text)
        return json.loads(text_cleaned)

def chunk_text(text: str):
    if RecursiveCharacterTextSplitter:
        splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        return splitter.split_text(text)
    return [text[i:i+500] for i in range(0, len(text), 450)]

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

# ---------------- ADMIN ENDPOINTS ----------------
UPLOAD_DIR = "data/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.get("/admin/companies")
def list_companies():
    if not os.path.exists(UPLOAD_DIR):
        return []
    return [d for d in os.listdir(UPLOAD_DIR) if os.path.isdir(os.path.join(UPLOAD_DIR, d))]

@app.post("/admin/upload")
def upload_file(company: str = Form(...), file: UploadFile = File(...)):
    company = company.strip()
    company_dir = os.path.join(UPLOAD_DIR, company)
    os.makedirs(company_dir, exist_ok=True)
    path = os.path.join(company_dir, file.filename)
    with open(path, "wb") as f:
        f.write(file.file.read())
    return {"status": "uploaded", "company": company}

@app.post("/admin/ingest")
def ingest_company_data(company: str):
    company_dir = os.path.join(UPLOAD_DIR, company)
    if not os.path.exists(company_dir):
        raise HTTPException(status_code=404, detail="Company folder not found")
    all_text = ""
    for filename in os.listdir(company_dir):
        file_path = os.path.join(company_dir, filename)
        if filename.lower().endswith(".txt"):
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                all_text += f.read()
        elif filename.lower().endswith(".pdf") and PdfReader:
            reader = PdfReader(file_path)
            for page in reader.pages:
                text = page.extract_text()
                if text: all_text += text
    if not all_text.strip():
        raise HTTPException(status_code=400, detail="No readable text found")
    chunks = chunk_text(all_text)
    embeddings = embed_texts(chunks)
    collection = get_company_collection(company)
    for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
        collection.add(documents=[chunk], embeddings=[emb], ids=[f"{company}_{i}"])
    return {"status": "embedded", "chunks": len(chunks)}

# ---------------- GENERATION ENDPOINTS ----------------
def generate_mcqs_common(topic: str, parts: Dict[str, int], context: str = ""):
    context_str = f"CONTEXT:\n{context}\n" if context else ""
    prompt = f"""
You are an expert MCQ generator for placement preparation exams.
{context_str}
TOPIC: {topic}
INSTRUCTIONS:
1. Generate EXACTLY the number of questions specified per section: {json.dumps(parts)}
2. Each question must include 'question', 'options' (A, B, C, D), 'answer' (A, B, C, D), and 'explanation'.
3. Output JSON ONLY. No extra text or markdown code blocks.
Structure:
{{
  "SectionName": [
    {{
      "question": "...",
      "options": {{ "A": "...", "B": "...", "C": "...", "D": "..." }},
      "answer": "A",
      "explanation": "..."
    }}
  ]
}}
"""
    try:
        response = client.models.generate_content(model=MODEL_NAME, contents=prompt)
        return safe_json_loads(response.text)
    except (genai_errors.ClientError, genai_errors.APIError, Exception) as e:
        # Fallback to Mock Data if Quota Exceeded or other API error
        print(f"DEBUG: Catching API error: {str(e)}")
        mock_mcqs = {}
        for section, count in parts.items():
            mock_mcqs[section] = [
                {
                    "question": f"Sample placement question about {topic} - {section} (#{i+1}) [MOCK MODE: API Quota Exceeded]",
                    "options": { "A": "Correct Option", "B": "Distractor 1", "C": "Distractor 2", "D": "Distractor 3" },
                    "answer": "A",
                    "explanation": f"API Error detail: {str(e)[:100]}... This is a mock explanation because the Gemini API quota has been reached."
                } for i in range(count)
            ]
        return mock_mcqs

@app.post("/generate-mcqs")
def generate_mcqs(request: MCQRequest):
    return generate_mcqs_common(request.topic, request.parts)

@app.post("/generate-mcqs-rag")
def generate_mcqs_rag(request: RAGMCQRequest):
    try:
        context = retrieve_context(request.company, request.topic)
    except Exception:
        context = "Mock context (RAG failed or empty)"
    mcqs = generate_mcqs_common(request.topic, request.parts, context=context)
    return {"company": request.company, "mcqs": mcqs}

@app.post("/generate-feedback")
def generate_feedback(request: FeedbackRequest):
    section_summary = "\n".join([f"{k}: {v.correct}/{v.total}" for k, v in request.sections.items()])
    prompt = f"""
You are a placement mentor. Generate JSON feedback ONLY. No markdown.
Topic: {request.topic} | Score: {request.total_correct}/{request.total_questions}
Sections: {section_summary}
Format: {{ "overall_feedback": "...", "section_feedback": {{ "SectionName": "..." }} }}
"""
    try:
        response = client.models.generate_content(model=MODEL_NAME, contents=prompt)
        return safe_json_loads(response.text)
    except Exception as e:
        print(f"Feedback API Error (using fallback): {str(e)}")
        return {
            "overall_feedback": "You reached your AI Quota limit for today. Here is a generic summary: Continue practicing your core concepts and review your weak areas. (Showing mock feedback)",
            "section_feedback": { k: f"Focus on improving your accuracy in {k}." for k in request.sections.keys() }
        }

# ---------------- STATIC FILES (CATCH-ALL) ----------------
frontend_path = os.path.join(os.path.dirname(__file__), "frontend")
app.mount("/static", StaticFiles(directory=frontend_path), name="static")

@app.get("/")
def serve_index():
    return FileResponse(os.path.join(frontend_path, "index.html"))

@app.get("/{path_name:path}")
async def serve_file(path_name: str):
    file_path = os.path.join(frontend_path, path_name)
    if os.path.isfile(file_path):
        return FileResponse(file_path)
    return FileResponse(os.path.join(frontend_path, "index.html"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
