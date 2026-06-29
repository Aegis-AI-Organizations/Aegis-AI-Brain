# Model Card — Planner · Llama 3.1

> **Agent 1 du Crew (Planner)** — le « cerveau » de planification. Décompose la cible et
> produit un plan de test structuré qui pilote tout le reste du workflow.

---

## 1. Vue d'ensemble

- **Modèle :** Llama 3.1 (Meta)
- **Agent CrewAI :** `Planner` — rôle *"Target Analysis and Task Planner"*
- **Tag déployé :** `llama3.1:8b` (Ollama, cf. `.env.example`)
- **Mission :** analyser les métadonnées d'infrastructure cible, identifier les composants
  logiques / ports exposés / configs probables, et formuler un plan de test séquentiel.
- **Délégation :** désactivée (`allow_delegation=False`).

> **Pourquoi ce choix (benchmark) :** modèle **open-weights** → souveraineté totale des
> données, **auto-hébergeable** sur nos serveurs, fenêtre de **128k tokens**, très bonnes
> performances avec une taille ajustable.

## 2. Informations générales

| Champ | Valeur |
|-------|--------|
| Nom | Llama 3.1 |
| Développeur | **Meta** |
| Licence | Llama 3.1 Community License (open-weights) |
| Type | LLM généraliste, decoder-only (transformer) |
| Tailles disponibles | 8B / 70B / 405B |
| **Taille retenue** | **8B** (`llama3.1:8b`) — ⚠️ à ajuster selon GPU dispo |
| Fenêtre de contexte | 128k tokens |
| Multilingue | Oui (anglais, français, allemand, italien, portugais, espagnol, hindi, thaï) |
| Hébergement Aegis | Local via **Ollama** (`http://localhost:11434`) |

## 3. Architecture du modèle

- **Type :** transformer decoder-only, attention GQA (Grouped-Query Attention).
- **Pré-entraînement :** corpus massif multilingue (Meta).
- **Variantes :** `Instruct` (alignée pour le suivi d'instructions) — c'est la variante
  attendue pour un agent CrewAI.
- **Quantization :** par défaut Q4_K_M sur le 8B ; alternatives (Q8_0, fp16) détaillées en §5.

## 4. Spécifications techniques

| Spec | Valeur |
|------|--------|
| Context window | 128k tokens |
| Paramètres (retenu) | ~8 milliards |
| Runtime d'inférence | Ollama (local) ; bascule OpenAI-compatible possible |
| Quantization | Q4_K_M (défaut) · Q8_0 · fp16 — voir §5 |
| Hardware | 8B : GPU grand public OK ; 70B/405B : infra GPU lourde |
| Format de poids | GGUF (via Ollama) |

> Le benchmark note que la version **405B** nécessite une grosse infrastructure GPU — d'où
> le choix d'une taille raisonnable (8B) pour le planificateur.

## 5. Options de déploiement (à arbitrer plus tard)

Rien n'est figé : ces axes restent ouverts pour ajuster qualité ↔ coût selon l'infra.
Le défaut actuel est en **gras**.

### A. Taille du modèle
| Tag Ollama | Params | VRAM approx. (Q4) | Quand l'utiliser |
|------------|--------|-------------------|------------------|
| **`llama3.1:8b`** | 8B | ~6 GB | Léger/rapide, raisonnement simple (**défaut**) |
| `llama3.1:70b` | 70B | ~40–48 GB | Plans plus fins sur infra complexe (1 GPU 48 GB / multi-GPU) |
| `llama3.1:405b` | 405B | ~230 GB (multi-GPU) | Qualité max, infra lourde |

### B. Quantization
| Suffixe de tag | Précision | Compromis |
|----------------|-----------|-----------|
| **`-q4_K_M`** | 4-bit | Meilleur ratio taille/qualité (**défaut Ollama**) |
| `-q8_0` | 8-bit | Qualité ≈ fp16, ~2× la VRAM du Q4 |
| `-fp16` | 16-bit | Qualité maximale, VRAM la plus élevée |

### C. Mode d'hébergement
| Mode | Stack | `PROVIDER` | Quand |
|------|-------|-----------|-------|
| **Local** | **Ollama** | `ollama` | Souveraineté des données, dev (**défaut**) |
| Self-host scalable | vLLM / TGI | `openai_compatible` | Prod, fort débit, batching |
| Cloud OpenAI-compatible | Together / OpenRouter / Fireworks / Bedrock | `openai_compatible` | Pas d'infra GPU à gérer |

> Le routing du Crew (`get_llm_for_role`) bascule de `ollama/<model>` à `openai/<model>` selon
> `PLANNER_PROVIDER` — donc passer du local au cloud ne change **pas** le code, juste le `.env`.
>
> ⚠️ Une fois la combinaison choisie, figer la valeur réellement déployée via `ollama list`.

## 6. Données d'entraînement

- **Pré-entraînement :** corpus public Meta (cutoff Llama 3.1 ≈ décembre 2023).
- **Détail :** non public dans le détail (poids ouverts, données non intégralement publiées).

## 7. Fine-tuning

- **Dans Aegis :** ⚠️ pas de fine-tuning custom à ce stade — le modèle est utilisé **tel
  quel** (variante Instruct) et spécialisé par **prompt engineering** (role/goal/backstory
  CrewAI).
- **Prompt actuel :** basique (généré par IA) — **à améliorer** et aligner sur le workflow
  IA réel (cf. note de l'équipe).
- **Piste future :** fine-tuning LoRA possible si besoin de spécialiser la planification.

## 8. Entrées / Sorties

**Entrée** — `TARGET_INFRASTRUCTURE` (texte) :
```text
Company: Aegis, Target IP: 10.0.5.21,
Services: [Web App (80/TCP), PostgreSQL (5432/TCP), SSH (22/TCP)]
```

**Sortie attendue** (`expected_output` de la planning task) :
```text
Un plan de test de sécurité en markdown :
1. Décomposition architecturale du périmètre
2. Étapes de validation séquentielles (Recon, checks par service, SQLi, config…)
3. Liste des assets critiques
```

## 9. Intégration dans Aegis

- **Agent :** `create_planner_agent()` ([`src/agents.py`]).
- **Tâche :** `create_planning_task()` — 1ʳᵉ tâche du process séquentiel.
- **En aval :** sa sortie sert de `context` au Guider (WhiteRabbitNeo).
- **LLM injecté via :** `get_planner_llm()` → `get_llm_for_role("PLANNER")`.

## 10. Évaluation & métriques

- ⚠️ À COMPLÉTER (pas de benchmark interne formalisé pour la qualité des plans).
- Réf. publiques : Llama 3.1 8B Instruct = bon rapport perf/coût pour du raisonnement léger.

## 11. Limites, biais & risques

- **8B** : raisonnement plus limité que 70B/405B — peut produire des plans incomplets sur des
  infra complexes (monter en taille si nécessaire).
- Modèle **généraliste** (non spécialisé cyber) — d'où la séparation avec l'agent offensif.
- Garde-fous Meta : peut être plus prudent que WhiteRabbitNeo sur des formulations offensives.

## 12. Usage & exemples

```bash
# Pré-requis : Ollama avec le modèle
ollama pull llama3.1:8b

# .env
PLANNER_PROVIDER=ollama
PLANNER_MODEL=llama3.1:8b
PLANNER_API_BASE=http://localhost:11434
```
