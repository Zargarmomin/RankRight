# --- matcher.py (semantic-enabled) ---
import re
from typing import Dict, List, Set, Tuple, Optional
import spacy
from spacy.matcher import PhraseMatcher

# ======= OPTIONAL SEMANTIC SIMILARITY (embeddings) =======
# Loads once (lazily) so each request is fast.
_embed_model = None
_np = None

def _ensure_embed_model():
    global _embed_model, _np
    if _embed_model is None:
        from sentence_transformers import SentenceTransformer
        import numpy as np
        _embed_model = SentenceTransformer("all-MiniLM-L6-v2")
        _np = np

def _cosine(a, b):
    num = (a * b).sum()
    den = (_np.sqrt((a * a).sum()) * _np.sqrt((b * b).sum()))
    return float(num / den) if den else 0.0

def semantic_similarity(resume_text: str, jd_text: str) -> float:
    """Return cosine similarity between resume and JD using sentence-transformers."""
    _ensure_embed_model()
    v = _embed_model.encode([resume_text, jd_text])
    return _cosine(v[0], v[1])
# =========================================================

EDU_LEVELS = {
    "phd": ["phd", "ph.d", "doctorate"],
    "master": ["master", "mtech", "m.tech", "m.e.", "m.sc", "ms", "m.s", "mca", "mba"],
    "bachelor": ["bachelor", "b.tech", "btech", "b.e.", "b.sc", "bs", "b.s", "bca"],
}

YEARS_RE = re.compile(r"(\d+)\+?\s+years?")

def build_nlp(skills: List[str]):
    nlp = spacy.load("en_core_web_sm")
    matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
    patterns = [nlp.make_doc(s) for s in skills]
    matcher.add("SKILL", patterns)
    return nlp, matcher

def extract_skills(text: str, nlp, matcher) -> Set[str]:
    doc = nlp(text)
    matches = matcher(doc)
    return {doc[s:e].text.lower().strip() for _, s, e in matches}

def extract_years_experience(text: str) -> int:
    years = 0
    for m in YEARS_RE.finditer(text.lower()):
        try:
            years = max(years, int(m.group(1)))
        except:
            pass
    return years

def extract_education(text: str) -> str:
    t = text.lower()
    if any(k in t for k in EDU_LEVELS["phd"]): return "PhD"
    if any(k in t for k in EDU_LEVELS["master"]): return "Master"
    if any(k in t for k in EDU_LEVELS["bachelor"]): return "Bachelor"
    return "Unknown"

def parse_jd(jd_text: str, skills_master: List[str]) -> Dict:
    nlp, matcher = build_nlp(skills_master)
    req_skills = extract_skills(jd_text, nlp, matcher)
    req_years = extract_years_experience(jd_text)
    req_edu = extract_education(jd_text)
    return {"required_skills": req_skills, "required_years": req_years, "required_education": req_edu}

def extract_resume_profile(resume_text: str, nlp, matcher, skills_master: List[str]) -> Dict:
    sk = extract_skills(resume_text, nlp, matcher)
    yrs = extract_years_experience(resume_text)
    edu = extract_education(resume_text)
    return {"matched_skills": sorted(list(sk)), "years_experience": yrs, "education": edu}

def _education_score(candidate: str, required: str) -> float:
    order = ["Unknown", "Bachelor", "Master", "PhD"]
    c = order.index(candidate) if candidate in order else 0
    r = order.index(required) if required in order else 0
    return 1.0 if c >= r else (0.7 if (c == 1 and r == 2) else 0.4)

def score_resume(
    profile: Dict,
    jd: Dict,
    weights: Dict = None,
    *,
    resume_text: Optional[str] = None,
    jd_text: Optional[str] = None,
) -> Dict:
    """
    Now supports semantic scoring via embeddings when weights['embedding'] > 0
    and resume_text/jd_text are provided.
    """
    weights = weights or {"skills": 0.6, "experience": 0.25, "education": 0.15, "embedding": 0.0}

    rs = jd.get("required_skills", set())
    found = set(profile.get("matched_skills", []))
    missing = sorted(list(rs - found))
    overlap = len(found & rs)
    total = len(rs) if rs else 1
    skills_ratio = overlap / total

    exp_req = jd.get("required_years", 0)
    exp_have = profile.get("years_experience", 0)
    exp_score = 1.0 if exp_req == 0 else min(1.0, exp_have / exp_req)

    edu_score = _education_score(profile.get("education", "Unknown"), jd.get("required_education", "Unknown"))

    # --- semantic score ---
    emb_w = float(weights.get("embedding", 0.0))
    sem_score = 0.0
    if emb_w > 0 and resume_text and jd_text:
        try:
            sem_score = semantic_similarity(resume_text, jd_text)
        except Exception:
            sem_score = 0.0

    final = (
        float(weights["skills"]) * skills_ratio +
        float(weights["experience"]) * exp_score +
        float(weights["education"]) * edu_score +
        emb_w * sem_score
    )

    return {
        "skill_match_ratio": round(skills_ratio, 3),
        "missing_skills": ", ".join(missing),
        "experience_score": round(exp_score, 3),
        "education_score": round(edu_score, 3),
        "semantic_score": round(sem_score, 3),
        "final_score": round(final, 3),
    }
