# A2A (Agent-to-Agent) Zero Trust Demo

This repository demonstrates the **Agent-to-Agent (A2A)** protocol using the Google ADK library with a **Zero Trust** security model on Google Cloud Run.

## Architecture

The project consists of two main components:

1.  **Calculator Agent (Remote):** A specialized agent deployed to Cloud Run that handles mathematical calculations and unit conversions. It is secured behind Cloud Run's IAM firewall.
2.  **Orchestrator Agent (Local/Hub):** A coordinator that dynamically loads and delegates tasks to remote agents. It implements **Identity Propagation** using Google OIDC ID tokens to securely communicate with the Calculator Agent.

## Getting Started

### Prerequisites

*   Python 3.11+
*   Google Cloud SDK (`gcloud`)
*   ADK installed: `pip install google-adk a2a-sdk`

### 1. Deploy the Calculator Agent to Cloud Run

From the project root, run the following command to deploy the Calculator Agent to your GCP project:

```bash
gcloud run deploy calculator-agent \
  --source . \
  --region us-central1 \
  --no-allow-unauthenticated \
  --set-env-vars="GOOGLE_GENAI_USE_VERTEXAI=True,GOOGLE_CLOUD_PROJECT=$(gcloud config get-value project),ADK_MODEL=gemini-2.5-flash,BASE_URL=https://<YOUR_SERVICE_URL>"
```

*Note: Replace `<YOUR_SERVICE_URL>` with the actual URL provided by Cloud Run after the first deployment attempt (you may need to redeploy once to set the `BASE_URL` correctly).*

### 2. Grant Permissions

Ensure your user identity (the one running the Orchestrator) has the permission to call the private Cloud Run service:

```bash
gcloud run services add-iam-policy-binding calculator-agent \
  --member="user:$(gcloud config get-value account)" \
  --role="roles/run.invoker" \
  --region=us-central1
```

### 3. Configure the Orchestrator

Update `orchestrator_agent/agents_config.yaml` with the Calculator Agent's URL:

```yaml
remote_agents:
  - name: "calculator_agent"
    agent_card_url: "https://<YOUR_SERVICE_URL>/.well-known/agent-card.json"
    enabled: true
```

### 4. Run the Orchestrator

1.  Establish Application Default Credentials (ADC) locally:
    ```bash
    gcloud auth application-default login
    ```
2.  Start the Orchestrator UI:
    ```bash
    cd orchestrator_agent
    adk web
    ```
3.  Access the UI at `http://127.0.0.1:8000` and start interacting with your secure A2A agent team!

## Security Notes

This POC implements **Zero Trust** by:
*   Using **OIDC Identity Tokens** (via `Authorization` header) to pass the Cloud Run IAM firewall.
*   Enforcing **IAM Authorization** so only specific identities can invoke the agent.
*   The architecture is designed to be easily extensible to **OAuth 2.0 Scopes** for granular application-level permissions.
