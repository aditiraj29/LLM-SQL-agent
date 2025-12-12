@echo off
cd %~dp0
.\.venv\Scripts\activate
streamlit run app\ui_streamlit.py
pause
