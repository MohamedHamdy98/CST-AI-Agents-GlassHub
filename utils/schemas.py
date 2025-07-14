# schemas.py
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pydantic import BaseModel
from typing import List, Optional
from enum import Enum

class ComplianceStatus(str, Enum):
    COMPLIANT = "COMPLIANT"
    NON_COMPLIANT = "NON-COMPLIANT"
    INDECISIVE = "INDECISIVE"

class LLMComplianceResult(BaseModel):
    compliance_status: ComplianceStatus
    flags: List[str] = []
    Brief_report: str = ""
    needs_human_review: bool = False

class ControlData(BaseModel):
    control_number: str
    control_name: str
    control_statement: str
    control_guidelines: str
    classification: List[str]
    expert_type: str
    standard_type: str

class ControlsRequest(BaseModel):
    controls: List[ControlData]