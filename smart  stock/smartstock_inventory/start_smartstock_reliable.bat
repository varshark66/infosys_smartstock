@echo off
title SmartStock Reliable Launcher
color 0A

echo.
echo ╔════════════════════════════════════════╗
echo ║     SmartStock Inventory System        ║
echo ║        Reliable Launcher v2.0          ║
echo ╚════════════════════════════════════════╝
echo.

echo 🔧 Step 1: Ensuring MongoDB is running...
call "%~dp0ensure_mongodb.bat"
if errorlevel 1 (
    echo.
    echo ❌ CRITICAL: MongoDB setup failed
    echo    SmartStock cannot start without database
    echo.
    echo 🔍 Troubleshooting:
    echo    1. Make sure MongoDB is installed
    echo    2. Check if port 27017 is available
    echo    3. Verify C:\data\db directory permissions
    echo.
    pause
    exit /b 1
)

echo.
echo ✅ MongoDB is ready!
echo.

echo 🔧 Step 2: Starting SmartStock Application...
echo 📍 Changing to application directory...
cd /d "%~dp0smartstock_inventory\smartstock_inventory\smartstock_inventory"

if not exist "app.py" (
    echo ❌ ERROR: app.py not found in current directory
    echo    Current directory: %CD%
    echo.
    echo 🔍 Please check the file structure
    pause
    exit /b 1
)

echo 🚀 Starting Flask application...
echo 🌐 Application will be available at: http://localhost:5000
echo 📊 Dashboard: http://localhost:5000/dashboard
echo.
echo Press Ctrl+C to stop the application
echo.

python app.py

if errorlevel 1 (
    echo.
    echo ❌ SmartStock application failed to start
    echo    This might be due to database connection issues
    echo.
    echo 🔍 Checking MongoDB status...
    netstat -an | findstr :27017
    echo.
    pause
    exit /b 1
)

echo.
echo 🎉 SmartStock stopped gracefully
pause
