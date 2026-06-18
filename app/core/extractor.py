import re

# Deterministic high-performance regex patterns
PATTERNS = {
    "md5": re.compile(r'\b[a-fA-F0-9]{32}\b'),
    "sha256": re.compile(r'\b[a-fA-F0-9]{64}\b'),
    "ipv4": re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'),
    "email": re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'),
    "domain": re.compile(r'\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9][a-z0-9-]{0,61}[a-z0-9]\b', re.IGNORECASE),
    "btc_wallet": re.compile(r'\b(?:1[A-HJ-NP-Za-km-z1-9]{25,34}|3[A-HJ-NP-Za-km-z1-9]{25,34}|bc1[a-zA-HJ-NP-Z0-9]{39,59})\b'),
    "xmr_wallet": re.compile(r'\b(?:4[0-9AB][1-9A-HJ-NP-Za-km-z]{93})\b')
}

def extract_iocs(text: str) -> list[dict]:
    """Extracts Indicators of Compromise (IOCs) using regex scanning."""
    if not text: return []
    return [{"type": t, "value": v} for t, p in PATTERNS.items() for v in set(p.findall(text))]
