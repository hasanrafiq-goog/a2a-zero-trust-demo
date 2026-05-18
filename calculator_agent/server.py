"""Calculator Agent A2A Server."""

import os
from pathlib import Path
from dotenv import load_dotenv
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from .agent import root_agent

# Load .env file if it exists (local development)
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)

# Get the port from environment
port = int(os.environ.get("PORT", 8080))

# Create the A2A app natively.
# No custom cards or middleware needed.
# Google Cloud Run IAM (--no-allow-unauthenticated) provides 100% of the security.
a2a_app = to_a2a(
    agent=root_agent, 
    port=port
)

if __name__ == '__main__':
    import uvicorn
    print(f"Starting Calculator Agent on port {port} (Pure Cloud Run IAM Security)")
    uvicorn.run(a2a_app, host='0.0.0.0', port=port)
