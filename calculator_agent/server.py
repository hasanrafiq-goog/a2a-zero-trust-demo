"""Calculator Agent A2A Server."""

import os
from pathlib import Path
from dotenv import load_dotenv
from urllib.parse import urlparse
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from .agent import root_agent

# Load .env file if it exists (local development)
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
    print(f"Loaded .env from {env_path}")

# 1. Get the port (Cloud Run uses 8080, local uses 9001)
env_port = int(os.environ.get("PORT", 9001))

# 2. Extract configuration from BASE_URL
# This is crucial for Cloud Run so the Agent Card doesn't say 'localhost'
base_url = os.environ.get("BASE_URL")
host = "localhost"
protocol = "http"
broadcast_port = env_port

if base_url:
    parsed = urlparse(base_url)
    host = parsed.hostname
    protocol = parsed.scheme
    # Cloud Run handles the port mapping, so we usually broadcast 
    # the protocol's default port (443 for https) unless explicitly stated.
    if parsed.port:
        broadcast_port = parsed.port
    elif protocol == "https":
        broadcast_port = 443
    else:
        broadcast_port = 80
    print(f"🔧 Configured Agent Card for public URL: {protocol}://{host}:{broadcast_port}")

# 3. Create the A2A app.
# We pass the broadcast_port here so it shows up in the Agent Card.
a2a_app = to_a2a(
    agent=root_agent, 
    host=host,
    port=broadcast_port,
    protocol=protocol
)

if __name__ == '__main__':
    import uvicorn
    # Use the actual environment port for the server to listen on
    print(f"Starting Calculator Agent on port {env_port}")
    uvicorn.run(a2a_app, host='0.0.0.0', port=env_port)
