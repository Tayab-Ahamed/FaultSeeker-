@echo off
echo Setting up FaultSeeker++ execution environment...

:: 1. Add Foundry to PATH temporarily for this session
set PATH=%PATH%;%CD%\foundry_bin

:: 2. Create virtual environment if it doesn't exist
if not exist "venv" (
    echo Creating Python virtual environment...
    python -m venv venv
)

:: 3. Activate the virtual environment
call venv\Scripts\activate.bat

:: 4. Install dependencies
echo Installing dependencies...
pip install -e .

:: Clear any corrupted cached files from previous bad RPC connects
echo Clearing stale caches...
if exist "data\cache\replay\" (
    del /q "data\cache\replay\*"
)

:: Start Ollama in background if not already running
echo Checking Ollama status...
tasklist /FI "IMAGENAME eq ollama.exe" 2>NUL | find /I "ollama.exe" >NUL
if errorlevel 1 (
    echo Starting Ollama in background...
    start /B ollama serve >NUL 2>&1
    timeout /t 3 /nobreak >NUL
    echo Ollama started!
) else (
    echo Ollama is already running.
)

:: 5. Run the FaultSeeker analysis with phi3:mini
echo.
echo Starting FaultSeeker analysis via local phi3:mini...
echo.
python -m faultseeker.main -txn_hash 0xbea605b238c85aabe5edc636219155d8c4879d6b05c48091cf1f7286bd4702ba -chain bsc -forensics_model phi3:mini -function_analysis_model phi3:mini --local-model phi3:mini --explain --track-cost

echo.
pause
