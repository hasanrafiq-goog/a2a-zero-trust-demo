"""Orchestrator Agent - User Identity Forwarding."""

import os
import yaml
import httpx
import subprocess
from urllib.parse import urlparse
from pathlib import Path
from google.adk.agents.llm_agent import LlmAgent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent
from a2a.client.client import ClientConfig as A2AClientConfig
from a2a.client.client_factory import ClientFactory as A2AClientFactory

# --- User Identity Forwarder ---
class UserIdentityAuth(httpx.Auth):
    """
    Simulates Single Sign-On (SSO) by explicitly fetching the human user's 
    OIDC token using gcloud and forwarding it in the Authorization header.
    """
    def __init__(self, audience: str):
        self.audience = audience

    def auth_flow(self, request):
        try:
            # We must use subprocess here because google.auth.default() inside 
            # Cloud Run will always return the Service Account token, not yours!
            result = subprocess.run(
                ["gcloud", "auth", "print-identity-token", f"--audiences={self.audience}"],
                capture_output=True, text=True, check=True
            )
            token = result.stdout.strip()
            
            # Put the USER token in the standard header for Cloud Run Firewall
            request.headers["Authorization"] = f"Bearer {token}"
            print(f"✅ Forwarding Human Identity for {self.audience}")
        except Exception as e:
            print(f"⚠️ Failed to fetch Human Identity: {e}")
        yield request

def get_identity_forwarding_factory(agent_url: str):
    parsed_url = urlparse(agent_url)
    service_uri = f"{parsed_url.scheme}://{parsed_url.netloc}"

    async_client = httpx.AsyncClient(
        timeout=httpx.Timeout(timeout=30),
        auth=UserIdentityAuth(service_uri) 
    )
    return A2AClientFactory(config=A2AClientConfig(httpx_client=async_client))

# --- Orchestrator Initialization ---
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
        
        # Apply the Identity Forwarding factory
        factory = get_identity_forwarding_factory(url) if "run.app" in url else None

        remote_agent = RemoteA2aAgent(
            name=agent_config['name'],
            description=agent_config['description'],
            agent_card=url,
            a2a_client_factory=factory
        )

        remote_agents.append(remote_agent)
        agent_descriptions.append(f"- {agent_config['name']}: {agent_config['description']}")
        print(f"✅ Loaded {agent_config['name']} with User Identity Forwarding")

    return remote_agents, agent_descriptions

remote_agents, agent_descriptions = load_remote_agents()
agent_list_text = "\n".join(agent_descriptions)

# Create Orchestrator Agent
orchestrator_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="orchestrator_agent",
    description="Orchestrator - Single Sign-On Identity Forwarding",
    instruction=f"""
You are a root orchestrator agent. Use specialized agents to fulfill requests:
{agent_list_text}

When the user asks for a math calculation or unit conversion, transfer to the calculator_agent.
    """,
    sub_agents=remote_agents,
)

root_agent = orchestrator_agent
