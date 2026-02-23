# 🧠 Aegis AI - Brain & Core Logic

**Project ID:** AEGIS-CORE-2026

## 🏗️ System Architecture & Role
The **Aegis AI Brain** lies at the heart of the DECISION CENTER in the Aegis Core Cloud. It works intimately with the **Temporal Server** to supervise the orchestration and AI logic of the entire vulnerability detection and exploitation flow.

* **Tech Stack:** Python (Temporal-SDK).
* **Role:**
  * Executes long-running penetration testing workflows, sagas, and state retries.
  * Interacts with Neo4j (Topology Graph) to calculate real-time attack vectors.
  * Emits commands to the Infinite Worker Pools (Ingest, Pentest, Deployer/Fixer).
* **Architecture Justification:** Python offers rapid integration with bleeding-edge AI logic ecosystems and Temporal provides durable, resilient workflows capable of surviving pod crashes (< 2s RTO).

## 🔐 Security & DevSecOps Mandates
* **No Plain-Text Secrets:** Secrets injected dynamically at runtime (Infisical).
* **High Availability:** Runs in an HA Mode ReplicaSet to instantly resume workflows upon node failure.

## 🐳 Docker Container Deployment
Immutable, K8s-ready Python 3.11+ container, stripped of capabilities.

```bash
docker pull ghcr.io/aegis-ai/aegis-brain:latest

# Secured execution, strictly non-root
infisical run --env=prod -- docker run -d \
  --name aegis-brain \
  --read-only \
  --cap-drop=ALL \
  --security-opt no-new-privileges:true \
  --user 10001:10001 \
  -e INFISICAL_TOKEN=$INFISICAL_TOKEN \
  ghcr.io/aegis-ai/aegis-brain:latest
```
