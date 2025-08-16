import csv
from typing import List, Set

def load_skills(path: str) -> List[str]:
    skills = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            s = row.get("skill", "").strip()
            if s:
                skills.append(s.lower())
    # dedupe
    return sorted(list(set(skills)))

def normalize_skill(s: str) -> str:
    return s.lower().strip()
