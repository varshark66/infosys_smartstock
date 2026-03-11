#!/usr/bin/env python3
"""
Test MongoDB Connection
"""

from pymongo import MongoClient

def test_mongodb_connection():
    """Test MongoDB connection"""
    try:
        print("🔍 Testing MongoDB connection...")
        client = MongoClient('mongodb://localhost:27017/', serverSelectionTimeoutMS=5000)
        client.server_info()
        print("✅ MongoDB connected successfully!")
        return True
    except Exception as e:
        print(f"❌ MongoDB connection failed: {str(e)}")
        return False

if __name__ == "__main__":
    test_mongodb_connection()
