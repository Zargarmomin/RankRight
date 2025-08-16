# modules/settings_page.py
import os, json
from pathlib import Path
import pandas as pd
import streamlit as st
from .settings_utils import load_settings, save_settings, normalize_weights

SKILLS_PATH = Path("data/skills_master.csv")

def render_settings_page():
    st.title("⚙️ Settings")

    # Ensure settings in session
    if "settings" not in st.session_state:
        st.session_state.settings = load_settings()
    cfg = st.session_state.settings

    tabs = st.tabs(["Weights", "Skills Master Editor", "Import / Export"])

    # ---- Tab 1: Weights (matches your config.yaml keys) ----
    with tabs[0]:
        st.subheader("Scoring Weights")
        st.caption("These override config.yaml at runtime. Weights are normalized to 1.")

        w = cfg.get("weights", {})
        c1, c2 = st.columns(2)
        with c1:
            skills_w = st.slider("Skills", 0.0, 1.0, float(w.get("skills", 0.6)), 0.01, key="w_skills")
            exp_w    = st.slider("Experience", 0.0, 1.0, float(w.get("experience", 0.25)), 0.01, key="w_exp")
        with c2:
            edu_w    = st.slider("Education", 0.0, 1.0, float(w.get("education", 0.15)), 0.01, key="w_edu")
            emb_w    = st.slider("Embedding (semantic)", 0.0, 1.0, float(w.get("embedding", 0.0)), 0.01, key="w_emb")

        new_w = normalize_weights({
            "skills": skills_w,
            "experience": exp_w,
            "education": edu_w,
            "embedding": emb_w
        })
        st.write("**Normalized weights**:", new_w)

        if st.button("Save Weights", type="primary"):
            cfg["weights"] = new_w
            save_settings(cfg)
            st.success("Weights saved. They will be used immediately.")

    # ---- Tab 2: Skills Master Editor (edit CSV used by your pipeline) ----
    with tabs[1]:
        st.subheader("Skills Master Editor")
        st.caption("Edits `data/skills_master.csv` in-place. Make a backup if needed.")

        if not SKILLS_PATH.exists():
            st.info("`data/skills_master.csv` not found. Create a starter file with a single 'skill' column.")
            if st.button("Create starter skills_master.csv"):
                SKILLS_PATH.parent.mkdir(parents=True, exist_ok=True)
                pd.DataFrame({"skill": ["python", "sql", "streamlit"]}).to_csv(SKILLS_PATH, index=False)
                st.success(f"Created {SKILLS_PATH}.")
                st.rerun()

        if SKILLS_PATH.exists():
            df = pd.read_csv(SKILLS_PATH)
            if "skill" not in df.columns:
                st.error("CSV must contain a 'skill' column.")
            else:
                edited = st.data_editor(
                    df,
                    num_rows="dynamic",
                    use_container_width=True,
                    key="skills_editor"
                )
                colA, colB = st.columns([1,1])
                with colA:
                    if st.button("Save CSV", type="primary"):
                        edited.to_csv(SKILLS_PATH, index=False)
                        st.success("Saved data/skills_master.csv")
                with colB:
                    st.download_button(
                        "Download CSV",
                        edited.to_csv(index=False).encode("utf-8"),
                        file_name="skills_master.csv",
                        mime="text/csv",
                    )

    # ---- Tab 3: Import / Export entire settings.json ----
    with tabs[2]:
        st.subheader("Import / Export settings.json")
        st.download_button(
            "Download current settings.json",
            data=json.dumps(cfg, indent=2),
            file_name="settings.json",
            mime="application/json"
        )
        up = st.file_uploader("Upload settings.json", type=["json"])
        if up and st.button("Import"):
            try:
                new_cfg = json.loads(up.read().decode("utf-8"))
                st.session_state.settings = new_cfg
                save_settings(new_cfg)
                st.success("Imported settings.")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to import: {e}")
