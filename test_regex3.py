import re

def parse(content):
    matches = re.findall(r"(?<![.\d])(?:0?\.\d+|1\.0+)(?![.\d])|\b[01]\b", content)
    if matches:
        return max(0.0, min(1.0, float(matches[-1])))
    return None

print(parse("Based on the 0.0-1.0 scale (0=hallucinated, 1=fully grounded), the answer is fully supported. Score: 1.0"))
print(parse("Based on the scale where 0 is hallucinated, I give it a 1"))
print(parse("0.85"))
print(parse("1"))
print(parse("0.0"))
print(parse("Score: 0.9 (hallucinated is 0.0)"))
