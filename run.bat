@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo [1/2] creating venv ...
  python -m venv .venv
  if errorlevel 1 goto fail
  .venv\Scripts\python.exe -m pip install -i https://pypi.org/simple -r requirements.txt
  if errorlevel 1 goto fail
)
echo [2/2] starting game at http://127.0.0.1:5000
start "" http://127.0.0.1:5000
.venv\Scripts\python.exe app.py
goto end
:fail
echo setup failed. check python and network.
pause
:end
endlocal
