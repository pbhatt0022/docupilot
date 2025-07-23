from typing import Dict, List
from dataclasses import dataclass
from enum import Enum

class RuleCategory(Enum):
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
    DOCUMENT_VALIDITY = "Document Validity"  

@dataclass
class ComplianceRule:
    rule_id: str
    category: RuleCategory
    title: str
    content: str
    entity: str = None
    source: str = None

# Internal Rules
INTERNAL_RULES = [
    ComplianceRule(
        rule_id="KYC001",
        category=RuleCategory.KYC,
        title="Mandatory KYC Verification",
        content="Every loan application must include valid KYC documents such as Passport, PAN Card, Voter ID. Documents must be verified using Form Recognizer or internal verification agents."
    ),
    ComplianceRule(
        rule_id="ID001",
        category=RuleCategory.IDENTITY,
        title="Name Consistency Across Documents",
        content="Applicant's full name must match exactly across all submitted identity and income documents. Minor spelling variations must be flagged for manual review."
    ),
    ComplianceRule(
        rule_id="ADDR001",
        category=RuleCategory.ADDRESS,
        title="Address Confirmation",
        content="At least one identity document must contain a complete and valid address. Address should match the address mentioned in the loan application form. Any mismatch should trigger a review."
    ),
    ComplianceRule(
        rule_id="SIG001",
        category=RuleCategory.SIGNATURE,
        title="Signature Matching",
        content="Applicant's signature must match across the loan application form and supporting documents such as Passport or PAN. Use digital signature comparison tools when available."
    ),
    ComplianceRule(
        rule_id="AGE001",
        category=RuleCategory.AGE,
        title="Minimum and Maximum Age",
        content="Applicants must be between 21 and 58 years old at the time of application. DOB should be parsed from Passport, PAN, or Voter ID and validated against this range."
    ),
    ComplianceRule(
        rule_id="INC001",
        category=RuleCategory.INCOME,
        title="Income Proof Requirement",
        content="At least one valid income document must be submitted (Salary Slip, Bank Statement, Income Tax Return, Form 16). Each must include employer name, salary/net income, and recent date (within 3 months)."
    ),
    ComplianceRule(
        rule_id="APP001",
        category=RuleCategory.APPLICATION,
        title="Mandatory Fields in Loan Form",
        content="Loan Application Form must contain Applicant Name, Loan Amount Requested, Application Date, and Signature. Missing fields must be flagged as 'incomplete'."
    ),
    ComplianceRule(
        rule_id="FORM001",
        category=RuleCategory.FORM,
        title="Form Freshness",
        content="Loan Application Form and supporting documents must be dated within the last 6 months to be considered valid."
    ),
    ComplianceRule(
        rule_id="FRD001",
        category=RuleCategory.FRAUD,
        title="Forgery and Tampering Detection",
        content="Any signs of digital tampering, overwriting, or image artifacts should trigger an automatic flag for fraud detection."
    ),
    ComplianceRule(
        rule_id="CMP001",
        category=RuleCategory.COMPLIANCE,
        title="Final Compliance Check",
        content="All required fields must be extracted, verified, and marked 'complete' before a document can be approved by the loan officer. Missing or uncertain fields must be listed with reasoning."
    ),
]

# RBI Rules
RBI_RULES = [
    ComplianceRule(
        rule_id="RBI-001",
        category=RuleCategory.RBI,
        title="Eligibility & Creditworthiness",
        content="Lenders must assess creditworthiness using credit score, income stability, employment history, and existing debts.",
        entity="Borrower",
        source="RBI Guidelines for Personal Loans"
    ),
    ComplianceRule(
        rule_id="RBI-002",
        category=RuleCategory.RBI,
        title="Credit Information",
        content="Lenders must use credit information companies (e.g., CIBIL) to obtain credit scores and reports.",
        entity="Lender",
        source="RBI Guidelines for Personal Loans"
    ),
    ComplianceRule(
        rule_id="RBI-003",
        category=RuleCategory.RBI,
        title="Interest Rates Transparency",
        content="Interest rates must be disclosed transparently, including the Annual Percentage Rate (APR).",
        entity="Lender",
        source="RBI Guidelines for Personal Loans"
    ),
    ComplianceRule(
        rule_id="RBI-004",
        category=RuleCategory.RBI,
        title="Communication of Loan Terms",
        content="Loan terms and repayment schedules must be clearly communicated in the borrower’s preferred language.",
        entity="Lender",
        source="Fair Practices Code (FPC)"
    ),
    ComplianceRule(
        rule_id="RBI-005",
        category=RuleCategory.RBI,
        title="Non-Discrimination & Harassment",
        content="Lenders must avoid discrimination based on caste, religion, or gender and must not harass borrowers.",
        entity="Lender",
        source="Fair Practices Code (FPC)"
    ),
    ComplianceRule(
        rule_id="RBI-006",
        category=RuleCategory.RBI,
        title="Loan Processing & Disclosure",
        content="Loan applications must be acknowledged with timelines provided. Loan terms must be disclosed in full.",
        entity="Lender",
        source="RBI Processing Guidelines"
    ),
    ComplianceRule(
        rule_id="RBI-007",
        category=RuleCategory.RBI,
        title="Foreclosure & Prepayment",
        content="Borrowers must be allowed to prepay or foreclose loans, with charges communicated in advance.",
        entity="Borrower",
        source="RBI Foreclosure Rules"
    ),
    ComplianceRule(
        rule_id="RBI-008",
        category=RuleCategory.RBI,
        title="Grievance Redressal",
        content="Lenders must resolve complaints within 30 days and provide escalation paths including Ombudsman.",
        entity="Lender",
        source="RBI Grievance Redressal Guidelines"
    ),
    ComplianceRule(
        rule_id="RBI-009",
        category=RuleCategory.RBI,
        title="Data Privacy",
        content="Lenders must ensure data privacy, obtain explicit borrower consent for non-loan-related data usage.",
        entity="Lender",
        source="RBI Digital Lending Guidelines"
    ),
    ComplianceRule(
        rule_id="RBI-010",
        category=RuleCategory.RBI,
        title="Debt Restructuring Options",
        content="During financial distress, lenders must offer restructuring options like tenure extension or lower interest.",
        entity="Borrower",
        source="RBI Restructuring Guidelines"
    ),
    ComplianceRule(
        rule_id="RBI-011",
        category=RuleCategory.RBI,
        title="Monitoring & Internal Reporting",
        content="Banks must submit regular loan portfolio reports and conduct internal audits for RBI compliance.",
        entity="Lender",
        source="RBI Compliance Framework"
    ),
]