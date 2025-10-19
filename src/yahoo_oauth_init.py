import base64, os, urllib.parse, http.server, socketserver, requests, webbrowser
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.environ["YAHOO_CLIENT_ID"]
CLIENT_SECRET = os.environ["YAHOO_CLIENT_SECRET"]
REDIRECT_URI = "https://bpzqj-66-165-11-251.a.free.pinggy.link/callback"
AUTH_URL = "https://api.login.yahoo.com/oauth2/request_auth"
TOKEN_URL = "https://api.login.yahoo.com/oauth2/get_token"
SCOPE = "fspt-w"  # Fantasy Sports read/write; read is implied. Yahoo uses scope at app-level.


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/callback?"):
            qs = urllib.parse.parse_qs(self.path.split("?", 1)[1])
            code = qs.get("code", [""])[0]
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Got code. You can close this window.")

            # Exchange for tokens
            auth = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
            data = {
                "grant_type": "authorization_code",
                "redirect_uri": REDIRECT_URI,
                "code": code,
            }
            headers = {
                "Authorization": f"Basic {auth}",
                "Content-Type": "application/x-www-form-urlencoded",
            }
            r = requests.post(TOKEN_URL, data=data, headers=headers, timeout=30)
            r.raise_for_status()
            print("\n=== Store these securely ===")
            print("access_token:", r.json().get("access_token"))
            print("refresh_token:", r.json().get("refresh_token"))
            print("expires_in:", r.json().get("expires_in"))
            os._exit(0)


PORT = 9876
params = {
    "client_id": CLIENT_ID,
    "redirect_uri": REDIRECT_URI,
    "response_type": "code",
    "language": "en-us",
}
url = f"{AUTH_URL}?{urllib.parse.urlencode(params)}"
print("Opening browser for Yahoo login...")
webbrowser.open(url)
with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print(f"Listening on {PORT} for callback...")
    httpd.serve_forever()
