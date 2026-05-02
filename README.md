# 🧠 Aegis AI - Brain Orchestrator

**Project ID:** AEGIS-CORE-2026

## 🏗️ System Architecture & Role
The **Aegis AI Brain** is the central "Decision Center" of the platform. It orchestrates complex, long-running vulnerability research workflows using **Temporal** and provides high-intelligence data via a **gRPC mTLS** interface.

* **Tech Stack:** Python 3.11+, **Temporal SDK**, gRPC (`grpcio` generated stubs), SQLAlchemy 2.0.
* **Role:**
  * **Workflow Engine**: Executes resilient, distributed penetration testing "Sagas".
  * **gRPC Server**: Serves as the source of truth for scans, vulnerabilities, and evidence.
  * **Graph Intelligence**: Interacts with **Neo4j** to map infrastructure topologies and attack paths.
  * **Report Engine**: Generates professional PDF penetration test reports.

---

## 🚀 Key Features

- **Durable Workflows**: Powered by Temporal, ensuring scans survive pod restarts and network partitions.
- **Internal mTLS**: Enforces bi-directional TLS for its gRPC server, only accepting connections from authorized clients (e.g., API Gateway).
- **Multi-tenancy**: Native support for company isolation and role-based access at the core logic level.
- **Asynchronous Processing**: Handles massive payloads and loot extraction using Python's `asyncio`.

---

## 🔐 Security & DevSecOps Mandates

- **mTLS Enforced**: The gRPC server **strictly requires** a valid client certificate signed by the Internal CA. Fallback to insecure is disabled.
- **Zero-Privilege**: Runs as a non-root, unprivileged user with no capability escalation.
- **Database Security**: Uses SQLAlchemy ORM models to ensure data integrity with PostgreSQL.

---

## 🐳 Deployment (Kubernetes)

```yaml
# Helm values example
tls:
  enabled: true
  caCert: "/etc/tls/ca.crt"
  serverCert: "/etc/tls/server.crt"
  serverKey: "/etc/tls/server.key"
env:
  TEMPORAL_HOST: "aegis-temporal-mvp-frontend:7233"
  DATABASE_URL: "postgresql://..."
```

---

## 🛠️ Development

```bash
# Install dependencies
poetry install

# Run the gRPC server
python src/grpc_server.py

# Run Temporal workers
python src/worker.py
```

*Aegis AI — Intelligence & Orchestration — 2026*
