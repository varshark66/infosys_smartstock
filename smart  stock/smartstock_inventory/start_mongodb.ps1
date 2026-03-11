# MongoDB Auto-Start Script for SmartStock
Write-Host "🔄 SmartStock MongoDB Auto-Start Script" -ForegroundColor Cyan

$mongoProcess = Get-Process -Name "mongod" -ErrorAction SilentlyContinue

if ($mongoProcess) {
    Write-Host "✅ MongoDB is already running (PID: $($mongoProcess.Id))" -ForegroundColor Green
}
else {
    Write-Host "🚀 Starting MongoDB server..." -ForegroundColor Yellow
    
    $dataPath = "C:\data\db"
    if (!(Test-Path $dataPath)) {
        New-Item -ItemType Directory -Path $dataPath -Force | Out-Null
        Write-Host "📁 Created MongoDB data directory: $dataPath" -ForegroundColor Blue
    }
    
    Start-Process -FilePath "mongod" -ArgumentList "--dbpath", $dataPath, "--logpath", "$dataPath\mongod.log" -WindowStyle Hidden
    
    Write-Host "⏳ Waiting for MongoDB to start..." -ForegroundColor Yellow
    Start-Sleep -Seconds 3
    
    $mongoProcess = Get-Process -Name "mongod" -ErrorAction SilentlyContinue
    if ($mongoProcess) {
        Write-Host "✅ MongoDB started successfully (PID: $($mongoProcess.Id))" -ForegroundColor Green
    }
    else {
        Write-Host "❌ Failed to start MongoDB" -ForegroundColor Red
        exit 1
    }
}

Write-Host "🔗 Testing MongoDB connection..." -ForegroundColor Yellow
try {
    $result = python -c "from pymongo import MongoClient; client = MongoClient('mongodb://localhost:27017/', serverSelectionTimeoutMS=5000); client.admin.command('ping'); print('CONNECTION_SUCCESS')"
    if ($result -match "CONNECTION_SUCCESS") {
        Write-Host "✅ MongoDB connection test passed" -ForegroundColor Green
    }
    else {
        Write-Host "❌ MongoDB connection test failed" -ForegroundColor Red
        exit 1
    }
}
catch {
    Write-Host "❌ MongoDB connection test failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host "🎉 MongoDB is ready for SmartStock!" -ForegroundColor Green
