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

import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.helper_functions import load_python_module

controls_content = load_python_module(file_path=r"H:\GlassHub\glasshub\temp_uploads\Sadeem_controls.py")
control_number = "control_AC_1"
print(f"{controls_content}.{control_number}")
