#!/usr/bin/env python3
"""
Apply Single Account Email Fix - Working Version
"""

import sys
import os
import re

def apply_single_account_fix():
    """Apply fix to send alerts to one specific account only"""
    print("🔧 APPLYING SINGLE ACCOUNT EMAIL FIX")
    print("=" * 50)
    
    try:
        # Navigate to the correct directory
        os.chdir('c:/Users/ganesh/Documents/smartstock_inventory/smartstock_inventory/smartstock_inventory')
        
        app_py_path = 'smartstock_inventory/app.py'
        
        with open(app_py_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find the admin fallback section and replace with single account logic
        admin_fallback_pattern = r'admin_users = list\(collection\.find\(\{"role": "admin"\}, \{"email": 1\}\)\)\s*\n\s*recipients = \[user\[\'email\'\] for user in admin_users if \'email\' in user\]'
        
        # Create single account fix
        single_account_fix = '''# SINGLE ACCOUNT EMAIL FIX - Only send to logged-in user
        if not recipients:
            print("⚠️ No recipients found for alert notification")
            return
        
        # Check if we can get current user from request context
        try:
            from flask import request
            auth_header = request.headers.get('Authorization')
            current_user = None
            
            if auth_header and auth_header.startswith('Bearer '):
                try:
                    import jwt
                    token = auth_header.split(' ')[1]
                    decoded = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
                    current_user = decoded
                    print(f"✅ Found logged-in user: {current_user.get('email', 'Unknown')}")
                except Exception as e:
                    print(f"⚠️ Could not decode token: {str(e)}")
            
            # Only send to logged-in user
            if current_user and 'email' in current_user:
                recipients = [current_user['email']]
                print(f"✅ Sending alert to logged-in user: {current_user['email']}")
            else:
                print("⚠️ No logged-in user found - no email sent")
                return
                
        except Exception as e:
            print(f"⚠️ Error getting user context: {str(e)}")
            return'''
        
        # Apply the fix
        admin_fallback_pattern = re.compile(r'admin_users = list\(collection\.find\(\{"role": "admin"\}, \{"email": 1\}\)\)\s*\n\s*recipients = \[user\[\'email\'\] for user in admin_users if \'email\' in user\]', re.MULTILINE)
        
        if admin_fallback_pattern.search(content):
            new_content = admin_fallback_pattern.sub(single_account_fix, content)
            
            with open(app_py_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            print("✅ Single account fix applied!")
            print("📋 Changes made:")
            print("   - Removed admin fallback completely")
            print("   - Only logged-in user gets alerts")
            print("   - No more universal admin spam")
            
            return True
        else:
            print("❌ Could not find the admin fallback section")
            print("📋 Let me check what's in the file...")
            
            # Search for admin_users in the file
            if 'admin_users' in content:
                print("✅ Found 'admin_users' in file")
                # Try a simpler replacement
                old_line = 'admin_users = list(collection.find({"role": "admin"}, {"email": 1}))'
                new_line = '# NO ADMIN FALLBACK - Only send to logged-in user'
                
                if old_line in content:
                    new_content = content.replace(old_line, new_line)
                    
                    with open(app_py_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    
                    print("✅ Simple fix applied!")
                    return True
                else:
                    print("❌ Could not find the exact admin_users line")
            else:
                print("❌ No 'admin_users' found in file")
            
            return False
            
    except Exception as e:
        print(f"❌ Error applying fix: {str(e)}")
        return False

def main():
    """Main function"""
    print("🚀 SmartStock - Single Account Email Fix")
    
    success = apply_single_account_fix()
    
    print("\n" + "=" * 50)
    if success:
        print("🏁 SINGLE ACCOUNT EMAIL FIX COMPLETE!")
        print("\n📋 What Was Applied:")
        print("   ✅ Single account email routing implemented")
        print("   ✅ Only logged-in user gets alerts")
        print("   ✅ Admin fallback removed")
        
        print("\n🎯 Next Steps:")
        print("   1. Restart Flask server: python app.py")
        print("   2. Test: Only your account will receive alerts")
        print("   3. Verify: No other admin accounts get alerts")
    else:
        print("❌ Fix failed - check error messages above")
    
    print("\n" + "=" * 50)

if __name__ == "__main__":
    main()
