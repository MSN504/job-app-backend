from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://job-app-frontend-mu.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class JobLink(BaseModel):
    jobLink: str

@app.get("/api/ping")
def ping():
    return {"status": "ok"}

@app.post("/api/generate-letter")
def generate_letter(data: JobLink):
    # dummy output for now
    return {"letter": f"Generated motivational letter for {data.jobLink}"}
