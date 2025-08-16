@echo off
python -m venv .venv
call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m spacy download en_core_web_sm
echo ✅ Environment ready. Run: streamlit run app/streamlit_app.py
