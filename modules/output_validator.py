import re

LEAK_PATTERNS = [
    r"I will now act as",
    r"sure,? here'?s? how to bypass",
    r"my (system )?prompt (is|says|contains)",
    r"as an? (unrestricted|unfiltered|jailbroken)",
    r"DAN mode (enabled|activated)",
    r"I have no restrictions",
    r"ignore (all |my )?(previous )?instructions",
]

def validate_output(response: str) -> dict:
    for pattern in LEAK_PATTERNS:
        if re.search(pattern, response, flags=re.IGNORECASE):
            return {
                "is_safe": False,
                "sanitized_response": "[BLOCKED: The AI response violated safety policies.]",
                "reason": "Unsafe pattern detected in output."
            }

    if len(response.strip()) < 2:
        return {
            "is_safe": False,
            "sanitized_response": "[BLOCKED: Empty or invalid response.]",
            "reason": "Response too short or empty."
        }

    return {
        "is_safe": True,
        "sanitized_response": response,
        "reason": "Output passed all safety checks."
    }