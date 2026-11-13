@echo off
rem ------------------------------------------------------------------
rem  Flrig EMCOMM - Windows build
rem  Double-click this file. Makes:
rem     dist\FlrigEMCOMM.exe                     (the program, one file)
rem     output\FlrigEMCOMM_Setup_<version>.exe   (installer to send people,
rem                                               if Inno Setup 6 is installed)
rem  Needs Python from python.org on THIS PC only.
rem ------------------------------------------------------------------
setlocal
cd /d "%~dp0"
set "PYTHONDONTWRITEBYTECODE=1"
where python >nul 2>nul && (set "PY=python") || (set "PY=py")

for /f "delims=" %%v in ('%PY% -c "import flrig_emcomm as m; print(m.APP_VERSION)"') do set "VER=%%v"
if not defined VER (echo Could not run Python. Install it from python.org. & goto :end)
echo Building Flrig EMCOMM %VER%

echo [1/3] Getting the build tool (PyInstaller)...
%PY% -m pip install --upgrade --quiet --disable-pip-version-check -r requirements.txt || (echo Could not install PyInstaller. & goto :end)

echo [2/3] Building FlrigEMCOMM.exe (takes a minute)...
%PY% -m PyInstaller --noconfirm --clean FlrigEMCOMM.spec >build_log.txt 2>&1
if not exist "dist\FlrigEMCOMM.exe" (echo Build failed. See build_log.txt & goto :end)
rmdir /s /q build >nul 2>nul
del /q build_log.txt >nul 2>nul

echo [3/3] Making the installer...
set "ISCC="
for /f "delims=" %%i in ('where iscc 2^>nul') do if not defined ISCC set "ISCC=%%i"
if not defined ISCC if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if not defined ISCC (
  echo Inno Setup 6 not found, so no installer this time.
  echo Get it free from https://jrsoftware.org/isinfo.php to make one.
  goto :done
)
"%ISCC%" /Q /DAppVersion=%VER% FlrigEMCOMM.iss || (echo Installer build failed. & goto :end)

:done
echo.
echo Done!
echo   Program:   dist\FlrigEMCOMM.exe
if exist "output\FlrigEMCOMM_Setup_%VER%.exe" echo   Installer: output\FlrigEMCOMM_Setup_%VER%.exe
echo.
:end
if not defined CI pause
