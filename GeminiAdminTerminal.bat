@echo off
setlocal

:: Get current directory path
set "current_dir=%cd%"

:: Create temporary VBS script for elevation
set "vbs_path=%temp%\launch_admin_terminal.vbs"
echo Set UAC = CreateObject^("Shell.Application"^) > "%vbs_path%"
echo UAC.ShellExecute "wt.exe", "-d ""%current_dir%"" cmd /k gemini", "", "runas", 1 >> "%vbs_path%"

:: Execute VBS script silently
cscript //nologo "%vbs_path%"

:: Cleanup temporary file
timeout /t 1 /nobreak >nul
del "%vbs_path%" >nul 2>&1

endlocal