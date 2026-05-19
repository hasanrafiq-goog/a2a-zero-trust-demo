# Zero Trust Agent-to-Agent (A2A) POC Registry

This repository contains Proof of Concept (POC) implementations for secure, cross-project Agent-to-Agent communication using Google ADK and GCP Identity infrastructure.

## 📌 Architecture Approaches

We have explored and documented two primary architectural patterns for handling identity propagation in a Zero Trust environment.

### 1. [Local-to-GCP Identity Flow](https://github.com/rafiqh/hsbc-a2a/tree/local-to-gcp)
*   **Target:** Local developers or on-prem services talking to Cloud Run.
*   **Mechanism:** Uses Service Account OIDC tokens with specific Audiences to pass through Cloud Run's IAM-protected URLs.
*   **Status:** Initial POC for infrastructure connectivity.

### 2. [GCP-to-GCP Human Identity Delegation](https://github.com/rafiqh/hsbc-a2a/tree/gcp-to-gcp)
*   **Target:** Cross-project production environments (e.g., Bank-grade deployments).
*   **Mechanism:** **Shared Identity Domain** using OIDC + OAuth.
*   **Key Features:**
    *   Orchestrator captures human `id_token` via standard Google OAuth login.
    *   Identity is propagated via `Authorization: Bearer` header.
    *   Native **IAP (Identity-Aware Proxy)** on the downstream agent verifies the token and enforces RBAC via Google Groups.
    *   **Zero custom auth code** in downstream agents.
*   **Status:** **Recommended Production Architecture.**

---

## 🚀 How to use this Repo

1.  Switch to the branch corresponding to your desired architecture.
2.  Follow the detailed `README.md` within that branch for deployment instructions.
3.  Ensure your GCP Console is configured according to the "Deployment Guide" in each branch.

---
*Created for the Zero Trust A2A Initiative.*
