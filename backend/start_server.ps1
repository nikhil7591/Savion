# PowerShell script to start Savion Backend with Gemini AI
Write-Host "🚀 Setting up Gemini AI..." -ForegroundColor Green

# Set Gemini API key
$env:GEMINI_API_KEY = "AIzaSyCYvS0PIOo_2yyBJk73yE_xegtf37ZNxD8"
Write-Host "✅ Gemini API key set!" -ForegroundColor Green

# Test the setup
Write-Host "🧪 Testing Gemini AI configuration..." -ForegroundColor Yellow
try {
    python -c "
from app.gemini_ai import get_gemini_assistant
assistant = get_gemini_assistant()
if assistant.is_available():
    print('✅ Gemini AI is ready!')
else:
    print('❌ Gemini AI not available')
"
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Gemini AI configuration successful!" -ForegroundColor Green
    } else {
        Write-Host "❌ Gemini AI configuration failed" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "❌ Error testing Gemini AI: $_" -ForegroundColor Red
    exit 1
}

Write-Host "🎉 Starting Savion Backend Server..." -ForegroundColor Green
Write-Host "Server will be available at: http://localhost:8000" -ForegroundColor Cyan
Write-Host "API docs available at: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

# Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
