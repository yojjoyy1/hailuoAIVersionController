@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONPATH=%CD%
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

where py >nul 2>nul
if %ERRORLEVEL%==0 (
  py -3 -m avc web --host 127.0.0.1 --port 8765
  goto :end
)
where python >nul 2>nul
if %ERRORLEVEL%==0 (
  python -m avc web --host 127.0.0.1 --port 8765
  goto :end
)
where python3 >nul 2>nul
if %ERRORLEVEL%==0 (
  python3 -m avc web --host 127.0.0.1 --port 8765
  goto :end
)

echo 找不到 Python。請先安裝 Python 3，安裝時勾選 Add python.exe to PATH。
pause
exit /b 1

:end
if errorlevel 1 pause
