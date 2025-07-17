import os
import json
import re
from openai import OpenAI

OPENAI_ENDPOINT = "https://models.github.ai/inference"
OPENAI_MODEL = "openai/gpt-4o"
OPENAI_TOKEN = os.getenv("GITHUB_TOKEN")

client = OpenAI(
    base_url=OPENAI_ENDPOINT,
    api_key=OPENAI_TOKEN,
)

def call_gpt_eligibility(prompt: str) -> dict:
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": "You are a careful, fair loan eligibility expert."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=400,
        temperature=0.2,
    )
    gpt_output = response.choices[0].message.content
    # Extract JSON from the response
    match = re.search(r'\{.*\}', gpt_output, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass
    return {
        "decision": "Needs Review",
        "reason": "Could not parse model response.",
        "missing_fields": [],
        "flagged": True,
        "flagged_reason": "Malformed GPT output"
    } 