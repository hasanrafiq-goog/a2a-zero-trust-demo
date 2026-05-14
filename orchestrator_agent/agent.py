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

# A2A SDK Imports
from a2a.client.client import ClientConfig as A2AClientConfig
from a2a.client.client_factory import ClientFactory as A2AClientFactory
from a2a.client.auth.interceptor import AuthInterceptor
from a2a.client.auth.credentials import CredentialService as A2ACredentialService
from a2a.client.middleware import ClientCallContext

# ADK Native Auth Imports
from google.adk.auth.auth_credential import OAuth2Auth, AuthCredential, AuthCredentialTypes
from google.adk.auth.auth_provider_registry import AuthProviderRegistry
from google.adk.auth.base_auth_provider import BaseAuthProvider
from google.adk.auth.auth_schemes import ExtendedOAuth2

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
            print(f"✅ OIDC Identity injected into X-Serverless-Authorization for {self.audience}")
        except Exception as e:
            print(f"⚠️ OIDC Token Fetch Failed: {e}")
        yield request

# --- 2. Application Authentication (OAuth for Agent Popup) ---

class GoogleAuthProvider(BaseAuthProvider):
    """
    This class is the 'Brain' of the popup. 
    It tells the ADK UI which Client ID to use when showing the login screen.
    """
    async def get_auth_credential(self, auth_config, context):
        client_id = os.environ.get("OAUTH_CLIENT_ID")
        client_secret = os.environ.get("OAUTH_CLIENT_SECRET")
        
        if not client_id or not client_secret:
            print("⚠️ OAUTH_CLIENT_ID or OAUTH_CLIENT_SECRET not set in environment!")
            
        return AuthCredential(
            auth_type=AuthCredentialTypes.OAUTH2,
            oauth2=OAuth2Auth(
                client_id=client_id,
                client_secret=client_secret
            )
        )

# Register the provider globally in the Orchestrator
registry = AuthProviderRegistry()
# ExtendedOAuth2 is the internal class ADK uses to represent negotiated OAuth flows
registry.register(ExtendedOAuth2, GoogleAuthProvider())

class GoogleOAuthCredentialService(A2ACredentialService):
    """
    This service is called by the ADK when it detects the 'auth_required' signal.
    """
    async def get_credentials(self, security_scheme_name: str, context: ClientCallContext | None) -> str | None:
        # Check if the interactive flow has already populated the session state
        if context and 'auth_tokens' in context.state:
            token = context.state['auth_tokens'].get(security_scheme_name)
            if token:
                return token
        
        print(f"🔑 No OAuth token found for {security_scheme_name}. ADK will trigger Popup.")
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
    """Configures the Client Factory with the OIDC-aware HTTP client."""
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
        # Apply the Enterprise factory to all remote agents
        factory = get_enterprise_factory(url)

        remote_agent = RemoteA2aAgent(
            name=agent_config['name'],
            description=agent_config['description'],
            agent_card=url,
            a2a_client_factory=factory
        )

        remote_agents.append(remote_agent)
        agent_descriptions.append(f"- {agent_config['name']}: {agent_config['description']}")
        print(f"✅ Loaded {agent_config['name']} with Enterprise Zero Trust Factory")

    return remote_agents, agent_descriptions

# Load remote agents dynamically
remote_agents, agent_descriptions = load_remote_agents()
agent_list_text = "\n".join(agent_descriptions)

# Create Orchestrator Agent
orchestrator_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="orchestrator_agent",
    description="Orchestrator with Enterprise 3-Legged OAuth (Popup) Support",
    instruction=f"""
You are a root orchestrator agent. Use specialized agents to fulfill requests:
{agent_list_text}

When the user asks for a math calculation or unit conversion, transfer to the calculator_agent.
    """,
    sub_agents=remote_agents,
)

root_agent = orchestrator_agent
