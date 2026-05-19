"""Calculator Agent A2A Server - Zero Auth Code (IAP Protected)."""

import os
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from urllib.parse import urlparse

from google.adk.a2a.utils.agent_to_a2a import to_a2a
from .agent import root_agent
from google.adk.a2a.utils.agent_card_builder import AgentCardBuilder

# Load .env file
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)

# --- Server Configuration ---
env_port = int(os.environ.get("PORT", 8080))
base_url = os.environ.get("BASE_URL", f"http://localhost:{env_port}")
parsed = urlparse(base_url)
host = parsed.hostname or "localhost"
protocol = parsed.scheme or "http"
broadcast_port = parsed.port or (443 if protocol == "https" else 80)

async def get_final_card():
    rpc_url = f"{protocol}://{host}:{broadcast_port}/"
    builder = AgentCardBuilder(agent=root_agent, rpc_url=rpc_url)
    return await builder.build()

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
agent_card = loop.run_until_complete(get_final_card())

# Create the A2A app
# NO CUSTOM MIDDLEWARE. 
# Matches Lead's Architecture: "Zero auth code — IAP handles everything"
a2a_app = to_a2a(
    agent=root_agent, 
    agent_card=agent_card,
    port=env_port
)

if __name__ == '__main__':
    import uvicorn
    print(f"Starting Calculator Agent with IAP Infrastructure Security on port {env_port}")
    uvicorn.run(a2a_app, host='0.0.0.0', port=env_port)
