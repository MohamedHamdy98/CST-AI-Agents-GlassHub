# from pydantic import BaseModel, ValidationError
# from enum import Enum
# from typing import List
# import json

# # STEP 1: Schema
# class ComplianceStatus(str, Enum):
#     COMPLIANT = "COMPLIANT"
#     NON_COMPLIANT = "NON-COMPLIANT"
#     INDECISIVE = "INDECISIVE"

# class LLMComplianceResult(BaseModel):
#     compliance_status: ComplianceStatus
#     flags: List[str]
#     Brief_report: str
#     needs_human_review: bool

# # STEP 2: LLM response (as text)
# llm_response = '''json
# {
#     "compliance_status": "COMPLIANT",
#     "flags": [],
#     "Brief_report": "The control meets all the requirements.",
#     "needs_human_review": false
# }
# '''

# # STEP 3: Parsing it
# try:
#     parsed = LLMComplianceResult.model_validate_json(llm_response)
#     print("Parsed successfully!")
#     print(parsed.model_dump())
# except ValidationError as e:
#     print("❌ Invalid JSON format")
#     print(e)
control_number = 'AC-1.2'
control_display_number = control_number.replace(".", "_").replace("-", "_")
print(control_display_number)