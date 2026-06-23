import urllib.request

url = 'http://127.0.0.1:5000/'
try:
    with urllib.request.urlopen(url, timeout=5) as response:
        print(response.status)
        print(response.read(200).decode('utf-8', errors='ignore'))
except Exception as e:
    print(type(e).__name__, e)
