from fastapi import FastAPI, Request
from .executor import run_eligibility_pipeline
from dotenv import load_dotenv
load_dotenv()

app = FastAPI()

@app.post("/check-eligibility")
async def check_eligibility(request: Request):
    data = await request.json()
    applicant_id = data.get("applicant_id")

    if not applicant_id:
        return {"error": "Missing applicant_id"}

    result = await run_eligibility_pipeline(applicant_id)
    return result