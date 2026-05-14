# A2A (Agent-to-Agent) Enterprise OAuth Demo

This repository demonstrates the **Agent-to-Agent (A2A)** protocol using the Google ADK library with an **Enterprise 3-Legged OAuth** security model. 

This version showcases cross-project communication between two Cloud Run services. It uses a **Dual-Header Zero Trust** architecture:
1. **Infrastructure Identity (OIDC):** Bypasses the Cloud Run IAM firewall using `X-Serverless-Authorization`.
2. **Application Authorization (OAuth 2.0):** Triggers a "Sign in with Google" popup to satisfy the A2A Agent Card requirements using the standard `Authorization` header.

## Architecture

1.  **Calculator Agent (Project B):** Secured with Cloud Run IAM (`--no-allow-unauthenticated`) AND broadcasts a native A2A OAuth2 Authorization Code flow in its Agent Card.
2.  **Orchestrator Agent (Project A):** Hosted on Cloud Run. It serves the ADK UI, forwards the User's Cloud Run identity, and acts as the OAuth Client to handle the popup negotiation.

---

## Deployment Guide

### Step 1: Deploy the Calculator Agent (Project B)

Deploy the calculator first to establish its public URL.

```bash
# 1. Switch to Project B
gcloud config set project <PROJECT_B_ID>

# 2. Swap to the Calculator Dockerfile
cp Dockerfile.calculator Dockerfile

# 3. Deploy (Note: BASE_URL is set dynamically to itself after the first deployment, but for the first time, omit it or update it later)
gcloud run deploy calculator-agent \
  --source . \
  --region us-central1 \
  --no-allow-unauthenticated \
  --set-env-vars="GOOGLE_GENAI_USE_VERTEXAI=True,GOOGLE_CLOUD_PROJECT=$(gcloud config get-value project),ADK_MODEL=gemini-2.5-flash,BASE_URL=https://<CALCULATOR_URL>"

# 4. Clean up
rm Dockerfile
```
*Note: Ensure `<CALCULATOR_URL>` is the actual Cloud Run URL assigned to the service.*

### Step 2: Setup IAM Permissions

Allow the **Human User** to invoke the Calculator service through the Cloud Run firewall:

```bash
gcloud run services add-iam-policy-binding calculator-agent \
  --member="user:$(gcloud config get-value account)" \
  --role="roles/run.invoker" \
  --region=us-central1
```

### Step 3: Create OAuth Credentials (GCP Console)

Before deploying the Orchestrator, you need credentials for the login popup.
1. Go to **Project A** in the GCP Console -> **APIs & Services** -> **Credentials**.
2. Click **Create Credentials** -> **OAuth client ID** (Web Application).
3. Under **Authorized redirect URIs**, add the callback URL for your Orchestrator (e.g., `http://localhost:8080/callback` if using the proxy, or `https://<ORCHESTRATOR_URL>/callback` if public).
4. Save the **Client ID** and **Client Secret**.

### Step 4: Configure & Deploy the Orchestrator Agent (Project A)

1. **Update Config:** Open `orchestrator_agent/agents_config.yaml` and paste the Calculator's URL.
2. **Deploy:** Switch to Project A and deploy the Orchestrator, injecting the OAuth credentials.

```bash
# 1. Switch to Project A
gcloud config set project <PROJECT_A_ID>

# 2. Swap to the Orchestrator Dockerfile
cp Dockerfile.orchestrator Dockerfile

# 3. Deploy
gcloud run deploy orchestrator-agent \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars="GOOGLE_GENAI_USE_VERTEXAI=True,GOOGLE_CLOUD_PROJECT=$(gcloud config get-value project),ADK_MODEL=gemini-2.5-flash,OAUTH_CLIENT_ID=<YOUR_CLIENT_ID>,OAUTH_CLIENT_SECRET=<YOUR_CLIENT_SECRET>"

# 4. Clean up
rm Dockerfile
```

---

## Interaction Flow

1.  Access the Orchestrator UI in your browser (via its Cloud Run URL or `gcloud run services proxy`).
2.  Ask the Orchestrator: *"Calculate 123 * 456"*.
3.  The Orchestrator detects the OAuth requirement from the Calculator's Agent Card.
4.  **Google Login Popup:** The ADK UI pauses the agent and shows a popup asking for your permission. Click "Allow".
5.  The ADK automatically captures the callback token, resumes the agent, and the math calculation proceeds securely!
