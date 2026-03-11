@echo off
title SmartStock Inventory System
color 0A

echo.
echo ========================================
echo    SmartStock Inventory System
echo ========================================
echo.

echo [1/3] Starting MongoDB server...
call "%~dp0start_mongodb_simple.bat"
if errorlevel 1 (
    echo.
    echo ❌ Failed to start MongoDB. Please check the installation.
    pause
    exit /b 1
)

echo.
echo [2/3] Starting Flask application...
cd /d "%~dp0smartstock_inventory\smartstock_inventory\smartstock_inventory"
python app.py

if errorlevel 1 (
    echo.
    echo ❌ Flask application failed to start.
    pause
    exit /b 1
)

echo.
echo [3/3] SmartStock is running!
echo 🌐 Open http://localhost:5000 in your browser
echo.
pause
