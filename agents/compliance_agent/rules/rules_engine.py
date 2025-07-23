from typing import Dict, List
from dataclasses import dataclass
from enum import Enum

from .rule_definitions import ComplianceRule, INTERNAL_RULES, RBI_RULES, RuleCategory

class ComplianceRulesEngine:
    def __init__(self):
        self.internal_rules = {rule.rule_id: rule for rule in INTERNAL_RULES}
        self.rbi_rules = {rule.rule_id: rule for rule in RBI_RULES}

    async def validate_kyc_documents(self, documents: Dict) -> List[Dict]:
        violations = []
        required_docs = {"aadhaar", "pan"}

        # Check for required documents
        missing_docs = required_docs - set(documents.keys())
        if missing_docs:
            violations.append({
                "rule_id": "KYC001",
                "rule_category": RuleCategory.KYC.value,
                "severity": "HIGH",
                "message": f"Missing required KYC documents: {', '.join(missing_docs)}"
            })

        # For now, assume all provided documents are valid
        # In production, this would integrate with document verification services
        for doc_type, doc_info in documents.items():
            if hasattr(doc_info, 'document_type'):
                doc_path = doc_info.document_path
            else:
                doc_path = str(doc_info)

            if not doc_path or doc_path == "":
                violations.append({
                    "rule_id": "KYC001",
                    "rule_category": RuleCategory.KYC.value,
                    "severity": "HIGH",
                    "message": f"Invalid or missing {doc_type} document path"
                })

        return violations

    async def check_identity_consistency(self, documents: Dict) -> List[Dict]:
        violations = []

        # For demo purposes, simulate identity consistency check
        # In production, this would extract and compare names from actual documents
        doc_count = len(documents)
        if doc_count < 2:
            violations.append({
                "rule_id": "ID001",
                "rule_category": RuleCategory.IDENTITY.value,
                "severity": "MEDIUM",
                "message": "Insufficient documents to verify identity consistency"
            })

        # Simulate a 20% chance of name mismatch for demo
        import random
        if random.random() < 0.2:
            violations.append({
                "rule_id": "ID001",
                "rule_category": RuleCategory.IDENTITY.value,
                "severity": "MEDIUM",
                "message": "Name variations detected across documents - requires manual review"
            })

        return violations

    async def validate_income_documents(self, documents: Dict) -> List[Dict]:
        violations = []

        # Check for required income documents
        income_docs = {"salary_slip", "form16", "bank_statements"}
        provided_income_docs = [doc for doc in documents.keys() if doc in income_docs]

        if not provided_income_docs:
            violations.append({
                "rule_id": "INC001",
                "rule_category": RuleCategory.INCOME.value,
                "severity": "HIGH",
                "message": "No valid income proof document provided"
            })

        # For demo, simulate document validation
        for doc_type in provided_income_docs:
            # Simulate a 15% chance of invalid income document
            import random
            if random.random() < 0.15:
                violations.append({
                    "rule_id": "INC001",
                    "rule_category": RuleCategory.INCOME.value,
                    "severity": "HIGH",
                    "message": f"Invalid {doc_type}: Document appears to be tampered or illegible"
                })

        return violations

    async def check_rbi_compliance(self, application_data: Dict) -> List[Dict]:
        violations = []
        
        # Check creditworthiness (RBI-001)
        if "credit_score" not in application_data:
            violations.append({
                "rule_id": "RBI-001",
                "severity": "HIGH",
                "message": "Credit score assessment missing"
            })
        elif application_data["credit_score"] < 700:
            violations.append({
                "rule_id": "RBI-001",
                "severity": "HIGH",
                "message": f"Credit score {application_data['credit_score']} below minimum requirement (700)"
            })
        
        # Check income stability
        if not application_data.get("employment_verified", False):
            violations.append({
                "rule_id": "RBI-001",
                "severity": "MEDIUM",
                "message": "Employment history verification pending"
            })
        
        return violations

    async def run_all_checks(self, 
                           application_data: Dict, 
                           documents: Dict) -> tuple[bool, List[Dict], List[str]]:
        all_violations = []
        recommendations = []
        
        # Run KYC checks
        kyc_violations = await self.validate_kyc_documents(documents)
        all_violations.extend(kyc_violations)
        if kyc_violations:
            recommendations.append("Please provide all required KYC documents")
        
        # Run identity checks
        identity_violations = await self.check_identity_consistency(documents)
        all_violations.extend(identity_violations)
        if identity_violations:
            recommendations.append("Ensure consistent name across all documents")
        
        # Run income document checks
        income_violations = await self.validate_income_documents(documents)
        all_violations.extend(income_violations)
        if income_violations:
            recommendations.append("Provide valid income proof documents")
        
        # Run RBI compliance checks
        rbi_violations = await self.check_rbi_compliance(application_data)
        all_violations.extend(rbi_violations)
        if rbi_violations:
            recommendations.append("Address credit score and employment verification requirements")
        
        is_compliant = len(all_violations) == 0
        
        return is_compliant, all_violations, recommendations

class RuleCategory(Enum):
    DOCUMENT_VALIDITY = "Document Validity"  # Move to top
    KYC = "KYC Compliance"
    IDENTITY = "Identity Consistency"
    ADDRESS = "Address Verification"
    SIGNATURE = "Signature Validation"
    AGE = "Age Eligibility"
    INCOME = "Income Documentation"
    APPLICATION = "Loan Application Completeness"
    FORM = "Form Validity"
    FRAUD = "Document Fraud Prevention"
    COMPLIANCE = "Compliance Review"
    RBI = "RBI Regulation"