# schemas.py
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pydantic import BaseModel
from typing import List, Optional
from enum import Enum

# Report
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


class FilterTermsRequestEnterprise(BaseModel):
    path_load: str
    user_question: str
    is_licensed: str
    license_type: str
    regulations: str
    service_type: str
    k: int = 4

class FilterTermsRequestRegulator(BaseModel):
    path_load: str
    license_type: str
    regulations: str
    k: int = 4

# RAG
class FileURLsRag(BaseModel):
    urls: List[str]

class FileControlInput(BaseModel):
    url: str
    name_file: str

class FileURLs(BaseModel):
    files: List[FileControlInput]

# General Chat
class RequirementsControl(BaseModel):
    Audit_Instructions: List[str]

class ClauseInstructionChat(BaseModel):
    description_control: str
    requirements_control: RequirementsControl

class GeneralChat(BaseModel):
    title: str
    page: str
    source: str
    description: str
    clause_instruction: ClauseInstructionChat
    clause_audit_instruction: str

