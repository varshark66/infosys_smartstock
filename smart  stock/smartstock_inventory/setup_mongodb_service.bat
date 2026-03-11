@echo off
title MongoDB Service Setup
color 0E

echo 🔧 MongoDB Windows Service Setup
echo =================================
echo.

REM Check if running as Administrator
net session >nul 2>&1
if %errorLevel% == 0 (
    echo ✅ Running with Administrator privileges
) else (
    echo ❌ This script requires Administrator privileges
    echo Please right-click and "Run as administrator"
    pause
    exit /b 1
)

echo [1/3] Stopping any existing MongoDB service...
sc stop MongoDB 2>NUL
timeout /t 2 /nobreak >nul

echo [2/3] Deleting existing MongoDB service...
sc delete MongoDB 2>NUL

echo [3/3] Installing MongoDB as auto-start service...

REM Find MongoDB installation path
set MONGO_PATH=
for %%f in (
    "C:\Program Files\MongoDB\Server\8.2\bin\mongod.exe"
    "C:\Program Files\MongoDB\Server\8.0\bin\mongod.exe"
    "C:\Program Files\MongoDB\Server\7.0\bin\mongod.exe"
    "C:\Program Files\MongoDB\Server\6.0\bin\mongod.exe"
) do (
    if exist %%f (
        set MONGO_PATH=%%~f
        goto :found_mongo
    )
)

:found_mongo
if "%MONGO_PATH%"=="" (
    echo ❌ MongoDB installation not found
    echo Please install MongoDB Community Server first
    pause
    exit /b 1
)

echo 📁 Found MongoDB at: %MONGO_PATH%

REM Create data directory
if not exist "C:\data\db" mkdir "C:\data\db"

REM Install service
sc create MongoDB binPath= "\"%MONGO_PATH%\" --service --dbpath=\"C:\data\db\" --logpath=\"C:\data\db\mongod.log\"" start= auto DisplayName= "MongoDB Database Server"

if %errorLevel% == 0 (
    echo ✅ MongoDB service created successfully
) else (
    echo ❌ Failed to create MongoDB service
    pause
    exit /b 1
)

echo 🚀 Starting MongoDB service...
sc start MongoDB

if %errorLevel% == 0 (
    echo ✅ MongoDB service started successfully
) else (
    echo ⚠️ Service may need a moment to start
)

echo.
echo 🎉 MongoDB is now configured as a Windows service!
echo 🔄 MongoDB will automatically start with Windows
echo 📊 Service Name: MongoDB
echo 💾 Data Path: C:\data\db
echo 📄 Log File: C:\data\db\mongod.log
echo.
echo To manage the service:
echo   Start: sc start MongoDB
echo   Stop: sc stop MongoDB
echo   Status: sc query MongoDB
echo.
pause
