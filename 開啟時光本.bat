@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

rem 優先使用打包好的單一應用（不需要安裝 Python）
if exist "%~dp0dist\avc.exe" (
  start "" "%~dp0dist\avc.exe" web --host 127.0.0.1 --port 8765
  goto :eof
)

rem 沒有打包檔時，退回用 Python 執行原始碼
set PYTHONPATH=%CD%
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

echo 找不到打包好的 dist\avc.exe，也找不到 Python。
echo 請先雙擊「建立Windows應用.bat」打包，或安裝 Python 3。
pause
exit /b 1

:end
if errorlevel 1 pause
