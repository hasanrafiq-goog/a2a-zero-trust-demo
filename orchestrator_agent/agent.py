"""Orchestrator Agent with Enterprise 3-Legged OAuth setup."""

import os
import yaml
import httpx
import asyncio
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
from a2a.client.auth.interceptor import AuthInterceptor
from a2a.client.auth.credentials import CredentialService as A2ACredentialService
from a2a.client.middleware import ClientCallContext

# --- 1. Infrastructure Authentication (OIDC for Cloud Run Firewall) ---
def get_robust_id_token(audience: str) -> str:
    """Acquires an ID token for Cloud Run Identity (Infrastructure)."""
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

class CloudRunFirewallAuth(httpx.Auth):
    """
    Injects Identity Token into X-Serverless-Authorization header.
    This gets us through the Cloud Run IAM firewall, leaving the 
    standard 'Authorization' header free for the A2A OAuth token (the popup one).
    """
    def __init__(self, audience: str):
        self.audience = audience

    def auth_flow(self, request):
        try:
            token = get_robust_id_token(self.audience)
            request.headers["X-Serverless-Authorization"] = f"Bearer {token}"
        except Exception as e:
            print(f"⚠️ OIDC Token Fetch Failed: {e}")
        yield request

# --- 2. Application Authentication (OAuth for Agent Popup) ---
class GoogleOAuthCredentialService(A2ACredentialService):
    """
    This service is called by the ADK when it detects the 'auth_required' signal.
    It returns None if the token isn't in state, which triggers the UI Popup.
    """
    async def get_credentials(self, security_scheme_name: str, context: ClientCallContext | None) -> str | None:
        # In a real 3-legged flow, we look for the token in the session state.
        # If it's not there, ADK will initiate the interactive flow (Popup).
        if context and 'auth_tokens' in context.state:
            return context.state['auth_tokens'].get(security_scheme_name)
        return None

class ZeroTrustClientFactory(A2AClientFactory):
    """Injects the A2A Auth Interceptor to handle negotiated OAuth tokens."""
    def create(self, card, consumers=None, interceptors=None, extensions=None):
        if interceptors is None:
            interceptors = []
        
        # This interceptor handles the 'Authorization' header automatically 
        # based on the Agent Card negotiation.
        oauth_interceptor = AuthInterceptor(GoogleOAuthCredentialService())
        interceptors.append(oauth_interceptor)
        
        return super().create(card, consumers, interceptors, extensions)

def get_enterprise_factory(agent_url: str):
    parsed_url = urlparse(agent_url)
    service_uri = f"{parsed_url.scheme}://{parsed_url.netloc}"

    async_client = httpx.AsyncClient(
        timeout=httpx.Timeout(timeout=30),
        auth=CloudRunFirewallAuth(service_uri) # Handle the 'locked door' of Cloud Run
    )
    
    return ZeroTrustClientFactory(config=A2AClientConfig(httpx_client=async_client))

# --- 3. Orchestrator Initialization ---
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
        factory = get_enterprise_factory(url)

        remote_agent = RemoteA2aAgent(
            name=agent_config['name'],
            description=agent_config['description'],
            agent_card=url,
            a2a_client_factory=factory
        )

        remote_agents.append(remote_agent)
        agent_descriptions.append(f"- {agent_config['name']}: {agent_config['description']}")
        print(f"✅ Loaded {agent_config['name']} with Enterprise OAuth Support")

    return remote_agents, agent_descriptions

# Load remote agents
remote_agents, agent_descriptions = load_remote_agents()
agent_list_text = "\n".join(agent_descriptions)

# Create Orchestrator Agent
orchestrator_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="orchestrator_agent",
    description="Orchestrator with Enterprise 3-Legged OAuth (Popup) Support",
    instruction=f"""
You are a root orchestrator agent. Use specialized agents:
{agent_list_text}
    """,
    sub_agents=remote_agents,
)

root_agent = orchestrator_agent
