@echo off
echo Setting up Gemini AI...
set GEMINI_API_KEY=AIzaSyCYvS0PIOo_2yyBJk73yE_xegtf37ZNxD8
echo ✅ Gemini API key set!
echo.
echo Starting Savion Backend Server...
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
pause
