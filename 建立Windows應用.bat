@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

echo ================================================
echo   打包「時光本」Windows 單一應用（.exe）
echo ================================================
echo.

rem 確保有 PyInstaller
python -m PyInstaller --version >nul 2>nul
if errorlevel 1 (
  echo 尚未安裝 PyInstaller，正在安裝...
  python -m pip install --user pyinstaller
  if errorlevel 1 (
    echo 安裝 PyInstaller 失敗，請先安裝 Python 3 並確認能連上網路。
    pause
    exit /b 1
  )
)

echo 開始打包，這可能需要一兩分鐘...
rem 注意：exe 檔名用 ASCII（avc.exe），因為 .avc\avc.cmd 需要在 cmd 內以純 ASCII 路徑引用它。
python -m PyInstaller ^
  --noconfirm --clean --onefile ^
  --name avc ^
  --add-data "avc/web;avc/web" ^
  --collect-submodules avc ^
  avc\__main__.py

if errorlevel 1 (
  echo.
  echo 打包失敗。
  pause
  exit /b 1
)

echo.
echo ================================================
echo   完成！應用在： dist\avc.exe
echo   雙擊 dist\avc.exe（或雙擊「開啟時光本.bat」）
echo   就會開啟時光本網頁，不需要另外裝 Python。
echo ================================================
pause
