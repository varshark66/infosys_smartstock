@echo off
title MongoDB Auto-Start for SmartStock
color 0A

echo 🔄 SmartStock MongoDB Auto-Start Script
echo.

REM Check if MongoDB is already running
tasklist /FI "IMAGENAME eq mongod.exe" 2>NUL | find /I "mongod.exe" >NUL
if %ERRORLEVEL% == 0 (
    echo ✅ MongoDB is already running
    goto :test_connection
)

echo 🚀 Starting MongoDB server...

REM Create data directory if it doesn't exist
if not exist "C:\data\db" mkdir "C:\data\db"

REM Start MongoDB in background
start /B mongod --dbpath "C:\data\db" --logpath "C:\data\db\mongod.log"

echo ⏳ Waiting for MongoDB to start...
timeout /t 3 /nobreak >nul

:test_connection
echo 🔗 Testing MongoDB connection...
python -c "from pymongo import MongoClient; client = MongoClient('mongodb://localhost:27017/', serverSelectionTimeoutMS=5000); client.admin.command('ping'); print('CONNECTION_SUCCESS')" >temp_output.txt 2>&1

findstr "CONNECTION_SUCCESS" temp_output.txt >nul
if %ERRORLEVEL% == 0 (
    echo ✅ MongoDB connection test passed
    echo 🎉 MongoDB is ready for SmartStock!
) else (
    echo ❌ MongoDB connection test failed
    type temp_output.txt
    del temp_output.txt
    pause
    exit /b 1
)

del temp_output.txt
echo.
echo MongoDB is running and ready!
pause
