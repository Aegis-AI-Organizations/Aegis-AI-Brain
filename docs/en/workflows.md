# The Aegis AI Brain (Orchestrator)

The Brain is the monolithic, asynchronous orchestrator in the Aegis ecosystem. Designed around Python, `psycopg`, and `temporalio`, it ingests scanning orders via gRPC and commands the worker fleet through complex Temporal Workflows.

## Architecture (MVP v2)
In version 2 of the framework, the Brain assumes the exclusive role of system orchestrator:
1. **gRPC Server Layer (`aegis.v2`)**: Listens continuously for requests originating from the API Gateway.
2. **PostgreSQL Client**: Persists scan states, handles UUID generation, logs incoming vulnerabilities, and archives evidence blobs via `psycopg`.
3. **Temporal Client**: Launches asynchronous, distributed workflows across the worker cluster (`pentest-worker`, `ingest-worker`, etc.).

## Temporal Workflows Overview

### 1. `PentestWorkflow`
The most critical workflow in Aegis AI. When triggered through the gRPC `StartScan`, the Brain begins stepping through activities:

- **`deploy_sandbox_target` (Kubernetes Activity):** Dynamically spins up a sterile target namespace (`aegis-war-room-{scan_id}`) where the vulnerable image is exposed under strict network isolation.
- **`run_pentest` (Pentest Worker):** In parallel, commands the remote pentest-worker node to blast payloads into the target within the sandbox. The worker generates `Evidences` and `Vulnerabilities` streams sent back to the temporal history.
- **`cleanup_sandbox` (Kubernetes Activity):** Dismantles the target namespace to restore cluster equilibrium once the scan is successfully concluded.

## Service Logic Flows

### 1. Post-payment Client Onboarding (MVP)
Onboarding is managed by Aegis administrators after payment. It creates the customer tenant and prepares the owner account, but the owner remains inactive until the first-login invitation is redeemed.

1.  **gRPC Request**: The API Gateway calls internal `OnboardCompany` rpc.
2.  **Entity Creation**: `CompanyService` saves the new `Company` record to PostgreSQL.
3.  **Token Generation**: A unique 32-char hex `deployment_token` (`ag_` prefix) is generated via `secrets.token_hex`.
4.  **Owner Initialization**: The initial "Owner" user is created, linked to the company, marked inactive, and assigned the `pending_activation` status.
5.  **Invitation Creation**: A one-time first-login invitation token (`aegis_inv_` prefix) is generated, hashed in PostgreSQL, and stored with an expiration date.
6.  **Onboarding Response**: The system returns the deployment token and raw invitation token. It does not return owner credentials.
7.  **Owner Activation**: The API Gateway calls `AuthService.SetupPassword` with the invitation token and the new password. The Brain validates that the invitation is unused and not expired, hashes the password, activates the owner, marks the invitation as used, and creates the initial session tokens.

## Zero Trust Security Scope
The Brain is securely locked away within `aegis-system`. By Cilium Network Policies, it is the solitary component explicitly permitted inward ingress traffic to the `aegis-postgres-mvp` namespace.
