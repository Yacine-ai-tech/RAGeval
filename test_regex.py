import re
texts = ["1", "0", "0.0", "1.0", "0.85", "Score: 1.0", "I give this a 1", "0.0 (hallucinated)"]
for content in texts:
    m = re.search(r"(?<![.\d])(?:0?\.\d+|1\.0+)(?![.\d])", content) or re.search(r"\b[01]\b", content)
    res = max(0.0, min(1.0, float(m.group()))) if m else None
    print(f"{content!r} -> {res}")
