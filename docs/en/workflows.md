# The Aegis AI Brain (Orchestrator)

The Brain is the monolithic, asynchronous orchestrator in the Aegis ecosystem. Designed around Python, `asyncpg`, and `temporalio`, it ingests scanning orders via gRPC and commands the worker fleet through complex Temporal Workflows.

## Architecture (MVP v2)
In version 2 of the framework, the Brain assumes the exclusive role of system orchestrator:
1. **gRPC Server Layer (`aegis.v2`)**: Listens continuously for requests originating from the API Gateway.
2. **PostgreSQL Asynchronous Client**: Persists scan states, handles UUID generation, logs incoming vulnerabilities, and archives evidence blobs via `asyncpg`.
3. **Temporal Client**: Launches asynchronous, distributed workflows across the worker cluster (`pentest-worker`, `ingest-worker`, etc.).

## Temporal Workflows Overview

### 1. `PentestWorkflow`
The most critical workflow in Aegis AI. When triggered through the gRPC `StartScan`, the Brain begins stepping through activities:

- **`deploy_sandbox_target` (Kubernetes Activity):** Dynamically spins up a sterile target namespace (`aegis-war-room-{scan_id}`) where the vulnerable image is exposed under strict network isolation.
- **`run_pentest` (Pentest Worker):** In parallel, commands the remote pentest-worker node to blast payloads into the target within the sandbox. The worker generates `Evidences` and `Vulnerabilities` streams sent back to the temporal history.
- **`cleanup_sandbox` (Kubernetes Activity):** Dismantles the target namespace to restore cluster equilibrium once the scan is successfully concluded.

## Zero Trust Security Scope
The Brain is securely locked away within `aegis-system`. By Cilium Network Policies, it is the solitary component explicitly permitted inward ingress traffic to the `aegis-postgres-mvp` namespace.
