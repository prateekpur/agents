from pydantic import BaseModel
from typing import List, Optional

class CodeStructure(BaseModel):
    functions: List[str]
    classes: List[str]
    imports: List[str]

class CodeIssue(BaseModel):
    type: str          # e.g. "bug", "style", "performance"
    description: str
    line: Optional[int] = None
    severity: str      # low | medium | high

class ScanResult(BaseModel):
    structure: CodeStructure
    issues: List[CodeIssue]

class RefactorStep(BaseModel):
    step: int
    action: str
    rationale: str

class RefactorPlan(BaseModel):
    summary: str
    steps: List[RefactorStep]
