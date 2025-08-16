


# modules/scorer.py
import re
from typing import Dict, List

def normalize_token(s: str) -> List[str]:
    return re.sub(r"[^a-z0-9+#]", " ", (s or "").lower()).split()

def expand_with_synonyms(tokens, synonyms_map):
    expanded = set(tokens)
    rev = {s: canon for canon, syns in synonyms_map.items() for s in syns}
    for t in list(expanded):
        if t in rev:
            expanded.add(rev[t])
        if t in synonyms_map:
            expanded.update(synonyms_map[t])
    return expanded

def skill_match_score(candidate_skills, prof, weight_req=0.7, weight_pref=0.3):
    cand = set(normalize_token(" ".join(candidate_skills or [])))
    cand = expand_with_synonyms(cand, prof.get("synonyms", {}))

    required  = set(prof.get("required", []))
    preferred = set(prof.get("preferred", []))
    bonus     = set(prof.get("bonus", []))

    req_hits   = len(required & cand)
    pref_hits  = len(preferred & cand)
    bonus_hits = len(bonus & cand)

    req_score  = req_hits  / (len(required)  or 1)
    pref_score = pref_hits / (len(preferred) or 1)

    blended = weight_req * req_score + weight_pref * pref_score
    return req_score, pref_score, bonus_hits, blended

def scale_years(x, xmin, xmax):
    if xmax <= xmin:
        return 1.0 if (x or 0) >= xmax else 0.0
    x = max(xmin, min(x or 0, xmax))
    return (x - xmin) / (xmax - xmin)

def compute_score(candidate: Dict, cfg: Dict):
    """
    candidate keys expected:
      - years_exp: float
      - education_level: str ('bachelor', 'master', 'phd', etc.)
      - certifications: list[str]
      - skills: list[str]
    Returns (score_0_100, breakdown_dict)
    """
    W = cfg["weights"]
    prof = cfg["skills"][cfg["active_profile"]]

    # Experience
    exp_norm = scale_years(candidate.get("years_exp", 0),
                           cfg["scoring"]["min_years_exp"],
                           cfg["scoring"]["max_years_exp"])

    # Education mapping (simple, tweak later)
    edu_map = {"none":0.0, "diploma":0.25, "bachelor":0.6, "master":0.8, "phd":1.0}
    edu_key = re.sub(r"[^a-z]", "", str(candidate.get("education_level","")).lower())
    edu_score = max((v for k, v in edu_map.items() if k in edu_key), default=0.0)

    # Certifications
    certs = candidate.get("certifications", []) or []
    cert_score = min(len(certs) / 3.0, 1.0)  # cap after 3

    # Skills
    req_s, pref_s, bonus_hits, _ = skill_match_score(candidate.get("skills", []), prof)

    # Weighted sum -> percentage
    total = (
        W["experience_years"] * exp_norm +
        W["education"]        * edu_score +
        W["skills_required"]  * req_s +
        W["skills_preferred"] * pref_s +
        W["certifications"]   * cert_score
    )
    return round(100 * total, 2), {
        "exp_norm": exp_norm, "edu_score": edu_score,
        "req_score": req_s, "pref_score": pref_s,
        "bonus_hits": bonus_hits, "cert_score": cert_score
    }
