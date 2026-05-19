"""Orchestrator Agent - Pure User OAuth Architecture."""

import os
import yaml
import httpx
from urllib.parse import urlparse
from pathlib import Path
from contextvars import ContextVar

from google.adk.agents.llm_agent import LlmAgent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent
from a2a.client.client import ClientConfig as A2AClientConfig
from a2a.client.client_factory import ClientFactory as A2AClientFactory

# --- 0. ContextVar for Identity Bridging ---
# Holds the user's OAuth id_token captured during login in server.py.
current_user_token: ContextVar[str | None] = ContextVar("current_user_token", default=None)

# --- 1. Pure User identity Auth ---
class UserIdentityAuth(httpx.Auth):
    """
    Forwards the user's Google OAuth id_token as the Bearer token.
    Proves to Cloud Run B (via IAP) that the HUMAN user is calling.
    No Service Account or fetch_id_token used.
    """
    def auth_flow(self, request):
        # Extract the user's actual identity token from the async context
        user_id_token = current_user_token.get()
        
        if user_id_token:
            # Matches Lead's Architecture: id_token in Authorization header
            request.headers["Authorization"] = f"Bearer {user_id_token}"
            print("✅ Attaching User OAuth Identity for Cloud Run B")
        else:
            print("⚠️ No User Identity found to forward")
            
        yield request

def get_user_identity_factory():
    """Returns a factory that uses the user's forwarded identity."""
    async_client = httpx.AsyncClient(
        timeout=httpx.Timeout(timeout=30),
        auth=UserIdentityAuth() 
    )
    return A2AClientFactory(config=A2AClientConfig(httpx_client=async_client))

# --- 2. Orchestrator Initialization ---
def load_remote_agents(config_path: str = None):
    if config_path is None:
        config_path = Path(__file__).parent / "agents_config.yaml"
    else:
        config_path = Path(config_path)

    base_dir = config_path.parent.absolute()

    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    remote_agents = []
    agent_descriptions = []
    
    # Use the User Identity factory for all remote calls
    factory = get_user_identity_factory()

    for agent_config in config.get('remote_agents', []):
        if not agent_config.get('enabled', True):
            continue
            
        url = agent_config['agent_card_url'].replace("{base_dir}", str(base_dir))

        # We always want to apply the UserIdentityAuth factory because even if we load the card locally,
        # the actual RPC requests (the ones we need to secure) will be sent to the remote Cloud Run URL.
        remote_agent = RemoteA2aAgent(
            name=agent_config['name'],
            description=agent_config['description'],
            agent_card=url,
            a2a_client_factory=factory
        )

        remote_agents.append(remote_agent)
        agent_descriptions.append(f"- {agent_config['name']}: {agent_config['description']}")
        print(f"✅ Loaded {agent_config['name']} with Pure User Identity Auth")

    return remote_agents, agent_descriptions

remote_agents, agent_descriptions = load_remote_agents()
agent_list_text = "\n".join(agent_descriptions)

orchestrator_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="orchestrator_agent",
    description="Orchestrator - Pure User Identity Delegation",
    instruction=f"""
You are a root orchestrator agent. Use specialized agents to fulfill requests:
{agent_list_text}

When the user asks for a math calculation or unit conversion, transfer to the calculator_agent.
    """,
    sub_agents=remote_agents,
)

root_agent = orchestrator_agent
