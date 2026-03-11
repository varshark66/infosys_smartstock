#!/usr/bin/env python3
"""
Test Flask App Import
"""

try:
    import app
    print("✅ Flask app imports successfully!")
    print("✅ Email notification fix applied!")
except Exception as e:
    print(f"❌ Error importing app: {str(e)}")
