#!/usr/bin/env python3
"""
One-time setup script to authorize the YouTube API.

Steps before running:
1. Go to https://console.cloud.google.com/
2. Create a project (or select an existing one)
3. Enable "YouTube Data API v3" and "YouTube Analytics API"
4. Go to APIs & Services > Credentials > Create Credentials > OAuth client ID
5. Choose "Desktop app" as the application type
6. Download the JSON file and save it as 'client_secret.json' in this directory

Then run:
    python setup_youtube.py

A browser window will open for you to authorize with your YouTube account.
The resulting token is saved to .youtube_token.json (local use) and printed
as a JSON string you can paste into the YOUTUBE_TOKEN_JSON env var on Render.
"""

import json
import os
import sys

try:
    from google_auth_oauthlib.flow import InstalledAppFlow
except ImportError:
    print("Missing dependency. Install it with:")
    print("  pip install google-auth-oauthlib")
    sys.exit(1)

SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]

CLIENT_SECRET_FILE = os.path.join(os.path.dirname(__file__) or ".", "client_secret.json")
TOKEN_FILE = os.path.join(os.path.dirname(__file__) or ".", ".youtube_token.json")


def main():
    if not os.path.exists(CLIENT_SECRET_FILE):
        print(f"ERROR: '{CLIENT_SECRET_FILE}' not found.")
        print()
        print("Download your OAuth client secret from Google Cloud Console:")
        print("  https://console.cloud.google.com/apis/credentials")
        print()
        print("Save it as 'client_secret.json' in this directory, then re-run.")
        sys.exit(1)

    print("Starting OAuth authorization flow...")
    print("A browser window will open. Sign in with the Google account that owns the YouTube channel.")
    print()

    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
    creds = flow.run_local_server(port=8090, prompt="consent")

    with open(TOKEN_FILE, "w") as f:
        f.write(creds.to_json())
    print(f"Token saved to {TOKEN_FILE}")

    print()
    print("=" * 60)
    print("FOR RENDER DEPLOYMENT:")
    print("=" * 60)
    print()
    print("Set the YOUTUBE_TOKEN_JSON environment variable to this value:")
    print()
    token_data = json.loads(creds.to_json())
    compact = json.dumps(token_data, separators=(",", ":"))
    print(compact)
    print()
    print("Copy the line above and paste it as the value of YOUTUBE_TOKEN_JSON")
    print("in your Render dashboard under Environment Variables.")
    print()
    print("Done! You can now run the app with: python app.py")


if __name__ == "__main__":
    main()
