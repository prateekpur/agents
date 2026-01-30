from typing import List
import json
import logging
import schemas
from llm_client import LLMClient

logger = logging.getLogger(__name__)


class AnalysisAgent:
    def __init__(self):
        self.llm = LLMClient()
    
    def run(self, data: dict) -> List[schemas.CodeIssue]:
        """
        Perform deep analysis on code using LLM to find bugs and logic issues.
        
        Args:
            data: Dictionary with 'code' and 'scan' (ScanResult) keys
            
        Returns:
            List of CodeIssue objects focused on bugs and logic errors
        """
        code = data.get("code", "")
        scan_result = data.get("scan")
        
        # Build context from scan results
        context = ""
        if scan_result:
            context = f"""
Code Structure:
- Functions: {', '.join(scan_result.structure.functions)}
- Classes: {', '.join(scan_result.structure.classes)}
- Imports: {', '.join(scan_result.structure.imports)}

Previously identified issues:
{[issue.description for issue in scan_result.issues]}
"""
        
        system_prompt = """You are an expert code analyzer specializing in finding bugs, logic errors, 
security vulnerabilities, and correctness issues. Focus on:
- Input validation problems
- Edge cases and boundary conditions
- Logic errors and incorrect implementations
- Security vulnerabilities
- Error handling issues
- Type safety problems

Return ONLY a JSON object with an "issues" array:
{
  "issues": [
    {
      "type": "bug|security|logic",
      "description": "Clear description of the issue",
      "severity": "low|medium|high|critical"
    }
  ]
}"""

        user_prompt = f"""Analyze this code for bugs and logic issues:

{context}

Code:
```python
{code}
```"""

        try:
            response = self.llm.generate_completion(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            issues_data = json.loads(response)
            issues_list = issues_data.get("issues", [])
            issues = [schemas.CodeIssue(**issue) for issue in issues_list]
            
            logger.info(f"Found {len(issues)} analysis issues")
            return issues
            
        except Exception as e:
            logger.error(f"Error analyzing code: {e}")
            return []
