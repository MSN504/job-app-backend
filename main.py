from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os, shutil, uuid, time
import openai
from fpdf import FPDF
import requests
from bs4 import BeautifulSoup
import urllib.parse

app = FastAPI()

# Enable CORS for Vercel frontend only
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://job-app-frontend-mu.vercel.app"],  # Replace with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

openai.api_key = os.getenv("OPENAI_API_KEY")

def cleanup_old_files(directory, max_age_seconds=3600):
    now = time.time()
    for f in os.listdir(directory):
        path = os.path.join(directory, f)
        if os.path.isfile(path) and (now - os.path.getmtime(path)) > max_age_seconds:
            os.remove(path)

class JobSearch(BaseModel):
    jobKeywords: str
    location: str
    excludeTerms: str

class LetterRequest(BaseModel):
    jobLink: str

class LetterContent(BaseModel):
    letter: str

@app.post("/api/generate-letter")
async def generate_letter(req: LetterRequest):
    cleanup_old_files(UPLOAD_DIR)
    prompt = f"Write a motivational letter for this job: {req.jobLink}"
    try:
        res = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=600
        )
        letter = res['choices'][0]['message']['content'].strip()
        return { "letter": letter }
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.post("/api/convert-letter-to-pdf")
async def convert_letter_to_pdf(data: LetterContent):
    cleanup_old_files(UPLOAD_DIR)
    filename = f"motivational_letter_{uuid.uuid4().hex}.pdf"
    path = os.path.join(UPLOAD_DIR, filename)

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    for line in data.letter.split('\n'):
        pdf.multi_cell(0, 10, line)
    pdf.output(path)
    return { "filename": filename }

@app.post("/api/upload-documents")
async def upload_documents(cv: UploadFile = File(...), additional: UploadFile = File(...), cover_letter: UploadFile = File(...)):
    try:
        for file in [cv, additional, cover_letter]:
            path = os.path.join(UPLOAD_DIR, file.filename)
            with open(path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        return { "message": "Files uploaded successfully" }
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.post("/api/search-jobs")
async def search_jobs(req: JobSearch):
    cleanup_old_files(UPLOAD_DIR)
    query = f"{req.jobKeywords} {req.location}"
    exclude = req.excludeTerms.split(',')
    url = f"https://de.indeed.com/jobs?q={urllib.parse.quote_plus(query)}&limit=10"
    try:
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(res.text, 'html.parser')
        jobs = []
        for card in soup.select(".job_seen_beacon"):
            title = card.select_one("h2 span")
            link = card.select_one("a")
            company = card.select_one(".companyName")
            location = card.select_one(".companyLocation")
            if title and not any(ex.lower() in title.text.lower() for ex in exclude):
                jobs.append({
                    "title": title.text.strip(),
                    "company": company.text.strip() if company else "",
                    "location": location.text.strip() if location else "",
                    "link": "https://de.indeed.com" + link["href"] if link else ""
                })
        return { "results": jobs[:10] }
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
