@echo off
title MATRIX — AI Operating System
cd /d "%~dp0"
echo ======================================================================
echo                     MATRIX AI ECOSYSTEM LAUNCHER
echo ======================================================================
echo Starting MATRIX Server & HUD on Windows 11...
python run_matrix.py
if errorlevel 1 (
    echo.
    echo [ERROR] MATRIX launcher terminated with error code %errorlevel%.
    echo Please ensure Python 3.10+ is installed and in your PATH.
    pause
)
