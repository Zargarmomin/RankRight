# --- app/streamlit_app.py ---
# RankRight: logo-only header (centered, bigger), login via Enter, red Logout, Thank You flow, Settings integration

import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st
import pandas as pd
import yaml
from PIL import Image
from streamlit_option_menu import option_menu

# your existing project modules
from src.parsers import extract_text_from_file
from src.skills import load_skills
from src.matcher import build_nlp, extract_resume_profile, parse_jd, score_resume
from src.utils import mask_pii

# NEW: settings helpers
from modules.settings_utils import load_settings
from modules.settings_page import render_settings_page

# ---------- APP CONFIG ----------
st.set_page_config(
    page_title="RankRight • AI Resume Screener",
    page_icon="assets/logo.png",   # ideally a square PNG/mark
    layout="wide"
)

LOGO_PATH = "assets/logo.png"

def brand_header(_show_tagline_ignored=True):
    """Top header with ONLY the logo (top-left, original position)."""
    if os.path.exists(LOGO_PATH):
        try:
            img = Image.open(LOGO_PATH)
            st.image(img, width=230)   # adjust size (200–300 works well)
        except Exception:
            st.empty()


# ---------- SIMPLE LOGIN (shared password via secrets) ----------
def require_login():
    """Show login (in a form so Enter submits) if APP_PASSWORD is set and user isn't authenticated."""
    app_pwd = st.secrets.get("APP_PASSWORD", "")
    if not app_pwd:
        return

    if "auth_ok" not in st.session_state:
        st.session_state.auth_ok = False

    if not st.session_state.auth_ok:
        # Logo on login
        if os.path.exists(LOGO_PATH):
            try:
                st.image(LOGO_PATH, width=100)
            except Exception:
                pass
        st.markdown("<h2 style='margin:0 0 0.5rem 0;color:#1f2937;'>Welcome to RankRight</h2>", unsafe_allow_html=True)
        st.caption("Please enter the app password to continue.")

        # Use a form so pressing Enter submits
        with st.form("login_form", clear_on_submit=False):
            pwd = st.text_input("Enter app password", type="password", key="login_pwd")
            submitted = st.form_submit_button("Enter")
        if submitted:
            if pwd == app_pwd:
                st.session_state.auth_ok = True
                st.rerun()
            else:
                st.error("Wrong password")
        st.stop()

# ---------- THANK YOU PAGE (must run BEFORE require_login) ----------
# If user just clicked Logout, show Thank You first (no login prompt in between)
if st.session_state.get("show_thank_you"):
    st.session_state.show_thank_you = False  # consume the flag so it shows once
    if os.path.exists(LOGO_PATH):
        try:
            st.image(LOGO_PATH, width=120)
        except Exception:
            pass
    st.markdown("<h1 style='text-align:center;margin-top:0.5rem;'>Thank You</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;opacity:0.85;'>Created By Momin Zargar</p>", unsafe_allow_html=True)
    st.markdown("<div style='height:1rem;'></div>", unsafe_allow_html=True)
    # Centered "Log in again" button
    colA, colB, colC = st.columns([1, 1, 1])
    with colB:
        if st.button("Log in again", use_container_width=True):
            st.session_state.auth_ok = False
            st.rerun()
    st.stop()

# Only enforce login after we handled the Thank You state.
require_login()

# ---------- LOAD CONFIG + SETTINGS (weights override) ----------
# Load YAML config (kept for other settings/fallback)
try:
    with open("config.yaml", "r", encoding="utf-8") as f:
        cfg_yaml = yaml.safe_load(f) or {}
except FileNotFoundError:
    cfg_yaml = {}

# Load JSON settings once per session (created via Settings page)
if "settings" not in st.session_state:
    st.session_state.settings = load_settings()
settings = st.session_state.settings

# Final weights used by scoring (Settings > config.yaml > defaults)
weights = (
    settings.get("weights")
    or cfg_yaml.get("weights")
    or {"skills": 0.6, "experience": 0.25, "education": 0.15, "embedding": 0.0}
)

# ---------- SIDEBAR NAV ----------
with st.sidebar:
    # Make the Logout button red (only in sidebar)
    st.markdown("""
        <style>
        /* Sidebar button base */
        section[data-testid="stSidebar"] div.stButton > button {
            background-color: #ef4444 !important;  /* red-500 */
            color: white !important;
            border: none !important;
            border-radius: 6px !important;
        }
        /* Hover state */
        section[data-testid="stSidebar"] div.stButton > button:hover {
            background-color: #dc2626 !important;  /* red-600 */
            color: white !important;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("## Navigation")
    page = option_menu(
        None,
        ["Screen & Rank", "Results Dashboard", "Settings"],
        icons=["clipboard-check", "bar-chart", "gear"],
        menu_icon="list",
        default_index=0,
        styles={
            "container": {"padding": "0.5rem 0.5rem", "background-color": "transparent"},
            "icon": {"color": "#4a90e2", "font-size": "1.1rem"},
            "nav-link": {
                "font-size": "1.0rem",
                "padding": "0.5rem 0.75rem",
                "border-radius": "8px",
                "color": "#1f2933",
                "margin": "0.125rem 0",
            },
            "nav-link-hover": {"background-color": "rgba(74,144,226,0.12)"},
            "nav-link-selected": {
                "background-color": "white",
                "color": "#1f2933",
                "box-shadow": "0 1px 4px rgba(0,0,0,0.08)"
            },
        },
    )

    # RED Logout button
    if st.button("Logout", key="logout_btn", use_container_width=True):
        st.session_state.auth_ok = False
        st.session_state.show_thank_you = True
        st.rerun()

# ---------- PAGE ROUTING ----------
if page == "Screen & Rank":
    brand_header()
    st.markdown(
        "<h2 style='margin-bottom:0; color:#4a90e2;'>🚀 RankRight: Screen & Rank</h2>",
        unsafe_allow_html=True
    )
    st.caption("Upload resumes → let RankRight analyze → instantly see top candidates.")

    col1, col2 = st.columns([2, 1])
    with col1:
        # Load default JD sample if present
        try:
            jd_default = open("data/samples/jd_backend.txt", encoding="utf-8").read()
        except FileNotFoundError:
            jd_default = "Responsibilities: Build backend APIs in Python/Node...\nRequirements: Python, SQL, REST, Docker..."
        jd_text = st.text_area("Paste Job Description (JD) here:", height=220, value=jd_default)
    with col2:
        st.write("**Tips**")
        st.markdown(
            "- Upload PDF/DOCX/TXT resumes\n"
            "- Edit skills in **Settings → Skills Master Editor** (writes to `data/skills_master.csv`)\n"
            "- Emails/phones are masked before analysis\n"
            "- Adjust weights in **Settings**"
        )
        st.write("**Current Weights**")
        st.json(weights)

    uploads = st.file_uploader("Upload one or more resumes", type=["pdf", "docx", "txt"], accept_multiple_files=True)
    run_btn = st.button("Analyze")

    if run_btn and uploads and jd_text.strip():
        try:
            # Load resources
            skills_master = load_skills("data/skills_master.csv")
            nlp, matcher = build_nlp(skills_master)
            jd = parse_jd(jd_text, skills_master)

            rows = []
            with st.spinner("Analyzing resumes..."):
                for up in uploads:
                    # Extract & mask raw text for fairness
                    text = extract_text_from_file(up)
                    text = mask_pii(text)

                    # Build candidate profile and scores
                    profile = extract_resume_profile(text, nlp, matcher, skills_master)
                    scores = score_resume(
                        profile, jd, weights=weights,
                        resume_text=text, jd_text=jd_text  # enables semantic scoring if configured
                    )

                    rows.append({
                        "filename": up.name,
                        "years_experience": profile.get("years_experience"),
                        "education": profile.get("education"),
                        "skill_match_ratio": scores.get("skill_match_ratio"),
                        "missing_skills": ", ".join(scores.get("missing_skills", [])) if isinstance(scores.get("missing_skills"), list) else scores.get("missing_skills"),
                        "experience_score": scores.get("experience_score"),
                        "education_score": scores.get("education_score"),
                        "semantic_score": scores.get("semantic_score", 0.0),
                        "final_score": scores.get("final_score"),
                    })

            df = pd.DataFrame(rows).sort_values("final_score", ascending=False, ignore_index=True)

            # Persist last results for dashboard
            os.makedirs("data", exist_ok=True)
            df.to_csv("data/last_results.csv", index=False)

            st.subheader("Ranked Candidates")
            st.dataframe(df, use_container_width=True)

            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("Download results as CSV", csv, file_name="ranked_candidates.csv", mime="text/csv")

            with st.expander("View parsed JD details"):
                st.json(jd)

        except Exception as e:
            st.error("Something went wrong while analyzing. See details below:")
            st.exception(e)
    else:
        st.info("Upload resumes and paste a JD, then click **Analyze**.")

elif page == "Results Dashboard":
    brand_header()
    st.markdown(
        "<h2 style='margin-bottom:0; color:#4a90e2;'>📊 RankRight Dashboard</h2>",
        unsafe_allow_html=True
    )
    st.caption("Insights, KPIs, and trends from your latest screening run.")

    # Load last results
    try:
        df = pd.read_csv("data/last_results.csv")
    except FileNotFoundError:
        st.info("No saved results yet. Run an analysis first.")
        st.stop()

    # KPIs
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Candidates", len(df))
    try:
        c2.metric("Top Score", f"{df['final_score'].max():.2f}")
        c3.metric("Avg Score", f"{df['final_score'].mean():.2f}")
        c4.metric("≥ 0.7 Score", int((df['final_score'] >= 0.7).sum()))
    except Exception:
        c2.metric("Top Score", "—")
        c3.metric("Avg Score", "—")
        c4.metric("≥ 0.7 Score", "—")

    # Top missing skills
    st.subheader("Top Missing Skills")
    missing = df['missing_skills'].fillna('').astype(str).str.split(', ').explode()
    missing = missing[(missing != '') & (missing.notna())]
    if not missing.empty:
        top_missing = missing.value_counts().head(10)
        st.bar_chart(top_missing)
    else:
        st.info("No missing skills found in the last run.")

    # Table with sorting/filtering (basic)
    st.subheader("Last Run Table")
    st.dataframe(df, use_container_width=True)

    # Optional: download again
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("Download results as CSV", csv, file_name="ranked_candidates.csv", mime="text/csv")

elif page == "Settings":
    brand_header()
    st.markdown(
        "<h2 style='margin-bottom:0; color:#4a90e2;'>⚙️ RankRight Settings</h2>",
        unsafe_allow_html=True
    )
    st.caption("Tune scoring weights and update skills to match your hiring goals.")
    render_settings_page()
