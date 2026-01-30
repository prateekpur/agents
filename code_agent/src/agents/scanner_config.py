"""Configuration constants for Scanner Agent."""

# Default configuration values
DEFAULT_MAX_CODE_SIZE = 500_000  # 500KB
DEFAULT_RATE_LIMIT_CALLS = 10
DEFAULT_RATE_LIMIT_WINDOW = 60  # seconds
DEFAULT_MAX_ANALYSIS_LENGTH = 10_000  # Maximum code length to send to LLM
TRUNCATION_THRESHOLD = 0.8  # Keep 80%+ of code when truncating at line boundary

# LLM prompts
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
    # Dynamic code execution
    r'__import__\s*\(',
    r'eval\s*\(',
    r'exec\s*\(',
    r'compile\s*\(',
    
    # File system operations
    r'open\s*\([^)]*["\']w',  # Write mode file operations
    
    # System commands
    r'os\.system\s*\(',
    r'subprocess\.',
    
    # Built-in access
    r'__builtins__',
]
