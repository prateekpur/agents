from typing import List
import json
import logging
import schemas
from llm_client import LLMClient

logger = logging.getLogger(__name__)


class StyleAgent:
    def __init__(self):
        self.llm = LLMClient()
    
    def run(self, data: dict) -> List[schemas.CodeIssue]:
        """
        Analyze code style and quality using LLM.
        
        Args:
            data: Dictionary with 'code' and 'scan' (ScanResult) keys
            
        Returns:
            List of CodeIssue objects focused on style and quality
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
"""
        
        system_prompt = """You are a code style expert specializing in Python best practices. 
Focus on:
- PEP 8 compliance
- Naming conventions
- Code organization and structure
- Documentation and comments
- Readability and maintainability
- Function/method length and complexity
- DRY principle violations

Return ONLY a JSON object with an "issues" array:
{
  "issues": [
    {
      "type": "style",
      "description": "Clear description of the style issue",
      "severity": "low|medium|high"
    }
  ]
}"""

        user_prompt = f"""Review this code for style and quality issues:

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
            
            logger.info(f"Found {len(issues)} style issues")
            return issues
            
        except Exception as e:
            logger.error(f"Error analyzing code style: {e}")
            return []
