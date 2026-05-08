"""Calculator Agent A2A Server with 3-Legged OAuth support."""

import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from urllib.parse import urlparse
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from .agent import root_agent

# Load .env file if it exists (local development)
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)

# --- A2A OAuth Security Configuration (3-Legged OAuth) ---
from a2a.types import OAuth2SecurityScheme, OAuthFlows, AuthorizationCodeOAuthFlow
from google.adk.a2a.utils.agent_card_builder import AgentCardBuilder

# Define the OAuth2 security scheme for Authorization Code Flow (triggers popups)
oauth_scheme = OAuth2SecurityScheme(
    description="Enterprise OAuth2 Authentication (3-Legged)",
    flows=OAuthFlows(
        authorization_code=AuthorizationCodeOAuthFlow(
            authorization_url="https://accounts.google.com/o/oauth2/auth",
            token_url="https://oauth2.googleapis.com/token",
            scopes={
                "https://www.googleapis.com/auth/cloud-platform": "Full access to GCP resources"
            }
        )
    )
)

async def build_card(port):
    base_url = os.environ.get("BASE_URL", f"http://localhost:{port}")
    rpc_url = f"{base_url.rstrip('/')}/rpc"
    
    # Initialize builder with absolute RPC URL
    builder = AgentCardBuilder(agent=root_agent, rpc_url=rpc_url)
    card = await builder.build() 
    
    # Attach security requirements to trigger the ADK Auth Flow (Popup)
    card.security_schemes = {"google_oauth": oauth_scheme}
    card.security = [{"google_oauth": ["https://www.googleapis.com/auth/cloud-platform"]}]
    return card

# Get the port from environment
port = int(os.environ.get("PORT", 8080))

# Initialize the async card building
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
agent_card = loop.run_until_complete(build_card(port))

# Create the A2A app
a2a_app = to_a2a(
    agent=root_agent, 
    host=urlparse(os.environ.get("BASE_URL", "http://localhost")).hostname or "localhost",
    port=port,
    agent_card=agent_card
)

if __name__ == '__main__':
    import uvicorn
    print(f"Starting Calculator Agent on port {port} (Scenario 2 - 3-Legged OAuth)")
    uvicorn.run(a2a_app, host='0.0.0.0', port=port)
