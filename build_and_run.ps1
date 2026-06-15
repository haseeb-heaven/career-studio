# One-click build and run for AI Career Studio (Windows PowerShell)
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if ([string]::IsNullOrEmpty($ScriptDir)) {
    $ScriptDir = Get-Item .
}

Write-Host "=== 1. Building Frontend ===" -ForegroundColor Cyan
Set-Location "$ScriptDir\frontend"
npm install
npm run build

Write-Host "`n=== 2. Setting up Backend ===" -ForegroundColor Cyan
Set-Location "$ScriptDir\backend"
& "D:\henv\Scripts\pip.exe" install -r requirements.txt

Write-Host "`n=== 3. Launching Services ===" -ForegroundColor Cyan
# Launch FastAPI backend in a new window
Start-Process -FilePath "D:\henv\Scripts\uvicorn.exe" -ArgumentList "main:app --host 127.0.0.1 --port 8000 --reload" -WorkingDirectory "$ScriptDir\backend"

# Launch Vite frontend in a new window
Start-Process -FilePath "cmd.exe" -ArgumentList "/c npm run dev" -WorkingDirectory "$ScriptDir\frontend"

Write-Host "`n[SUCCESS] Both backend and frontend services have been launched in separate windows!" -ForegroundColor Green
Write-Host "- Backend running at: http://127.0.0.1:8000" -ForegroundColor Gray
Write-Host "- Frontend running at: http://localhost:5173" -ForegroundColor Gray
