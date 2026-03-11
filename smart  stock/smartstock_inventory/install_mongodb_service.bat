@echo off
echo Installing MongoDB as Windows Service...

sc create MongoDB binPath= "\"C:\Program Files\MongoDB\Server\8.2\bin\mongod.exe\" --service --dbpath=\"C:\data\db\" --logpath=\"C:\data\db\mongod.log\"" start= auto

if errorlevel 1 (
    echo ❌ Failed to create MongoDB service
    pause
    exit /b 1
)

echo ✅ MongoDB service created successfully
echo Starting MongoDB service...
sc start MongoDB

if errorlevel 1 (
    echo ⚠️ Service may already be running or needs manual start
) else (
    echo ✅ MongoDB service started successfully
)

echo.
echo MongoDB will now automatically start with Windows
pause
