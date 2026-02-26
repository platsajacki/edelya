def normalize_string(s: str) -> str:
    """Delete extra spaces and trim string."""
    s = s.strip()
    while '  ' in s:
        s = s.replace('  ', ' ')
    return s
