# 🧠 Modèles IA & Orchestration — Aegis AI

Cette section documente la **stack IA** d'Aegis telle qu'elle est réellement implémentée
dans le repo [`Aegis-AI-Agent-Crew`](https://github.com/Aegis-AI-Organizations/Aegis-AI-Agent-Crew) :
un **orchestrateur multi-agents (CrewAI)** qui pilote **3 modèles LLM spécialisés**.

> ℹ️ Le repo `Aegis-AI-Brain` (orchestration Temporal) n'héberge pas ces modèles. La logique
> multi-agents vit dans `Aegis-AI-Agent-Crew`. Ces docs sont la synthèse du benchmark de
> sélection + de l'implémentation réelle du Crew.

## Stack retenue (confirmée par le code)

| Couche | Choix | Rôle | Fiche |
|--------|-------|------|-------|
| **Orchestration** | **CrewAI** | Coordonne les 3 agents en process séquentiel | [orchestrator-crewai.md](orchestrator-crewai.md) |
| **Agent 1 — Planner** | **Llama 3.1** (`llama3.1:8b`) | Analyse la cible & planifie les étapes du test | [planner-llama3.1.md](planner-llama3.1.md) |
| **Agent 2 — Guider** | **WhiteRabbitNeo** (`whiterabbitneo`) | Modélise les vulnérabilités, dirige l'exploitation, rédige le rapport | [guider-whiterabbitneo.md](guider-whiterabbitneo.md) |
| **Agent 3 — Executor** | **DeepSeek-Coder-V2** (`deepseek-coder-v2`) | Exécute les tools, valide les failles, écrit les correctifs (IaC/code) | [executor-deepseek-coder-v2.md](executor-deepseek-coder-v2.md) |

> ✅ Ces 4 choix correspondent exactement aux entrées **« (Choisi) »** du benchmark, et sont
> confirmés par `src/agents.py` + `.env.example` du repo Crew (provider **Ollama** par défaut).

## ⚠️ Note de nommage

Dans le **code du Crew**, les agents s'appellent **Planner / Guider / Executor**.
Dans le benchmark / le flux Aegis global, on parle plutôt de rôles **Brain (planification)**,
**Offensif/Pentest** et **Code/Remédiation**. Correspondance :

| Agent (code) | Rôle benchmark | Modèle |
|--------------|----------------|--------|
| Planner | Planificateur (Brain) | Llama 3.1 |
| Guider | Offensif & pentest | WhiteRabbitNeo |
| Executor | Code & correction | DeepSeek-Coder-V2 |

> ⚠️ Ne pas confondre avec la **flotte de workers** Aegis (`Worker-Ingest`, `Worker-Pentest`,
> `Worker-Deployer`, `Worker-Fixer`) qui est la couche d'exécution/infra, distincte de ce
> layer agent CrewAI.

## Flux d'exécution (process séquentiel CrewAI)

```
 Cible (TARGET_INFRASTRUCTURE)
        │
        ▼
 ┌──────────────┐   plan         ┌──────────────┐   risques/payloads   ┌──────────────┐
 │   PLANNER    │ ─────────────▶ │    GUIDER    │ ───────────────────▶ │   EXECUTOR   │
 │  Llama 3.1   │                │WhiteRabbitNeo│                      │ DeepSeek-V2  │
 └──────────────┘                └──────┬───────┘                      └──────┬───────┘
                                        │  ▲  rapport final                   │ tools + patches
                                        │  └─────────────────────────────────┘
                                        ▼
                            security_report_findings.md
```

1. **Planning task** → Planner : décompose la cible, produit un plan de test structuré.
2. **Guider task** → Guider : évalue les risques, propose vecteurs d'exploit & payloads.
3. **Execution task** → Executor : lance les tools, confirme les failles, écrit les correctifs.
4. **Report task** → Guider : compile le rapport pentest exécutif final.

## Convention des fiches

Chaque model card suit la structure :
Vue d'ensemble · Infos générales · Architecture · Specs techniques · Données d'entraînement ·
Fine-tuning · I/O · Intégration dans Aegis · Évaluation · Limites & risques · Usage.

> Les specs marquées **⚠️ À CONFIRMER** dépendent du déploiement (tag/quantization Ollama,
> GPU, version exacte) et ne sont pas figées dans le repo Crew.
