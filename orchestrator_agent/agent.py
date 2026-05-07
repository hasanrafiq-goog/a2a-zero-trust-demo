"""Orchestrator Agent with Simple Zero Trust A2A setup."""

import os
import yaml
import httpx
from urllib.parse import urlparse
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2 import id_token
import google.auth
from google.auth import impersonated_credentials
from google.adk.agents.llm_agent import LlmAgent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent

from a2a.client.client import ClientConfig as A2AClientConfig
from a2a.client.client_factory import ClientFactory as A2AClientFactory

# --- Robust OIDC Fetching ---
def get_robust_id_token(audience: str) -> str:
    """Acquires an ID token for Cloud Run Identity."""
    creds, _ = google.auth.default()
    auth_req = Request()
    if isinstance(creds, impersonated_credentials.Credentials):
        id_creds = impersonated_credentials.IDTokenCredentials(creds, target_audience=audience, include_email=True)
        id_creds.refresh(auth_req)
        return id_creds.token
    if hasattr(creds, "id_token") and creds.id_token:
        return creds.id_token
    creds.refresh(auth_req)
    if hasattr(creds, "id_token") and creds.id_token:
        return creds.id_token
    return id_token.fetch_id_token(auth_req, audience)

class GoogleIdTokenAuth(httpx.Auth):
    """
    Injects OIDC Token into the STANDARD Authorization header.
    This is what Cloud Run natively expects.
    """
    def __init__(self, audience: str):
        self.audience = audience

    def auth_flow(self, request):        
        token = get_robust_id_token(self.audience)
        request.headers["Authorization"] = f"Bearer {token}"
        yield request

def get_cloud_run_client_factory(agent_path: str):
    """Client Factory for Cloud Run authentication."""
    parsed_url = urlparse(agent_path)
    service_uri = f"{parsed_url.scheme}://{parsed_url.netloc}"

    async_client = httpx.AsyncClient(
        timeout=httpx.Timeout(timeout=30), 
        auth=GoogleIdTokenAuth(service_uri)
    )
    return A2AClientFactory(A2AClientConfig(httpx_client=async_client))

# --- Orchestrator Logic ---
def load_remote_agents(config_path: str = None):
    if config_path is None:
        config_path = Path(__file__).parent / "agents_config.yaml"

    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    remote_agents = []
    agent_descriptions = []

    for agent_config in config.get('remote_agents', []):
        if not agent_config.get('enabled', True):
            continue
            
        url = agent_config['agent_card_url']
        
        # Inject OIDC logic ONLY for Cloud Run URLs
        factory = None
        if "run.app" in url:
            factory = get_cloud_run_client_factory(url)

        remote_agent = RemoteA2aAgent(
            name=agent_config['name'],
            description=agent_config['description'],
            agent_card=url,
            a2a_client_factory=factory
        )

        remote_agents.append(remote_agent)
        agent_descriptions.append(
            f"- {agent_config['name']}: {agent_config['description']}"
        )
        print(f"✅ Loaded {agent_config['name']} with Zero Trust Factory")

    return remote_agents, agent_descriptions

# Load remote agents dynamically
remote_agents, agent_descriptions = load_remote_agents()
agent_list_text = "\n".join(agent_descriptions)

# Create Orchestrator Agent
orchestrator_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="orchestrator_agent",
    description="Orchestrator with Native Cloud Run Zero Trust Authentication",
    instruction=f"""
You are a root orchestrator agent. Use specialized agents:
{agent_list_text}

For mathematical calculations or unit conversions, transfer to the calculator_agent.
    """,
    sub_agents=remote_agents,
)

root_agent = orchestrator_agent
