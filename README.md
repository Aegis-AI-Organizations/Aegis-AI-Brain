# 🧠 Aegis AI - Brain & Offensive Engine

[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![Temporal](https://img.shields.io/badge/temporal-io-black.svg)](https://temporal.io/)
[![Docker](https://img.shields.io/badge/docker-ghcr.io-blue.svg)](https://github.com/features/packages)
[![Docs](https://img.shields.io/badge/docs-docusaurus-ff69b4.svg)](https://aegis-ai.github.io/docs)

**Aegis Brain** is the cognitive core and execution engine of the Aegis AI Offensive Cyberdefense platform. Written in Python, it acts as a fleet of intelligent Temporal workers capable of orchestrating complex attack workflows, performing graph-based network traversal (via Neo4j), and dynamically generating zero-day-like payloads using LLM hybridization. 

These workers execute their payloads strictly against isolated Digital Twins deployed in the `aegis-infra` sandbox.

## 📖 Full Documentation
This README focuses on deployment and quickstart instructions. For detailed architecture, workflow definitions, and API contracts, please visit our documentation portal:
👉 **[Aegis AI Documentation Portal (Docusaurus)](https://aegis-ai.github.io/docs)**

## ✨ Key Features
* **Durable Execution:** Powered by Temporal, the Brain guarantees that long-running attack workflows never lose state, even during critical worker crashes.
* **Graph-Based Reasoning:** Integrates with Neo4j to map target infrastructure and calculate the optimal attack path dynamically.
* **Cognitive Payloads:** Leverages LLM APIs (OpenAI/Mistral) to analyze target source code and generate custom exploits on the fly.
* **Stateless Workers:** The Brain workers hold no local state and can be scaled infinitely to parallelize large-scale penetration tests.

## 🚀 Quickstart: Running via GitHub Container Registry (GHCR)

The recommended way to deploy the Aegis Brain in production or staging environments is via our pre-built Docker images hosted on GHCR.

### 1. Pull the Image
```bash
docker pull ghcr.io/aegis-ai/aegis-brain:latest