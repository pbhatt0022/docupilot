async def callMCPTool(tool_name, params):
    # TODO: Replace with actual tool logic. This is a stub for local development/testing.
    if tool_name == "parse_passport_pan":
        return {"passport_number": "A1234567", "pan_number": "ABCDE1234F"}
    elif tool_name == "parse_credit_report":
        return {"credit_score": 750, "emi_burden_pct": 30}
    elif tool_name == "parse_itr_fields":
        return {"annual_income": 1200000, "consistency_years": 3}
    elif tool_name == "parse_bank_statements":
        return {"average_balance": 50000, "overdraft_instances": 0}
    elif tool_name == "upload_blob":
        # Simulate a blob URL
        return "https://dummy.blob.core.windows.net/eligibility-reports/" + params.get("file_name", "report.json")
    else:
        return {}

