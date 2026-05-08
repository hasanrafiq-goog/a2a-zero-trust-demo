# A2A (Agent-to-Agent) Enterprise OAuth Demo

This repository demonstrates the **Agent-to-Agent (A2A)** protocol with an **Enterprise 3-Legged OAuth** security model. This version showcases cross-project communication between two Cloud Run services with explicit user consent (login popups).

## Architecture

1.  **Calculator Agent (Project B):** Secured with Cloud Run IAM AND a native A2A OAuth2 Authorization Code flow.
2.  **Orchestrator Agent (Project A):** Hosted on Cloud Run. It serves the ADK UI and orchestrates tasks. It forwards the User's identity and handles the OAuth popup negotiation.

## Deployment Steps

### 1. Deploy the Calculator Agent (Project B)

Point to Project B and deploy the calculator to get its public URL:

```bash
gcloud config set project <PROJECT_B_ID>

cp Dockerfile.calculator Dockerfile

gcloud run deploy calculator-agent \
  --source . \
  --region us-central1 \
  --no-allow-unauthenticated \
  --set-env-vars="GOOGLE_GENAI_USE_VERTEXAI=True,GOOGLE_CLOUD_PROJECT=$(gcloud config get-value project),ADK_MODEL=gemini-2.5-flash,BASE_URL=https://<CALCULATOR_URL>"

rm Dockerfile
```

### 2. Configure & Deploy the Orchestrator Agent (Project A)

1.  **Update Config:** Open `orchestrator_agent/agents_config.yaml` and paste the Calculator's URL.
2.  **Deploy:** Switch to Project A and deploy the Orchestrator:

```bash
gcloud config set project <PROJECT_A_ID>

cp Dockerfile.orchestrator Dockerfile

gcloud run deploy orchestrator-agent \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars="GOOGLE_GENAI_USE_VERTEXAI=True,GOOGLE_CLOUD_PROJECT=$(gcloud config get-value project),ADK_MODEL=gemini-2.5-flash"

rm Dockerfile
```

### 3. Setup IAM Permissions

Allow the **User** to invoke the Calculator service (switch back to Project B):

```bash
gcloud config set project <PROJECT_B_ID>

gcloud run services add-iam-policy-binding calculator-agent \
  --member="user:$(gcloud config get-value account)" \
  --role="roles/run.invoker" \
  --region=us-central1
```

### 4. Finalize OAuth (GCP Console)

Now that you have the **Orchestrator URL**, finalize the security handshake:

1.  **Create OAuth Client ID:** In GCP Console -> APIs & Services -> Credentials (Web Application).
2.  **Add Redirect URI:** Add `https://<ORCHESTRATOR_URL>/callback` to the Authorized Redirect URIs.

## Interaction Flow

1.  Access the Orchestrator URL in your browser.
2.  Ask "Calculate 123 * 456".
3.  The ADK UI will detect the OAuth requirement from the Calculator's Agent Card.
4.  **Google Login Popup:** You will see a popup asking for permission. Click "Allow".
5.  The request proceeds to the Calculator Agent securely using your personal identity!
