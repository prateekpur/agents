"""Scanner Agent for code structure analysis and issue detection."""

# Standard library imports
import ast
import json
import logging
import os
import re
import textwrap
from typing import Any, Dict, List, Optional

# Third-party imports
import openai

# Local imports
import schemas
from agents.rate_limiter import RateLimiter
from agents.scanner_config import (
    DANGEROUS_PATTERNS,
    DEFAULT_MAX_ANALYSIS_LENGTH,
    DEFAULT_MAX_CODE_SIZE,
    DEFAULT_RATE_LIMIT_CALLS,
    DEFAULT_RATE_LIMIT_WINDOW,
    ISSUE_DETECTION_PROMPT,
    STRUCTURE_ANALYSIS_PROMPT,
    TRUNCATION_THRESHOLD,
)
from agents.scanner_exceptions import (
    APIRateLimitError,
    CodeSizeError,
    CodeValidationError,
    DangerousCodeError,
    IssueDetectionError,
    LLMResponseError,
    StructureExtractionError,
)
from llm_client import LLMClient

logger = logging.getLogger(__name__)


class ScannerAgent:
    """Scans Python code to extract structure and identify issues."""
    
    # Maximum line length to prevent LLM processing issues
    MAX_LINE_LENGTH = 1000
    
    # Required fields for issue validation
    REQUIRED_ISSUE_FIELDS = ("type", "description", "severity")
    
    # Environment variable constants
    ENV_VAR_SCANNER_PRODUCTION = "SCANNER_PRODUCTION"
    ENV_VALUE_TRUE = "true"
    ENV_VALUE_FALSE = "false"
    
    # Pre-compiled regex patterns for performance (class-level)
    _compiled_patterns: Optional[List[re.Pattern]] = None
    
    def __init__(
        self,
        max_code_size: int = DEFAULT_MAX_CODE_SIZE,
        rate_limit_calls: int = DEFAULT_RATE_LIMIT_CALLS,
        rate_limit_window: int = DEFAULT_RATE_LIMIT_WINDOW,
        block_dangerous_patterns: Optional[bool] = None,
    ):
        """Initialize the Scanner Agent.
        
        Args:
            max_code_size: Maximum code size in bytes
            rate_limit_calls: Max LLM calls per time window
            rate_limit_window: Time window in seconds for rate limiting
            block_dangerous_patterns: If True, blocks dangerous code patterns.
                If None, uses environment variable SCANNER_PRODUCTION (default: False)
        """
        self.llm = LLMClient()
        self.max_code_size = max_code_size
        
        # Determine production mode
        if block_dangerous_patterns is None:
            block_dangerous_patterns = (
                os.getenv(
                    self.ENV_VAR_SCANNER_PRODUCTION, 
                    self.ENV_VALUE_FALSE
                ).lower() == self.ENV_VALUE_TRUE
            )
        self.block_dangerous_patterns = block_dangerous_patterns
        
        # Initialize rate limiter
        self.rate_limiter = RateLimiter(rate_limit_calls, rate_limit_window)
        
        # Compile regex patterns once for performance
        if ScannerAgent._compiled_patterns is None:
            ScannerAgent._compiled_patterns = [
                re.compile(pattern, re.IGNORECASE) 
                for pattern in DANGEROUS_PATTERNS
            ]
        
        logger.debug(
            f"ScannerAgent initialized: max_code_size={max_code_size}, "
            f"rate_limit={rate_limit_calls} calls per {rate_limit_window}s, "
            f"block_dangerous_patterns={block_dangerous_patterns}"
        )
    
    def _sanitize_code_for_logging(self, code: str, max_length: int = 200) -> str:
        """Sanitize code for safe logging.
        
        Args:
            code: Code to sanitize
            max_length: Maximum length of sanitized output (default: 200)
            
        Returns:
            Sanitized code snippet safe for logging
        """
        # Replace newlines and carriage returns with spaces for readability
        sanitized = code.replace("\n", " ").replace("\r", "")
        
        # Use textwrap.shorten for better truncation
        return textwrap.shorten(sanitized, width=max_length, placeholder="...")
    
    def _extract_retry_after(self, error_str: str) -> Optional[int]:
        """Extract retry-after seconds from error message.
        
        Args:
            error_str: Error message string
            
        Returns:
            Number of seconds to wait, or None if not found
        """
        if not error_str:
            logger.debug("Empty error string provided to _extract_retry_after")
            return None
        
        try:
            wait_match = re.search(r"wait (\d+) seconds", error_str)
            if wait_match:
                retry_seconds = int(wait_match.group(1))
                logger.debug(f"Extracted retry_after: {retry_seconds} seconds")
                return retry_seconds
            else:
                logger.debug("No retry-after pattern found in error message")
                return None
        except (ValueError, IndexError) as e:
            logger.warning(f"Failed to parse retry_after from error: {e}")
            return None
    
    def _format_time_duration(self, seconds: int) -> str:
        """Format seconds into human-readable duration.
        
        Args:
            seconds: Duration in seconds
            
        Returns:
            Formatted duration string (e.g., '2h 30m', '45m 10s', '30s')
        """
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        remaining_seconds = seconds % 60
        
        if hours > 0:
            return f"{hours}h {minutes}m"
        elif minutes > 0:
            return f"{minutes}m {remaining_seconds}s"
        else:
            return f"{remaining_seconds}s"
    
    def _format_rate_limit_message(self, retry_after: Optional[int]) -> str:
        """Format human-readable rate limit error message.
        
        Args:
            retry_after: Seconds to wait before retrying
            
        Returns:
            Formatted error message
        """
        if not retry_after:
            return "API rate limit exceeded. Please wait before retrying."
        
        time_str = self._format_time_duration(retry_after)
        return (
            f"API rate limit exceeded. Please wait {time_str} "
            f"({retry_after} seconds) before retrying."
        )
    
    def _sanitize_code_for_llm(self, code: str) -> str:
        """Sanitize code input before sending to LLM.
        
        Prevents injection attacks by escaping special characters that could
        break out of code blocks or manipulate the LLM prompt.
        
        Args:
            code: Code to sanitize
            
        Returns:
            Sanitized code safe for LLM processing
        """
        # Handle None input
        if code is None:
            return ""
        
        # Remove null bytes and other problematic characters
        sanitized = code.replace("\x00", "")  # Remove null bytes
        
        # Normalize all line endings to Unix style
        sanitized = sanitized.replace("\r\n", "\n").replace("\r", "\n")
        
        # Remove control characters except newlines, tabs, and carriage returns
        sanitized = "".join(
            char for char in sanitized 
            if char in "\n\t" or ord(char) >= 32 or ord(char) == 127
        )
        
        # Escape backticks to prevent code block breakout
        sanitized = sanitized.replace("```", "\\`\\`\\`")
        
        # Escape other potential injection vectors
        sanitized = sanitized.replace("\\x", "\\\\x")  # Escape hex escapes
        sanitized = sanitized.replace("\\u", "\\\\u")  # Escape unicode escapes
        sanitized = sanitized.replace("\\N", "\\\\N")  # Escape named unicode escapes
        sanitized = sanitized.replace("\\U", "\\\\U")  # Escape long unicode escapes
        
        # Escape potential prompt injection sequences
        sanitized = sanitized.replace("<|im_sep|>", "<|im\_sep|>")
        sanitized = sanitized.replace("<|im_end|>", "<|im\_end|>")
        sanitized = sanitized.replace("<|endoftext|>", "<|endoftext\_|>")
        
        # Remove ANSI escape codes that could manipulate terminal output
        sanitized = re.sub(r"\x1b\[[0-9;]*[a-zA-Z]", "", sanitized)
        
        # Limit consecutive newlines to prevent prompt manipulation
        while "\n\n\n\n" in sanitized:
            sanitized = sanitized.replace("\n\n\n\n", "\n\n\n")
        
        return sanitized
    
    def _check_dangerous_patterns(self, code: str) -> None:
        """Check code for dangerous patterns using pre-compiled regex.
        
        Args:
            code: Source code to check
            
        Raises:
            DangerousCodeError: If dangerous pattern found and blocking is enabled
        """
        # Ensure patterns are compiled (defensive check)
        if self._compiled_patterns is None:
            logger.warning(
                "Dangerous patterns not compiled - reinitializing"
            )
            # Handle empty DANGEROUS_PATTERNS list
            if not DANGEROUS_PATTERNS:
                logger.debug(
                    "No dangerous patterns configured - skipping pattern check"
                )
                ScannerAgent._compiled_patterns = []
                return
            
            ScannerAgent._compiled_patterns = [
                re.compile(pattern, re.IGNORECASE) 
                for pattern in DANGEROUS_PATTERNS
            ]
        
        # Skip check if no patterns configured
        if not self._compiled_patterns:
            return
        
        # Patterns guaranteed to be non-None after above check
        for compiled_pattern in self._compiled_patterns:
            match = compiled_pattern.search(code)
            if match:
                pattern_str = compiled_pattern.pattern
                if self.block_dangerous_patterns:
                    logger.error(
                        f"Dangerous pattern blocked: {pattern_str} at position {match.start()}"
                    )
                    raise DangerousCodeError(pattern_str)
                else:
                    logger.warning(
                        f"Potentially dangerous pattern detected: {pattern_str} "
                        f"at position {match.start()}"
                    )
    
    def _check_line_lengths(self, code: str) -> List[str]:
        """Check for overly long lines that might cause LLM issues.
        
        Args:
            code: Source code to check
            
        Returns:
            List of warning messages for lines exceeding maximum length
        """
        warnings = []
        lines = code.split("\n")
        for line_num, line in enumerate(lines, 1):
            if len(line) > self.MAX_LINE_LENGTH:
                warning_msg = (
                    f"Line {line_num} exceeds {self.MAX_LINE_LENGTH} characters "
                    f"({len(line)} chars) - may affect LLM processing"
                )
                warnings.append(warning_msg)
                logger.warning(warning_msg)
        return warnings
    
    def _validate_code(self, code: str) -> None:
        """Validate and sanitize code input.
        
        Args:
            code: Source code to validate
            
        Raises:
            CodeValidationError: If code is empty or has validation issues
            CodeSizeError: If code exceeds size limit
            DangerousCodeError: If dangerous patterns detected and blocking enabled
        """
        if not code or not code.strip():
            raise CodeValidationError("Code input is empty")
        
        if len(code) > self.max_code_size:
            raise CodeSizeError(len(code), self.max_code_size)
        
        # Check for overly long lines
        self._check_line_lengths(code)
        
        # Check for dangerous patterns
        self._check_dangerous_patterns(code)
        
        lines = code.split("\n")
        logger.debug(
            f"Code validation passed: {len(code)} bytes, {len(lines)} lines"
        )
    
    def _validate_syntax(self, code: str) -> None:
        """Parse code with AST for syntax validation.
        
        Args:
            code: Source code to parse
            
        Raises:
            SyntaxError: If code has syntax errors
        """
        try:
            ast.parse(code)
            logger.debug("Syntax validation: Code is syntactically valid")
        except SyntaxError as e:
            logger.error(
                f"Syntax validation failed: line {e.lineno}, col {e.offset} - {e.msg}"
            )
            raise
        except Exception as e:
            # Handle unexpected errors from ast.parse
            logger.error(
                f"Syntax validation error: Unexpected {type(e).__name__} - {e}",
                exc_info=True
            )
            raise SyntaxError(f"Failed to parse code: {e}") from e
    
    def _parse_json_response(self, response: str, context: str) -> Dict[str, Any]:
        """Parse and validate JSON response from LLM.
        
        Args:
            response: JSON string from LLM
            context: Context description for error messages
            
        Returns:
            Parsed JSON data (guaranteed to be a dictionary)
            
        Raises:
            LLMResponseError: If response is not valid JSON or not a dictionary
        """
        if not response or not response.strip():
            raise LLMResponseError(context, "Empty response from LLM")
        
        try:
            data = json.loads(response)
            
            # Validate that response is a dictionary
            if not isinstance(data, dict):
                logger.error(
                    f"{context}: Expected dict, got {type(data).__name__}"
                )
                raise LLMResponseError(
                    context, 
                    f"Invalid response structure: expected object, got {type(data).__name__}"
                )
            
            logger.debug(f"{context}: JSON parsed and validated successfully")
            return data
            
        except json.JSONDecodeError as e:
            # Log sanitized error without exposing full response
            logger.error(
                f"{context}: Invalid JSON at position {e.pos} - {e.msg}"
            )
            raise LLMResponseError(context, "Invalid JSON response") from e
    
    def _validate_field_types(
        self, 
        issue: Dict[str, Any],
        required_fields: Optional[tuple[str, ...]] = None
    ) -> bool:
        """Validate types of issue fields.
        
        Args:
            issue: Issue dictionary to validate
            required_fields: Tuple of field names that must be strings (defaults to class constant)
            
        Returns:
            True if all field types are valid, False otherwise
        """
        if required_fields is None:
            required_fields = self.REQUIRED_ISSUE_FIELDS
        
        for field in required_fields:
            if not isinstance(issue.get(field), str):
                return False
        return True
    
    def _has_required_fields(self, issue: Dict[str, Any], index: int) -> bool:
        """Check if issue has all required fields.
        
        Args:
            issue: Issue dictionary
            index: Issue index for logging
            
        Returns:
            True if all required fields present, False otherwise
        """
        required = {"type", "description", "severity"}
        if not required.issubset(issue.keys()):
            missing = required - set(issue.keys())
            logger.warning(
                f"Issue validation: Issue {index} missing fields {missing} - skipping"
            )
            return False
        return True
    
    def _create_code_issue(self, issue: Dict[str, Any], index: int) -> schemas.CodeIssue:
        """Create a CodeIssue instance from validated data.
        
        Args:
            issue: Validated issue dictionary
            index: Issue index for error logging
            
        Returns:
            CodeIssue instance
            
        Raises:
            ValueError: If schema validation fails
            TypeError: If data types are incorrect
        """
        try:
            return schemas.CodeIssue(**issue)
        except ValueError as e:
            logger.warning(
                f"Issue {index} schema validation failed (ValueError): {e}"
            )
            raise
        except TypeError as e:
            logger.warning(
                f"Issue {index} schema validation failed (TypeError): {e}"
            )
            raise
        except Exception as e:
            logger.error(
                f"Issue {index} unexpected validation error ({type(e).__name__}): {e}",
                exc_info=True
            )
            raise ValueError(f"Failed to create CodeIssue: {e}") from e
    
    def _is_valid_issue_dict(self, issue: Any, index: int) -> bool:
        """Check if issue is a valid dictionary.
        
        Args:
            issue: Issue data to check
            index: Issue index for logging
            
        Returns:
            True if issue is a dict, False otherwise
        """
        if not isinstance(issue, dict):
            logger.warning(f"Issue validation: Issue {index} is not a dict - skipping")
            return False
        return True
    
    def _validate_issue(self, issue: Any, index: int) -> Optional[schemas.CodeIssue]:
        """Validate and create a CodeIssue from parsed data.
        
        Validates that the issue is a dictionary with required fields
        (type, description, severity) and that all field values are strings.
        
        Args:
            issue: Issue data (expected to be a dictionary)
            index: Issue index for logging purposes
            
        Returns:
            CodeIssue instance if validation succeeds, None otherwise
        """
        # Early return if not a dict
        if not self._is_valid_issue_dict(issue, index):
            return None
        
        # Early return if missing required fields
        if not self._has_required_fields(issue, index):
            return None
        
        # Early return if invalid field types
        if not self._validate_field_types(issue):
            logger.warning(
                f"Issue validation: Issue {index} has invalid field types - skipping"
            )
            return None
        
        # Create and return CodeIssue instance
        try:
            return self._create_code_issue(issue, index)
        except Exception:
            # Error already logged in _create_code_issue
            return None
    
    def _validate_structure_data(self, data: Dict[str, Any]) -> Dict[str, List[str]]:
        """Validate and normalize structure data from LLM.
        
        Creates a new dictionary with validated data rather than modifying input.
        Ensures all required fields exist and are lists.
        
        Args:
            data: Parsed structure data from LLM
            
        Returns:
            New dictionary with validated structure data containing all required fields
        """
        required_fields = {"functions", "classes", "imports"}
        result = {}
        
        for field in required_fields:
            if field not in data:
                logger.warning(
                    f"Structure validation: Missing field '{field}' in LLM response, "
                    f"using empty list"
                )
                result[field] = []
            elif not isinstance(data[field], list):
                logger.warning(
                    f"Structure validation: Field '{field}' is {type(data[field]).__name__}, "
                    f"expected list, using empty list"
                )
                result[field] = []
            else:
                result[field] = data[field]
                logger.debug(
                    f"Structure validation: Field '{field}' validated with "
                    f"{len(data[field])} items"
                )
        
        return result
    
    def _truncate_at_line_boundary(self, code: str, max_length: int) -> str:
        """Truncate code at a line boundary if possible.
        
        Args:
            code: Code to truncate
            max_length: Maximum length allowed
            
        Returns:
            Truncated code at line boundary when feasible
        """
        truncated = code[:max_length]
        last_newline = truncated.rfind("\n")
        
        # Use line boundary if it keeps enough content (70% threshold)
        threshold = int(max_length * TRUNCATION_THRESHOLD)
        
        if last_newline > threshold:
            return truncated[:last_newline]
        
        # Return as-is (either at lower line boundary or no newline)
        return truncated
    
    def _optimize_code_for_analysis(
        self,
        code: str,
        max_length: int = DEFAULT_MAX_ANALYSIS_LENGTH
    ) -> str:
        """Optimize code input for LLM analysis by truncating if needed.
        
        Intelligently truncates code at line boundaries when possible to
        maintain code structure and readability.
        
        Args:
            code: Source code to optimize
            max_length: Maximum code length to send to LLM
            
        Returns:
            Optimized code (truncated if necessary)
        """
        if len(code) <= max_length:
            return code
        
        truncated = self._truncate_at_line_boundary(code, max_length)
        
        logger.info(
            f"Code truncated from {len(code)} to {len(truncated)} bytes for analysis"
        )
        return truncated
    
    def _invoke_llm_with_rate_limiting(self, system_prompt: str, user_prompt: str) -> str:
        """Invoke LLM with rate limiting and comprehensive error handling.
        
        Args:
            system_prompt: System prompt for LLM
            user_prompt: User prompt for LLM
            
        Returns:
            LLM response string
            
        Raises:
            RateLimitError: If internal rate limit exceeded
            APIRateLimitError: If API rate limit exceeded
        """
        # Check internal rate limit
        self.rate_limiter.check_and_increment()
        
        usage = self.rate_limiter.get_current_usage()
        logger.debug(
            f"Calling LLM ({usage}/{self.rate_limiter.max_calls} calls used)"
        )
        
        try:
            response = self.llm.generate_completion(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            logger.debug("LLM call successful")
            return response
            
        except openai.RateLimitError as e:
            # Extract wait time from error message
            retry_after = self._extract_retry_after(str(e))
            error_msg = self._format_rate_limit_message(retry_after)
            
            logger.error(f"LLM call failed: API rate limit exceeded - {str(e)}")
            raise APIRateLimitError(error_msg, retry_after=retry_after) from e
            
        except Exception as e:
            # Log unexpected errors with full context
            logger.error(
                f"LLM call failed: Unexpected {type(e).__name__} - {e}",
                exc_info=True
            )
            raise
    
    def _create_code_prompt(self, code: str, prefix: str) -> str:
        """Create a prompt with sanitized code.
        
        Args:
            code: Source code
            prefix: Prompt prefix
            
        Returns:
            Formatted prompt
        """
        sanitized_code = self._sanitize_code_for_llm(code)
        return f"{prefix}\n\n```python\n{sanitized_code}\n```"
    
    def _extract_code_structure(self, code: str) -> schemas.CodeStructure:
        """Extract code structure using LLM.
        
        Args:
            code: Source code to analyze
            
        Returns:
            CodeStructure: Object containing extracted functions, classes, and imports
            
        Raises:
            StructureExtractionError: If extraction fails
            RateLimitError: If rate limit is exceeded
            LLMResponseError: If LLM response is invalid
        """
        logger.debug("Beginning code structure extraction")
        
        try:
            # Optimize and sanitize code
            optimized_code = self._optimize_code_for_analysis(code)
            user_prompt = self._create_code_prompt(
                optimized_code, "Analyze this Python code:"
            )
            
            # Call LLM
            logger.debug("Sending structure extraction request to LLM")
            response = self._invoke_llm_with_rate_limiting(STRUCTURE_ANALYSIS_PROMPT, user_prompt)
            
            # Parse and validate response
            structure_data = self._parse_json_response(response, "Structure extraction")
            validated_data = self._validate_structure_data(structure_data)
            
            # Create schema
            structure = schemas.CodeStructure(**validated_data)
            logger.info(
                f"Structure extraction successful: "
                f"{len(structure.functions)} functions, "
                f"{len(structure.classes)} classes, "
                f"{len(structure.imports)} imports"
            )
            return structure
            
        except (LLMResponseError, APIRateLimitError):
            raise
        except Exception as e:
            logger.error(
                f"Structure extraction failed with {type(e).__name__}: {e}"
            )
            raise StructureExtractionError(
                f"Failed to extract code structure: {e}"
            ) from e
    
    def _extract_issues_list(self, issues_data: Dict[str, Any]) -> List[Any]:
        """Extract issues list from LLM response data.
        
        Args:
            issues_data: Parsed JSON data from LLM
            
        Returns:
            List of issue dictionaries
            
        Raises:
            LLMResponseError: If data format is invalid
        """
        # Handle both dict with 'issues' key and direct list
        if isinstance(issues_data, dict) and "issues" in issues_data:
            issues_list = issues_data["issues"]
        elif isinstance(issues_data, list):
            issues_list = issues_data
        else:
            raise LLMResponseError(
                "Issue detection",
                f"Invalid response format: expected dict with 'issues' key "
                f"or list, got {type(issues_data).__name__}"
            )
        
        # Validate that issues_list is actually a list
        if not isinstance(issues_list, list):
            raise LLMResponseError(
                "Issue detection",
                f"Issues must be a list, got {type(issues_list).__name__}"
            )
        
        return issues_list
    
    def _validate_issues_list(self, issues_list: List[Any]) -> List[schemas.CodeIssue]:
        """Validate each issue in the list.
        
        Args:
            issues_list: List of issue data
            
        Returns:
            List of validated CodeIssue objects
        """
        validated_issues = []
        for idx, issue in enumerate(issues_list):
            validated = self._validate_issue(issue, idx)
            if validated:
                validated_issues.append(validated)
        return validated_issues
    
    def _identify_issues(self, code: str) -> List[schemas.CodeIssue]:
        """Identify code issues using LLM analysis.
        
        Args:
            code: Source code to analyze
            
        Returns:
            List[CodeIssue]: List of identified and validated code issues
            
        Raises:
            IssueDetectionError: If issue detection fails
            RateLimitError: If rate limit is exceeded
            LLMResponseError: If LLM response is invalid
        """
        logger.debug("Beginning issue detection")
        
        try:
            # Optimize and sanitize code
            optimized_code = self._optimize_code_for_analysis(code)
            user_prompt = self._create_code_prompt(optimized_code, "Code to analyze:")
            
            # Call LLM
            logger.debug("Sending issue detection request to LLM")
            response = self._invoke_llm_with_rate_limiting(ISSUE_DETECTION_PROMPT, user_prompt)
            
            # Parse response
            issues_data = self._parse_json_response(response, "Issue detection")
            
            # Extract and validate issues list
            issues_list = self._extract_issues_list(issues_data)
            validated_issues = self._validate_issues_list(issues_list)
            
            logger.info(
                f"Issue detection complete: {len(validated_issues)} valid issues found "
                f"({len(issues_list) - len(validated_issues)} invalid skipped)"
            )
            return validated_issues
            
        except (LLMResponseError, APIRateLimitError):
            raise
        except Exception as e:
            logger.error(f"Issue detection failed with {type(e).__name__}: {e}")
            raise IssueDetectionError(f"Failed to identify issues: {e}") from e
    
    def _validate_code_completely(self, code: str) -> None:
        """Perform comprehensive validation checks on code.
        
        Validates code structure, size, patterns, and syntax.
        
        Args:
            code: Source code to validate
            
        Raises:
            CodeValidationError: If validation fails
            DangerousCodeError: If dangerous patterns detected
            SyntaxError: If syntax is invalid
        """
        self._validate_code(code)
        self._validate_syntax(code)
    
    def _extract_structure_and_issues(
        self,
        code: str
    ) -> tuple[schemas.CodeStructure, List[schemas.CodeIssue]]:
        """Extract code structure and identify issues.
        
        Args:
            code: Source code to analyze
            
        Returns:
            Tuple of (CodeStructure, List[CodeIssue])
        """
        structure = self._extract_code_structure(code)
        issues = self._identify_issues(code)
        return structure, issues
    
    def run(self, code: str) -> schemas.ScanResult:
        """Scan code to extract structure and identify issues.
        
        This method orchestrates the complete scanning workflow:
        1. Validates input (size, dangerous patterns, syntax)
        2. Extracts code structure (functions, classes, imports) via LLM
        3. Identifies potential issues (bugs, style, security, performance) via LLM
        4. Returns structured results
        
        Args:
            code: Source code to scan
            
        Returns:
            ScanResult with code structure and identified issues
            
        Raises:
            CodeValidationError: If code validation fails
            CodeSizeError: If code exceeds size limit
            DangerousCodeError: If dangerous patterns detected (production mode)
            SyntaxError: If code has syntax errors
            RateLimitError: If rate limit is exceeded
            StructureExtractionError: If structure extraction fails
            IssueDetectionError: If issue detection fails
        """
        logger.info("Starting code scan")
        
        try:
            # Step 1: Validate input
            self._validate_code_completely(code)
            
            # Step 2: Extract structure and identify issues
            structure, issues = self._extract_structure_and_issues(code)
            
            # Step 3: Create result
            result = schemas.ScanResult(structure=structure, issues=issues)
            
            logger.info(
                f"Scan complete: {len(structure.functions)} functions, "
                f"{len(structure.classes)} classes, {len(issues)} issues"
            )
            
            return result
            
        except (
            CodeValidationError,
            DangerousCodeError,
            CodeSizeError,
            SyntaxError,
            StructureExtractionError,
            IssueDetectionError,
            APIRateLimitError,
        ) as e:
            logger.error(f"Scan failed: {e}")
            raise
