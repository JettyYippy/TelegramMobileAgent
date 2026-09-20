import re
from pathlib import Path
from typing import Dict, Any, Tuple

# Regex patterns for destructive shell operations
HIGH_RISK_COMMAND_PATTERNS = [
    # Linux/Mac/Bash destructive commands
    r"\brm\s+-[a-zA-Z]*[rfRF]",               # rm -rf, rm -r, rm -f
    r"\brm\s+--recursive\b",
    r"\brm\s+--force\b",
    r"\bshred\b",
    
    # Windows destructive commands
    r"\brmdir\s+.*(/[sS]|/[qQ])",             # rmdir /s /q
    r"\brd\s+.*(/[sS]|/[qQ])",                # rd /s /q
    r"\bdel\s+.*(/[sS]|/[fF]|/[qQ])",         # del /s /q /f
    r"\berase\s+.*(/[sS]|/[fF]|/[qQ])",       # erase /s /q /f
    
    # Git destructive commands
    r"\bgit\s+reset\s+--hard\b",              # git reset --hard
    r"\bgit\s+clean\s+-[a-zA-Z]*[fF]",        # git clean -f
    r"\bgit\s+restore\s+(\.|\*)\b",           # git restore .
    r"\bgit\s+checkout\s+--\s+(\.|\*)\b",     # git checkout -- .
    
    # Database drops
    r"\bdrop\s+(database|schema|table)\b",
    r"\btruncate\s+table\b",
    
    # Process and system destruction
    r"\bformat\s+[a-zA-Z]:",                  # format C:
    r"\b(pkill\s+-9|kill\s+-9|taskkill\s+/[fF])\b",
    r"\bchmod\s+(-R\s+)?777\b",
]

def is_high_risk(tool_name: str, args: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Evaluates whether a proposed tool execution is high risk (destructive).
    Returns (is_risk: bool, reason: str).
    """
    if tool_name == "run_command":
        cmd = args.get("CommandLine", "").strip()
        for pattern in HIGH_RISK_COMMAND_PATTERNS:
            if re.search(pattern, cmd, re.IGNORECASE):
                return True, f"Destructive command detected: `{cmd}`"
        return False, ""

    elif tool_name in ("write_to_file", "create_file"):
        content = args.get("CodeContent", args.get("code_content", ""))
        target = args.get("TargetFile", args.get("target_file", ""))
        # Flag if attempting to overwrite an existing file with empty content
        if target and content == "" and args.get("Overwrite", False):
            return True, f"Attempting to wipe file `{target}` with empty content"
        return False, ""

    return False, ""
