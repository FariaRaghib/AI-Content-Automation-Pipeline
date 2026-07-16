"""
Test Google Gemini API
----------------------
Verifies your API key works and generates test content.

Run:
    python test_gemini_api.py

This will:
1. Check API authentication
2. Send a test prompt
3. Verify response format
4. Print success/failure
"""

import os
import json
from dotenv import load_dotenv
import urllib.request
import urllib.parse

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    print("[FAIL] GOOGLE_API_KEY not found in .env")
    print("Add this to .env: GOOGLE_API_KEY=your_key_here")
    exit(1)

print(f"[OK] Found API key: {GOOGLE_API_KEY[:20]}...")

# Test 1: Simple ping
print("\n[CHECK] Test 1: API Authentication...")

GEMINI_MODEL = "gemini-3.5-flash"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GOOGLE_API_KEY}"

payload = {
    "contents": [
        {
            "parts": [
                {"text": "Say 'API is working' in exactly 3 words."}
            ]
        }
    ],
    "generationConfig": {
        "temperature": 0.7,
        "maxOutputTokens": 100,
    }
}

try:
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        GEMINI_URL,
        data=data,
        headers={"Content-Type": "application/json"}
    )
    
    with urllib.request.urlopen(req, timeout=10) as response:
        result = json.loads(response.read().decode('utf-8'))
        
    if 'candidates' in result:
        content = result['candidates'][0]['content']['parts'][0]['text']
        print(f"✅ API Authentication: SUCCESS")
        print(f"   Response: \"{content}\"")
        api_working = True
    else:
        print(f"[FAIL] Unexpected response format:")
        print(json.dumps(result, indent=2))
        api_working = False
        
except urllib.error.HTTPError as e:
    print(f"[FAIL] HTTP Error {e.code}: {e.reason}")
    if e.code == 400:
        print("   → Check that your API key is valid")
    elif e.code == 404:
        print("   → Model not found. Try gemini-1.5-flash instead")
    elif e.code == 429:
        print("   → Rate limited. Wait a minute and try again")
    api_working = False
    
except Exception as e:
    print(f"[FAIL] Error: {e}")
    api_working = False

# Test 2: Content generation
if api_working:
    print("\n[CHECK] Test 2: Content Generation (as Faria)...")
    
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": """You are Faria Raghib, founder of LeadQualify.

Write ONE short, punchy LinkedIn hook about lead scoring (under 100 chars).
Founder voice: direct, technical, no BS.

Output ONLY the hook, nothing else."""}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.8,
            "maxOutputTokens": 150,
        }
    }
    
    try:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            GEMINI_URL,
            data=data,
            headers={"Content-Type": "application/json"}
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode('utf-8'))
        
        if 'candidates' in result:
            hook = result['candidates'][0]['content']['parts'][0]['text']
            print(f"✅ Content Generation: SUCCESS")
            print(f"   Generated hook: \"{hook}\"")
            print(f"   Characters: {len(hook)}")
        else:
            print(f"[FAIL] Unexpected response")
            
    except Exception as e:
        print(f"[FAIL] Error: {e}")

# Summary
print("\n" + "="*60)
if api_working:
    print("✅ GOOGLE GEMINI API IS WORKING!")
    print("\nYou can now use hook_writer.py (real API version)")
    print("Replace hook_writer_mock.py with hook_writer.py in your workflow")
else:
    print("[FAIL] API IS NOT WORKING")
    print("\nUse hook_writer_mock.py instead (generates mock but high-quality hooks)")
    print("Or fix your API key and try again")

print("="*60)