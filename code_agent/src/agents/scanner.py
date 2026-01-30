"""Scanner Agent for code structure analysis and issue detection."""

import ast
import json
import logging
import re
import time
from typing import Dict, List, Any, Optional
import schemas
from llm_client import LLMClient

logger = logging.getLogger(__name__)


class ScannerAgent:
    """Agent for scanning Python code to extract structure and identify issues."""
    
    # Prompts as class-level constants (PEP 8 compliant)
    STRUCTURE_ANALYSIS_PROMPT = (
        "You are a code analysis expert. Analyze the provided Python code "
        "and extract:\n"
        "1. All function names\n"
        "2. All class names\n"
        "3. All imports\n\n"
        "Return ONLY a JSON object with this exact structure:\n"
        "{\n"
        '  "functions": ["list", "of", "function", "names"],\n'
        '  "classes": ["list", "of", "class", "names"],\n'
        '  "imports": ["list", "of", "imported", "modules"]\n'
        "}"
    )

    ISSUE_DETECTION_PROMPT = (
        "Analyze this Python code for potential issues.\n"
        'Return ONLY a JSON object with an "issues" array:\n'
        "{\n"
        '  "issues": [\n'
        "    {\n"
        '      "type": "bug|style|performance|security",\n'
        '      "description": "description of the issue",\n'
        '      "severity": "low|medium|high|critical"\n'
        "    }\n"
        "  ]\n"
        "}"
    )
    
    # Security patterns to detect potentially malicious code
    DANGEROUS_PATTERNS = [
        r'__import__\s*\(',
        r'eval\s*\(',
        r'exec\s*\(',
        r'compile\s*\(',
        r'open\s*\([^)]*["\']w',  # Write mode file operations
        r'os\.system\s*\(',
        r'subprocess\.',
        r'__builtins__',
    ]
    
    def __init__(self, max_code_size: int = 500_000, rate_limit_calls: int = 10, 
                 rate_limit_window: int = 60):
        """Initialize the Scanner Agent.
        
        Args:
            max_code_size: Maximum code size in bytes (default 500KB)
            rate_limit_calls: Max LLM calls per time window
            rate_limit_window: Time window in seconds for rate limiting
        """
        self.llm = LLMClient()
        self.max_code_size = max_code_size
        self.rate_limit_calls = rate_limit_calls
        self.rate_limit_window = rate_limit_window
        self._call_timestamps: List[float] = []
        logger.debug("ScannerAgent initialized with max_code_size=%d, "
                    "rate_limit=%d calls per %ds", 
                    max_code_size, rate_limit_calls, rate_limit_window)
    
    def _check_rate_limit(self) -> None:
        """Enforce rate limiting for LLM calls.
        
        Raises:
            RuntimeError: If rate limit is exceeded
        """
        current_time = time.time()
        # Remove timestamps outside the window
        self._call_timestamps = [
            ts for ts in self._call_timestamps 
            if current_time - ts < self.rate_limit_window
        ]
        
        if len(self._call_timestamps) >= self.rate_limit_calls:
            logger.warning("Rate limit exceeded: %d calls in %ds window",
                          len(self._call_timestamps), self.rate_limit_window)
            raise RuntimeError(
                f"Rate limit exceeded: {self.rate_limit_calls} calls per "
                f"{self.rate_limit_window} seconds"
            )
        
        self._call_timestamps.append(current_time)
        logger.debug("Rate limit check passed: %d/%d calls", 
                    len(self._call_timestamps), self.rate_limit_calls)
    
    def _validate_code(self, code: str) -> None:
        """Validate and sanitize code input.
        
        Args:
            code: Source code to validate
            
        Raises:
            ValueError: If code is empty, too large, or contains dangerous patterns
        """
        if not code or not code.strip():
            raise ValueError("Code input is empty")
        
        if len(code) > self.max_code_size:
            raise ValueError(
                f"Code input too large ({len(code)} bytes). "
                f"Maximum allowed: {self.max_code_size} bytes"
            )
        
        # Check for potentially malicious code patterns
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, code, re.IGNORECASE):
                logger.warning("Potentially dangerous pattern detected: %s", pattern)
                # Note: We log but don't block to avoid false positives
                # In production, consider stricter handling
        
        logger.debug("Code validated: %d bytes", len(code))
    
    def _validate_syntax(self, code: str) -> None:
        """Parse code with AST for syntax validation.
        
        Args:
            code: Source code to parse
            
        Raises:
            SyntaxError: If code has syntax errors
        """
        try:
            ast.parse(code)
            logger.debug("Syntax validation successful")
        except SyntaxError as e:
            logger.error("Syntax error at line %d: %s", e.lineno, e.msg)
            raise
    
    def _parse_json_response(self, response: str, context: str) -> Dict[str, Any]:
        """Parse and validate JSON response from LLM.
        
        Args:
            response: JSON string from LLM
            context: Context description for error messages
            
        Returns:
            Parsed JSON data
            
        Raises:
            ValueError: If response is not valid JSON
        """
        if not response or not response.strip():
            raise ValueError(f"{context}: Empty response from LLM")
        
        try:
            data = json.loads(response)
            logger.debug("%s: JSON parsed successfully", context)
            return data
        except json.JSONDecodeError as e:
            logger.error("%s: Invalid JSON at position %d: %s", 
                        context, e.pos, e.msg)
            raise ValueError(f"{context}: Invalid JSON response") from e
    
    def _validate_structure_data(self, data: Dict[str, Any]) -> Dict[str, List[str]]:
        """Validate and normalize structure data from LLM.
        
        Args:
            data: Parsed structure data
            
        Returns:
            Validated structure data with all required fields
        """
        required_fields = {"functions", "classes", "imports"}
        missing_fields = required_fields - set(data.keys())
        
        if missing_fields:
            logger.warning("Missing fields in structure data: %s", missing_fields)
            for field in missing_fields:
                data[field] = []
        
        # Ensure all fields are lists
        for field in required_fields:
            if not isinstance(data[field], list):
                logger.warning("Field '%s' is not a list, converting", field)
                data[field] = []
        
        return {k: data[k] for k in required_fields}
    
    def _optimize_code_for_analysis(self, code: str, max_length: int = 10000) -> str:
        """Optimize code input for LLM analysis by truncating if needed.
        
        Args:
            code: Source code
            max_length: Maximum code length to send to LLM
            
        Returns:
            Optimized code (truncated if necessary)
        """
        if len(code) <= max_length:
            return code
        
        # Truncate intelligently - try to preserve complete lines
        truncated = code[:max_length]
        last_newline = truncated.rfind('\n')
        if last_newline > max_length * 0.8:  # If we can keep 80%+ with clean line
            truncated = truncated[:last_newline]
        
        logger.info("Code truncated from %d to %d bytes for analysis", 
                   len(code), len(truncated))
        return truncated
    
    def _extract_code_structure(self, code: str) -> schemas.CodeStructure:
        """Extract code structure using LLM.
        
        Args:
            code: Source code to analyze
            
        Returns:
            CodeStructure with extracted information
            
        Raises:
            RuntimeError: If rate limit is exceeded
            ValueError: If LLM response is invalid
        """
        self._check_rate_limit()
        
        # Optimize code length for LLM
        optimized_code = self._optimize_code_for_analysis(code)
        user_prompt = f"Analyze this Python code:\n\n```python\n{optimized_code}\n```"
        
        try:
            response = self.llm.generate_completion(
                system_prompt=self.STRUCTURE_ANALYSIS_PROMPT,
                user_prompt=user_prompt,
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            # Parse and validate JSON
            structure_data = self._parse_json_response(response, "Structure extraction")
            validated_data = self._validate_structure_data(structure_data)
            
            # Create schema
            structure = schemas.CodeStructure(**validated_data)
            logger.info("Extracted: %d functions, %d classes, %d imports",
                       len(structure.functions), len(structure.classes), 
                       len(structure.imports))
            return structure
            
        except ValueError as e:
            logger.error("Structure extraction failed: %s", e)
            raise
        except Exception as e:
            logger.error("Unexpected error in structure extraction: %s", e)
            raise RuntimeError(f"Structure extraction failed: {e}") from e
    
    def _validate_issue(self, issue: Any, index: int) -> Optional[schemas.CodeIssue]:
        """Validate and create a CodeIssue from parsed data.
        
        Args:
            issue: Issue data (should be a dictionary)
            index: Issue index for logging
            
        Returns:
            CodeIssue if valid, None otherwise
        """
        if not isinstance(issue, dict):
            logger.warning("Issue %d is not a dict, skipping", index)
            return None
        
        required = {"type", "description", "severity"}
        if not required.issubset(issue.keys()):
            missing = required - set(issue.keys())
            logger.warning("Issue %d missing fields %s, skipping", index, missing)
            return None
        
        try:
            return schemas.CodeIssue(**issue)
        except Exception as e:
            logger.warning("Issue %d validation failed: %s", index, e)
            return None
    
    def _identify_issues(self, code: str) -> List[schemas.CodeIssue]:
        """Identify code issues using LLM analysis.
        
        Args:
            code: Source code to analyze
            
        Returns:
            List of identified code issues
            
        Raises:
            RuntimeError: If rate limit is exceeded
            ValueError: If LLM response is invalid
        """
        self._check_rate_limit()
        
        # Optimize code length for LLM
        optimized_code = self._optimize_code_for_analysis(code)
        user_prompt = f"Code to analyze:\n\n```python\n{optimized_code}\n```"
        
        try:
            response = self.llm.generate_completion(
                system_prompt=self.ISSUE_DETECTION_PROMPT,
                user_prompt=user_prompt,
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            # Parse JSON
            issues_data = self._parse_json_response(response, "Issue detection")
            
            # Extract issues list
            if "issues" in issues_data:
                issues_list = issues_data["issues"]
            elif isinstance(issues_data, list):
                issues_list = issues_data
            else:
                logger.warning("Unexpected issues format: %s", type(issues_data))
                raise ValueError("Invalid issues response format")
            
            if not isinstance(issues_list, list):
                logger.warning("Issues is not a list: %s", type(issues_list))
                raise ValueError("Issues must be a list")
            
            # Validate each issue
            validated_issues = []
            for idx, issue in enumerate(issues_list):
                validated = self._validate_issue(issue, idx)
                if validated:
                    validated_issues.append(validated)
            
            logger.info("Identified %d valid issues", len(validated_issues))
            return validated_issues
            
        except ValueError as e:
            logger.error("Issue detection failed: %s", e)
            raise
        except Exception as e:
            logger.error("Unexpected error in issue detection: %s", e)
            raise RuntimeError(f"Issue detection failed: {e}") from e
    
    def run(self, code: str) -> schemas.ScanResult:
        """Scan code to extract structure and identify issues.
        
        Args:
            code: Source code to scan
            
        Returns:
            ScanResult with code structure and issues
            
        Raises:
            ValueError: If code input is invalid
            SyntaxError: If code has syntax errors
            RuntimeError: If rate limit is exceeded or LLM fails
        """
        logger.info("Starting code scan")
        
        try:
            # Validate input
            self._validate_code(code)
            
            # Validate syntax
            self._validate_syntax(code)
            
            # Extract structure
            structure = self._extract_code_structure(code)
            
            # Identify issues
            issues = self._identify_issues(code)
            
            # Create result
            result = schemas.ScanResult(structure=structure, issues=issues)
            
            logger.info("Scan complete: %d functions, %d classes, %d issues",
                       len(structure.functions), len(structure.classes), len(issues))
            
            return result
            
        except (ValueError, SyntaxError, RuntimeError) as e:
            logger.error("Scan failed: %s", e)
            raise
