"""
Setup script for Duke SSO authentication.

This script helps you set up the MFA cookie for authentication.
Supports loading from .env file or manual entry.
"""

import os
from dotenv import load_dotenv
from duke_sso import DukeSSOAuth

# Load environment variables from .env file
load_dotenv()


def main():
    print("=" * 60)
    print("Duke SSO Authentication Setup")
    print("=" * 60)
    print()
    print("To use the Duke course scraper, you need to:")
    print("1. Log in to DukeHub in your browser")
    print("2. Check 'Remember me' when prompted by Duo")
    print("3. Use browser dev tools to get the 'mfa' cookie value")
    print()
    print("Steps to get the MFA cookie:")
    print("1. Open DukeHub in your browser: https://dukehub.duke.edu")
    print("2. Log in with your NetID and complete Duo authentication")
    print("3. Open browser Developer Tools (F12)")
    print("4. Go to Application/Storage tab > Cookies > shib.oit.duke.edu")
    print("5. Find the 'mfa' cookie and copy its value")
    print()
    print("=" * 60)
    print()

    # Try to get MFA cookie from environment first
    mfa_cookie = os.getenv("DUKE_MFA_COOKIE", "").strip()

    if mfa_cookie:
        print("Found MFA cookie in .env file")
        use_env = input("Use this cookie? (y/n): ").strip().lower()
        if use_env != 'y':
            mfa_cookie = ""

    # If no cookie from env, get from user
    if not mfa_cookie:
        mfa_cookie = input("Paste your MFA cookie value here: ").strip()

    if not mfa_cookie:
        print("Error: No cookie value provided")
        return

    # Initialize auth and set cookie
    session_file = os.getenv("SESSION_FILE", "duke_session.pkl")
    auth = DukeSSOAuth(cookie_file=session_file)
    auth.set_mfa_cookie(mfa_cookie)
    auth.save_session()  # Save the MFA cookie

    # Try to login
    print("\nAttempting to authenticate...")
    if auth.login():
        print("\n✓ Authentication successful!")
        print(f"✓ Session saved to {session_file}")
        print("✓ MFA cookie is working")
        print()
        print("Tip: Add your MFA cookie to .env file to skip manual entry:")
        print("  1. Copy .env.example to .env")
        print("  2. Set DUKE_MFA_COOKIE=your_cookie_value")
        print()
        print("You can now run the scraper examples:")
        print("  python examples/basic_usage.py")
    else:
        print("\n✗ Authentication failed")
        print("Please check that:")
        print("  - Your MFA cookie is valid and not expired")
        print("  - You copied the entire cookie value")
        print("  - You checked 'Remember me' during Duo authentication")


if __name__ == "__main__":
    main()
