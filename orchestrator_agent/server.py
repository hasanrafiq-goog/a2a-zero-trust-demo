"""Custom FastAPI Entrypoint for ADK Orchestrator with Google OAuth."""

import os
import httpx
import json
import base64
import time
from fastapi import Request
from fastapi.responses import RedirectResponse, JSONResponse
from starlette.middleware.sessions import SessionMiddleware
from google.adk.cli.fast_api import get_fast_api_app

# Import the ContextVar from agent.py
from orchestrator_agent.agent import current_user_token

# --- OAuth Configuration ---
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
SESSION_SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "super-secret-local-key")
env_port = int(os.environ.get("PORT", 8080))

# --- Initialize ADK ---
app = get_fast_api_app(
    agents_dir=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    web=True,
    host="0.0.0.0",
    port=env_port,
    auto_create_session=True
)

def get_redirect_uri(request: Request) -> str:
    """Dynamically construct the redirect URI based on the request."""
    # Cloud Run terminates HTTPS and forwards as HTTP. 
    # Use X-Forwarded-Proto if available, otherwise fallback to request.url.scheme
    scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
    return f"{scheme}://{request.url.netloc}/callback"

# --- Token Refresh Logic ---
async def refresh_google_id_token(refresh_token: str):

    """Refreshes the id_token using the refresh_token."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token"
            }
        )
    tokens = response.json()
    return tokens.get("id_token")

# --- OAuth Routes ---
@app.get("/login")
async def login(request: Request):
    """Redirects to Google OAuth."""
    if not GOOGLE_CLIENT_ID:
        return JSONResponse({"error": "GOOGLE_CLIENT_ID not configured"}, status_code=500)
        
    dynamic_redirect_uri = get_redirect_uri(request)
        
    google_auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={GOOGLE_CLIENT_ID}"
        f"&redirect_uri={dynamic_redirect_uri}"
        "&scope=openid email profile"
        "&response_type=code"
        "&access_type=offline"
        "&prompt=consent" # matches Lead's plan to get refresh_token
    )
    return RedirectResponse(google_auth_url)

@app.get("/callback")
async def callback(request: Request):
    """Handles the Google OAuth callback and stores the token."""
    code = request.query_params.get("code")
    if not code:
        return JSONResponse({"error": "No code returned"}, status_code=400)
        
    dynamic_redirect_uri = get_redirect_uri(request)

    # Exchange code for tokens
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": dynamic_redirect_uri,
                "grant_type": "authorization_code"
            }
        )
        
    tokens = token_response.json()
    if "error" in tokens:
        return JSONResponse({"error": tokens["error"]}, status_code=400)

    # Store in session
    request.session["id_token"] = tokens.get("id_token")
    request.session["refresh_token"] = tokens.get("refresh_token")
    
    return RedirectResponse("/")

# --- Authentication Middleware ---
@app.middleware("http")
async def require_auth(request: Request, call_next):
    # 1. Public endpoint bypass
    if request.url.path in ["/login", "/callback", "/health", "/.well-known/agent-card.json"] or request.url.path.startswith("/dev-ui"):
        return await call_next(request)
        
    id_token_jwt = request.session.get("id_token")
    refresh_token = request.session.get("refresh_token")
        
    # 2. Redirect to login if no token
    if not id_token_jwt:
        if "text/html" in request.headers.get("accept", "") or request.url.path == "/":
            return RedirectResponse("/login")
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    # 3. Handle Token Expiry (matches Lead's Step 4)
    try:
        parts = id_token_jwt.split(".")
        payload = json.loads(base64.urlsafe_b64decode(parts[1] + "==").decode())
        exp = payload.get("exp", 0)
        
        # If token expires in less than 5 minutes, refresh it
        if exp - time.time() < 300:
            print("🔄 User id_token is expiring soon. Refreshing...")
            new_id_token = await refresh_google_id_token(refresh_token)
            if new_id_token:
                request.session["id_token"] = new_id_token
                id_token_jwt = new_id_token
    except Exception as e:
        print(f"⚠️ Token decode failed: {e}")

    # 4. ** THE BRIDGE **
    # Pass the human user's actual identity to the ADK agent layer.
    token_context = current_user_token.set(id_token_jwt)
    
    try:
        response = await call_next(request)
    finally:
        current_user_token.reset(token_context)
        
    return response

# Add SessionMiddleware LAST so it is the outermost layer (executes first)
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET_KEY)

if __name__ == "__main__":
    import uvicorn
    print(f"Starting Orchestrator Server on port {env_port}")
    uvicorn.run(app, host="0.0.0.0", port=env_port)
