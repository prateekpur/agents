import schemas


class Orchestrator:
    def __init__(self):
        # Lazy imports to avoid circular dependency
        from agents.scanner import ScannerAgent
        from agents.analysis import AnalysisAgent
        from agents.style import StyleAgent
        from agents.planner import PlannerAgent
        
        self.scanner = ScannerAgent()
        self.analysis = AnalysisAgent()
        self.style = StyleAgent()
        self.planner = PlannerAgent()

    def run(self, code: str) -> schemas.RefactorPlan:
        scan_result = self.scanner.run(code)

        analysis_issues = self.analysis.run({
            "code": code,
            "scan": scan_result
        })

        style_issues = self.style.run({
            "code": code,
            "scan": scan_result
        })

        plan = self.planner.run({
            "scan": scan_result,
            "analysis_issues": analysis_issues,
            "style_issues": style_issues
        })

        return plan