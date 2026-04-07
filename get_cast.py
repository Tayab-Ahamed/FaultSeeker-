import urllib.request
import zipfile
import os
import json

print("Fetching latest Windows release of Foundry...")
req = urllib.request.Request("https://api.github.com/repos/foundry-rs/foundry/releases/latest", headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
    
    download_url = None
    for asset in data.get('assets', []):
        if 'win32_amd64.zip' in asset['name']:
            download_url = asset['browser_download_url']
            break
            
    if not download_url:
        print("Could not find Windows asset in the latest release! Proceed with caution.")
        exit(1)
        
    print(f"Downloading from: {download_url}")
    
    # Use proper User-Agent to avoid GitHub returning 404 for python's default urllib request
    req2 = urllib.request.Request(download_url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req2) as resp, open("foundry.zip", 'wb') as out_file:
        out_file.write(resp.read())
        
    print("Extracting cast.exe...")
    with zipfile.ZipFile("foundry.zip", 'r') as zip_ref:
        zip_ref.extract("cast.exe", ".")
    os.remove("foundry.zip")
    print("\n✅ Success! cast.exe is now in the current folder.")
except Exception as e:
    print(f"Error: {e}")
