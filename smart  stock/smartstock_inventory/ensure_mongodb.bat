@echo off
title MongoDB Connection Ensurer
color 0B

echo 🔍 MongoDB Connection Verification & Startup
echo ============================================
echo.

:check_mongodb
echo [1/4] Checking MongoDB status...
tasklist /FI "IMAGENAME eq mongod.exe" 2>NUL | find /I "mongod.exe" >NUL
if %ERRORLEVEL% == 0 (
    echo ✅ MongoDB process is running
    goto :test_connection
) else (
    echo ❌ MongoDB is not running
    goto :start_mongodb
)

:start_mongodb
echo [2/4] Starting MongoDB server...

REM Ensure data directory exists
if not exist "C:\data\db" (
    echo 📁 Creating MongoDB data directory...
    mkdir "C:\data\db"
)

REM Kill any existing MongoDB processes
taskkill /F /IM mongod.exe 2>NUL

REM Start MongoDB with explicit paths
echo 🚀 Starting MongoDB with database path: C:\data\db
start /MIN "MongoDB Server" mongod --dbpath "C:\data\db" --logpath "C:\data\db\mongod.log" --port 27017

echo ⏳ Waiting for MongoDB to initialize...
timeout /t 5 /nobreak >nul

:test_connection
echo [3/4] Testing MongoDB connection...

REM Create a temporary Python script to test connection
echo import sys > test_conn.py
echo try: >> test_conn.py
echo     from pymongo import MongoClient >> test_conn.py
echo     client = MongoClient('mongodb://localhost:27017/', serverSelectionTimeoutMS=10000) >> test_conn.py
echo     client.admin.command('ping') >> test_conn.py
echo     client.close() >> test_conn.py
echo     print('SUCCESS') >> test_conn.py
echo except Exception as e: >> test_conn.py
echo     print(f'ERROR: {e}') >> test_conn.py
echo     sys.exit(1) >> test_conn.py

python test_conn.py > connection_result.txt 2>&1

findstr "SUCCESS" connection_result.txt >NUL
if %ERRORLEVEL% == 0 (
    echo ✅ MongoDB connection successful
    goto :cleanup
) else (
    echo ❌ MongoDB connection failed
    echo 📄 Connection test output:
    type connection_result.txt
    goto :retry_connection
)

:retry_connection
echo [4/4] Retrying connection setup...
timeout /t 3 /nobreak >nul
goto :check_mongodb

:cleanup
del test_conn.py 2>NUL
del connection_result.txt 2>NUL

echo.
echo 🎉 MongoDB is ready and connected!
echo 📊 Status: Running on localhost:27017
echo 💾 Data Directory: C:\data\db
echo 📄 Log File: C:\data\db\mongod.log
echo.
echo ✅ SmartStock can now connect to MongoDB successfully
timeout /t 2 /nobreak >nul
exit /b 0
