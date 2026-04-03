@echo off
echo Removing paper, full_paper, AGENTS.md, and FaultSeeker_Plus_Plus.tex...

:: Delete directories
rmdir /S /Q paper 2>nul
rmdir /S /Q full_paper 2>nul

:: Delete files
del FaultSeeker_Plus_Plus.tex 2>nul
del AGENTS.md 2>nul

echo Folder and files removed successfully!
pause
