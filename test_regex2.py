import re

content = "Based on the 0.0-1.0 scale (0=hallucinated, 1=fully grounded), the answer is fully supported. Score: 1.0"
m = re.search(r"(?<![.\d])(?:0?\.\d+|1\.0+)(?![.\d])", content) or re.search(r"\b[01]\b", content)
res = max(0.0, min(1.0, float(m.group()))) if m else None
print(res)

content2 = "Based on the scale where 0 is hallucinated, I give it a 1"
m2 = re.search(r"(?<![.\d])(?:0?\.\d+|1\.0+)(?![.\d])", content2) or re.search(r"\b[01]\b", content2)
res2 = max(0.0, min(1.0, float(m2.group()))) if m2 else None
print(res2)
