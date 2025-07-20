### agents/eligibility/planner.py

class AgentPlanner:
    async def plan(self, context):
        raise NotImplementedError

    async def execute(self, context):
        raise NotImplementedError

class PlanContext:
    def __init__(self, latestUserMessage="", session_id=""):
        self.latestUserMessage = latestUserMessage
        self.session_id = session_id

class EligibilityAgentPlanner(AgentPlanner):
    def __init__(self):
        self.intro = (
            "I am the Eligibility Agent. I will evaluate a loan applicant based on structured fields "
            "from key financial documents. My goal is to decide if the applicant qualifies for pre-approval, "
            "using a scoring rubric grounded in explainability."
        )

    async def plan(self, context: PlanContext) -> str:
        msg = context.latestUserMessage.lower()

        if "eligibility" in msg:
            return (
                f"{self.intro}\n"
                "Step 1: Use tools to extract structured fields from passport, PAN, credit report, ITR, and bank statements.\n"
                "Step 2: Score each criterion using the charter rubric.\n"
                "Step 3: Aggregate weighted scores and calculate a confidence score.\n"
                "Step 4: Generate a summary with human-friendly justification.\n"
                "Step 5: Return a structured JSON with decision, score, and explanation."
            )

        return "Please upload the required documents to begin eligibility evaluation."
