# Zero Trust Agent-to-Agent (A2A) Architecture POC

This Proof of Concept (POC) demonstrates a highly secure, enterprise-grade Agent-to-Agent communication pattern across different Google Cloud Projects.

It solves the complex problem of **Human Identity Delegation**: allowing a human user to authenticate with an Orchestrator agent, and having that exact human identity verified by a downstream Calculator agent in a different GCP project, using native infrastructure (Google Cloud IAP) for authorization.

## Architecture: Shared Identity Domain (OIDC + OAuth + IAP)

This architecture utilizes a "Shared Identity Domain" pattern. By sharing a single Google OAuth Client ID across both the application layer (Orchestrator) and the infrastructure layer (Calculator IAP), we achieve seamless identity propagation without custom authentication code in the downstream services.

### The Flow

1.  **User Authentication (Orchestrator):** A user accesses the Orchestrator UI. The Orchestrator intercepts the request and performs a standard Google OAuth 2.0 Web Server flow, capturing the user's `id_token` and storing it in a secure session.
2.  **A2A Communication:** When the user sends a message requiring the Calculator, the Orchestrator's interceptor extracts the human `id_token` from the session and attaches it to the `Authorization: Bearer <id_token>` header of the RPC request.
3.  **Infrastructure Authorization (Calculator IAP):** The request arrives at Cloud Run B (Calculator). Before hitting the application code, Google Cloud IAP intercepts it. IAP cryptographically verifies the `id_token`. Because both projects share the same OAuth Client ID, IAP recognizes the token's `audience` and accepts it.
4.  **Native IAM (Zero Code):** IAP checks its IAM policy (`IAP-secured Web App User`). If the user (e.g., `rafiqh@google.com`) is authorized, the request is allowed through. If not, IAP drops the request natively (403 Forbidden). The Calculator agent contains **zero custom authentication code**.

## Directory Structure

*   `orchestrator_agent/`: The root agent containing the FastAPI server, the OAuth login flow, and the ADK Web UI.
*   `calculator_agent/`: The downstream agent containing pure business logic (math/conversion).

---

## 🚀 GCP Deployment Guide

This setup requires precise configuration in the Google Cloud Console across two projects.

### Phase 1: Create the "Bank-Wide" OAuth Client (Project A)

1.  Go to **Project A** (`hasanrafiq-test-331814`) -> APIs & Services -> Credentials.
2.  Create an **OAuth Client ID** (Web application).
3.  Add the **IAP Redirect URI** to the "Authorized redirect URIs":
    `https://iap.googleapis.com/v1/oauth/clientIds/<YOUR_CLIENT_ID>:handleRedirect`
4.  **Crucial:** Also add your **Orchestrator Callback URL** once known:
    `https://orchestrator-agent-xxx.run.app/callback`
5.  Copy the `CLIENT_ID` and `CLIENT_SECRET`.

### Phase 2: Deploy Calculator Agent (Project B)

Deploy the Calculator service. Notice we do not pass any authentication variables.

```bash
gcloud run deploy calculator-agent \
  --source ./calculator_agent \
  --region us-central1 \
  --no-allow-unauthenticated \
  --project=PROJECT_B \
  --set-env-vars="BASE_URL=https://calculator-agent-xxx.us-central1.run.app"
```

### Phase 3: Configure Shared IAP (Project B)

1.  Go to **Project B** -> Security -> Identity-Aware Proxy.
2.  Select the `calculator-agent` service.
3.  Open the info panel on the right and select **"Use a custom OAuth client"**.
4.  Paste the **Client ID** and **Client Secret** generated in Project A.
5.  **Authorization:** Add your Google Group (e.g., `payments-team@yourbank.com`) to the **"IAP-secured Web App User"** role.

### Phase 4: Deploy Orchestrator Agent (Project A)

1.  **Generate the Agent Card:** 
    ```bash
    CALCULATOR_URL=https://calculator-agent-xxx.run.app/ python3 orchestrator_agent/generate_card.py
    ```
2.  **Deploy Orchestrator:**
    ```bash
    gcloud run deploy orchestrator-agent \
      --source . \
      --region us-central1 \
      --allow-unauthenticated \
      --project=PROJECT_A \
      --set-env-vars="\
    GOOGLE_CLIENT_ID=<YOUR_CLIENT_ID>,\
    GOOGLE_CLIENT_SECRET=<YOUR_CLIENT_SECRET>,\
    FLASK_SECRET_KEY=$(openssl rand -base64 32)"
    ```

---

## 🏛️ Production Considerations (The "Scale" Strategy)

In this POC, we use a local JSON file (`calculator_card.json`) to bypass IAP during the Orchestrator's startup phase. For a production deployment at scale:

1.  **Agent Registry:** Instead of local files, agent cards should be stored in a centralized **Agent Registry** (e.g., a Firestore database or a central internal portal).
2.  **Dynamic Discovery:** Downstream agents should register themselves with this central registry upon deployment. 
3.  **Discovery API:** The Orchestrator should call a "Discovery API" (also protected by the Bank's shared OAuth) to retrieve the cards it needs, rather than fetching them directly from the downstream agents' IAP-protected URLs.

---

## 💻 Local Development

1.  **Environment Variables:** Create a `.env` file:
    ```env
    GOOGLE_CLIENT_ID=your-client-id
    GOOGLE_CLIENT_SECRET=your-client-secret
    FLASK_SECRET_KEY=super-secret-local-key
    ```
    *Add `http://localhost:8080/callback` to your OAuth Client's Authorized redirect URIs.*

2.  **Start:** `python3 orchestrator_agent/server.py`

## Key Security Features

*   **No Service Account Keys:** No JSON key files are used.
*   **Infrastructure Native:** IAP blocks unauthorized users before they hit your code.
*   **Identity Delegation:** The human user's exact identity is propagated across projects.
