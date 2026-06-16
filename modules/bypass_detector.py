import re
import unicodedata

LEET_MAP = {
    '0': 'o', '1': 'i', '3': 'e', '4': 'a',
    '5': 's', '6': 'g', '7': 't', '8': 'b',
    '@': 'a', '$': 's', '!': 'i', '+': 't'
}

SUSPICIOUS_PATTERNS = [
    r'[\u200b-\u200f\u202a-\u202e\ufeff]',
    r'(.)\1{8,}',
    r'\\u[0-9a-fA-F]{4}',
    r'&#\d+;',
    r'%[0-9a-fA-F]{2}',
]

SQL_INJECTION_PATTERNS = [
    r"'\s*(or|and)\s*'?\d",
    r"'\s*(or|and)\s*'\w+'\s*=\s*'\w+",
    r"(union|select|insert|drop|delete|update|exec)\s+",
    r"--\s*$",
    r"/\*.*\*/",
]

def normalize_text(text: str) -> str:
    text = unicodedata.normalize('NFKC', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Cf')
    text = text.lower()
    normalized = ''
    for ch in text:
        normalized += LEET_MAP.get(ch, ch)
    normalized = ' '.join(normalized.split())
    return normalized

def detect_bypass(original: str) -> dict:
    normalized = normalize_text(original)

    for pattern in SUSPICIOUS_PATTERNS:
        if re.search(pattern, original):
            return {
                "is_bypass": True,
                "reason": "Suspicious encoding or obfuscation detected.",
                "confidence": 0.98,
                "normalized_text": normalized
            }

    for pattern in SQL_INJECTION_PATTERNS:
        if re.search(pattern, original, re.IGNORECASE):
            return {
                "is_bypass": False,
                "reason": "SQL pattern detected — forwarding to guard classifier.",
                "confidence": 0.85,
                "normalized_text": normalized
            }

    original_clean = ' '.join(original.lower().split())

    if normalized != original_clean:
        changed_chars = sum(
            1 for a, b in zip(normalized, original_clean) if a != b
        )
        deviation_ratio = changed_chars / max(len(original_clean), 1)
        confidence = min(0.5 + (deviation_ratio * 2), 0.99)

        if deviation_ratio > 0.15:
            return {
                "is_bypass": True,
                "reason": "High character substitution detected — possible leetspeak or homoglyph attack.",
                "confidence": round(confidence, 2),
                "normalized_text": normalized
            }
        elif deviation_ratio > 0.05:
            return {
                "is_bypass": False,
                "reason": "Minor character variation detected — low risk.",
                "confidence": round(0.3 + deviation_ratio, 2),
                "normalized_text": normalized
            }

    return {
        "is_bypass": False,
        "reason": "No bypass patterns detected.",
        "confidence": 0.99,
        "normalized_text": normalized
    }