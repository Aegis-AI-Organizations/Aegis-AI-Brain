# Orchestration — CrewAI

> Framework d'orchestration multi-agents retenu pour Aegis. Il coordonne les 3 modèles
> LLM spécialisés (Planner / Guider / Executor) et gère la façon dont ils communiquent.

---

## 1. Vue d'ensemble

- **Choix :** **CrewAI** (role-based multi-agent framework)
- **Rôle :** diriger les agents et orchestrer leur collaboration sur un **workflow séquentiel**.
- **Implémentation :** repo `Aegis-AI-Agent-Crew`, fichier [`src/crew.py`](https://github.com/Aegis-AI-Organizations/Aegis-AI-Agent-Crew).
- **Process :** `Process.sequential` — les tâches s'enchaînent dans un ordre fixe, chaque
  sortie alimentant la suivante via le mécanisme `context`.

> **Justification du choix :** le workflow Aegis est séquentiel (planifier → guider →
> exécuter → rapporter). CrewAI respecte au mieux ces étapes avec une syntaxe claire et
> lisible, et une excellente gestion des rôles.

## 2. Benchmark comparatif

| Framework | Type | Points forts | Points faibles |
|-----------|------|--------------|----------------|
| **CrewAI** ✅ | Role-based | Processus métier clairs, facile à scripter, excellente gestion des rôles | Moins flexible pour des boucles complexes/infinies |
| AutoGen (Microsoft) | Conversational | Conversation libre entre agents, idéal pour problèmes non structurés | Difficile à contrôler (risque de boucles infinies coûteuses) |
| LangGraph | State Machine | Contrôle absolu sur le flux de données et les cycles, idéal systèmes critiques | Courbe d'apprentissage élevée, code verbeux |
| Semantic Kernel | Integration | Très bonne intégration entreprise & connecteurs existants | Plus rigide pour une orchestration "créative" |

## 3. Architecture du Crew

- **Agents (3) :** Planner, Guider, Executor — instanciés dans [`src/agents.py`].
- **Tasks (4) :** planning → guider → execution → report — définies dans [`src/tasks.py`].
- **Process :** séquentiel, `verbose=True`.
- **Délégation :** activée uniquement pour le Guider (`allow_delegation=True`) ;
  désactivée pour Planner et Executor.
- **Tools :** rattachés au seul Executor (cf. [executor-deepseek-coder-v2.md](executor-deepseek-coder-v2.md)).

```python
# src/crew.py (extrait)
Crew(
    agents=[planner, guider, executor],
    tasks=[planning_task, guider_task, execution_task, report_task],
    process=Process.sequential,
    verbose=True,
)
```

> À noter : la **4ᵉ tâche (report)** est assignée au **Guider**, pas à l'Executor — c'est
> WhiteRabbitNeo qui compile le rapport pentest final.

## 4. Configuration des modèles (LLM routing)

Chaque agent reçoit son LLM via `get_llm_for_role(role_prefix)` dans [`src/config.py`].
Les rôles sont configurés par variables d'environnement (`.env`) :

| Prefix | Modèle (défaut) | Provider | API base (défaut) |
|--------|-----------------|----------|-------------------|
| `PLANNER` | `llama3.1:8b` | `ollama` | `http://localhost:11434` |
| `GUIDER` | `whiterabbitneo` | `ollama` | `http://localhost:11434` |
| `EXECUTOR` | `deepseek-coder-v2` | `ollama` | `http://localhost:11434` |

- **Provider `ollama`** → modèle formaté `ollama/<model>`, pas de clé API.
- **Provider OpenAI-compatible** → `openai/<model>` + `api_base` + `api_key` (ex. OpenRouter,
  Together, gateway interne). Permet de basculer du local au remote sans changer le code.

## 5. Dépendances

```text
crewai>=0.28.0
crewai-tools>=0.2.0
langchain-openai>=0.1.0
python-dotenv>=1.0.0
requests>=2.31.0
```

## 6. Entrée / Sortie

- **Entrée :** `TARGET_INFRASTRUCTURE` (métadonnées de la cible : IP, services, ports).
  Ex. `"Target IP: 10.0.5.21, Services: [Web App (80/TCP), PostgreSQL (5432/TCP), SSH (22/TCP)]"`.
- **Sortie :** un rapport markdown sauvegardé dans `security_report_findings.md`.

## 7. Intégration dans Aegis

- Le Crew constitue le **layer agent IA**. Dans l'architecture cible, il est déclenché par
  l'orchestration (Temporal / Brain) sur une cible déployée en sandbox K8s, et produit le
  rapport de vulnérabilités + remédiations.
- ⚠️ **À CONFIRMER** : point d'intégration exact Crew ↔ Brain (appel direct, queue, gRPC…).

## 8. État & limites

- **Statut :** base de travail (`README` : *"En cours de construction"*). À consolider sur
  deux axes : **les prompts** (actuellement basiques, générés par IA — à aligner sur le
  workflow IA réel) et **les tools** (exemples seulement, à approfondir).
- **Limite du framework :** moins adapté si le workflow devient non-linéaire (boucles de
  re-test conditionnelles, retours arrière complexes).
