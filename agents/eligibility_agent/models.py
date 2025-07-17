from pydantic import BaseModel
from typing import List, Optional

class EligibilityRequest(BaseModel):
    applicant_id: str

class EligibilityDecision(BaseModel):
    decision: str  # "Yes", "No", or "Needs Review"
    reason: str
    missing_fields: List[str]
    flagged: Optional[bool] = False
    flagged_reason: Optional[str] = "" 