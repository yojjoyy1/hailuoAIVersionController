@echo off
setlocal
set ROOT=%~dp0..
set PYTHONPATH=%ROOT%
set PYTHONUTF8=1
cd /d "%CD%"
where py >nul 2>nul && py -3 -m avc %* && exit /b %ERRORLEVEL%
where python >nul 2>nul && python -m avc %* && exit /b %ERRORLEVEL%
echo 找不到 Python。
exit /b 1
