import json
import logging
import schemas
from llm_client import LLMClient

logger = logging.getLogger(__name__)


class PlannerAgent:
    def __init__(self):
        self.llm = LLMClient()
    
    def run(self, data: dict) -> schemas.RefactorPlan:
        """
        Create a refactoring plan using LLM based on identified issues.
        
        Args:
            data: Dictionary with 'scan', 'analysis_issues', and 'style_issues' keys
            
        Returns:
            RefactorPlan with summary and ordered steps
        """
        scan_result = data.get("scan")
        analysis_issues = data.get("analysis_issues", [])
        style_issues = data.get("style_issues", [])
        
        # Build comprehensive context
        all_issues = []
        
        if scan_result and scan_result.issues:
            all_issues.extend([
                f"[{issue.severity}] {issue.type}: {issue.description}" 
                for issue in scan_result.issues
            ])
        
        all_issues.extend([
            f"[{issue.severity}] {issue.type}: {issue.description}" 
            for issue in analysis_issues
        ])
        
        all_issues.extend([
            f"[{issue.severity}] {issue.type}: {issue.description}" 
            for issue in style_issues
        ])
        
        issues_text = "\n".join(all_issues) if all_issues else "No issues identified"
        
        system_prompt = """You are an expert software architect creating refactoring plans.
Based on the identified issues, create a prioritized step-by-step refactoring plan.

Prioritize steps by:
1. Critical security and bug fixes first
2. High-severity issues next
3. Code quality and style improvements last

Return ONLY a JSON object with this structure:
{
  "summary": "Brief 1-2 sentence summary of what the refactoring achieves",
  "steps": [
    {
      "step": 1,
      "action": "Clear, actionable description of what to do",
      "rationale": "Why this step is important"
    }
  ]
}"""

        user_prompt = f"""Create a refactoring plan for code with these issues:

{issues_text}

Create a logical, prioritized plan that addresses all issues efficiently."""

        try:
            response = self.llm.generate_completion(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.4,
                response_format={"type": "json_object"}
            )
            
            plan_data = json.loads(response)
            
            # Parse steps
            steps = [
                schemas.RefactorStep(**step) 
                for step in plan_data.get("steps", [])
            ]
            
            plan = schemas.RefactorPlan(
                summary=plan_data.get("summary", "Refactoring plan to address identified issues"),
                steps=steps
            )
            
            logger.info(f"Created refactoring plan with {len(steps)} steps")
            return plan
            
        except Exception as e:
            logger.error(f"Error creating refactoring plan: {e}")
            # Return a basic fallback plan
            return schemas.RefactorPlan(
                summary="Address identified issues",
                steps=[
                    schemas.RefactorStep(
                        step=1,
                        action="Review and fix all identified issues",
                        rationale="Improve code quality and correctness"
                    )
                ]
            )
