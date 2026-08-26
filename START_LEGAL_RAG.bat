@echo off

call C:\Users\user\anaconda3\Scripts\activate.bat rag

cd /d C:\Users\user\Desktop\UzmanlikProject\Deney15

REM start http://localhost:8501

streamlit run app.py

pause