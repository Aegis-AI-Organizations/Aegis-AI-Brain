# Model Card — Executor · DeepSeek-Coder-V2

> **Agent 3 du Crew (Executor)** — l'ingénieur. Exécute les tools de test, confirme les
> failles à partir des sorties, et écrit les correctifs de code/configuration (IaC, YAML,
> Dockerfile, etc.) pour combler les vulnérabilités.

---

## 1. Vue d'ensemble

- **Modèle :** DeepSeek-Coder-V2 (DeepSeek AI)
- **Agent CrewAI :** `Executor` — rôle *"Security Test Executor and Remediation Engineer"*
- **Tag déployé :** `deepseek-coder-v2` (Ollama, cf. `.env.example`)
- **Mission :** lancer les tools (vérif d'endpoints/ports, scan de configs), analyser les
  sorties pour confirmer les vulnérabilités, puis produire des **patches prêts à appliquer**
  (code, Dockerfile, config Nginx, patch SQL…).
- **Outils :** **seul agent équipé de tools** (cf. §7).
- **Délégation :** désactivée (`allow_delegation=False`).

> **Pourquoi ce choix (benchmark) :** modèle **très puissant et souple**, rivalise avec
> GPT-4 Turbo sur le code, supporte **300+ langages**, et a une **excellente compréhension
> des fichiers de configuration** (Terraform, K8s) — idéal pour générer de la remédiation IaC.

## 2. Informations générales

| Champ | Valeur |
|-------|--------|
| Nom | DeepSeek-Coder-V2 |
| Développeur | **DeepSeek AI** |
| Type | LLM de code **Mixture-of-Experts (MoE)** |
| Variantes | Lite (16B total / ~2.4B actifs) · Full (236B total / ~21B actifs) |
| **Variante retenue** | `deepseek-coder-v2` ≈ **Lite 16B** par défaut ; Full 236B en option — voir §5.A |
| Langages supportés | 300+ langages de programmation |
| Fenêtre de contexte | jusqu'à 128k tokens |
| Licence | DeepSeek License (open-weights) |
| Hébergement Aegis | Local via **Ollama** |

## 3. Architecture du modèle

- **Type :** transformer **Mixture-of-Experts** — seuls quelques experts sont activés par
  token → bon ratio performance/coût d'inférence.
- **Spécialité :** génération et compréhension de code + fichiers de configuration / IaC.
- **Variante & quantization :** Lite 16B (défaut) ou Full 236B ; quantization Q4/Q8/fp16 — détaillé en §5.

## 4. Spécifications techniques

| Spec | Valeur |
|------|--------|
| Context window | jusqu'à 128k tokens |
| Paramètres | Lite : 16B total (~2.4B actifs) · Full : 236B total (~21B actifs) |
| Runtime d'inférence | Ollama (local) ; bascule OpenAI-compatible possible |
| Quantization | Q4_K_M (défaut) · Q8_0 · fp16 — voir §5.B |
| Hardware | Lite : GPU raisonnable ; Full : infra GPU lourde |
| Format de poids | GGUF (via Ollama) |

## 5. Options de déploiement (à arbitrer plus tard)

Le défaut actuel est en **gras** ; les autres axes restent ouverts.

### A. Variante (MoE)
| Tag Ollama | Total / actifs | Context | VRAM approx. (Q4) | Quand |
|------------|----------------|---------|-------------------|-------|
| **`deepseek-coder-v2:16b`** (Lite) | 16B / ~2.4B | 128k | ~10–12 GB | Rapide, GPU raisonnable (**défaut**) |
| `deepseek-coder-v2:236b` | 236B / ~21B | 128k | ~130+ GB (multi-GPU) | Qualité max, infra lourde |

### B. Quantization
| Suffixe | Précision | Compromis |
|---------|-----------|-----------|
| **`q4_K_M`** | 4-bit | Meilleur ratio taille/qualité (**défaut**) |
| `q8_0` | 8-bit | Qualité ≈ fp16, ~2× la VRAM |
| `fp16` | 16-bit | Qualité maximale |

### C. Mode d'hébergement
| Mode | Stack | `PROVIDER` | Quand |
|------|-------|-----------|-------|
| **Local** | **Ollama** | `ollama` | Souveraineté, dev (**défaut**) |
| Self-host scalable | vLLM / TGI | `openai_compatible` | Prod, fort débit |
| Cloud OpenAI-compatible | DeepSeek API / Together / OpenRouter / Fireworks | `openai_compatible` | Pas d'infra GPU à gérer |

> ⚠️ Une fois la combinaison choisie, figer la valeur réellement déployée via `ollama list`.

## 6. Données d'entraînement

- **Nature :** vaste corpus de code (dépôts publics) + données générales, optimisé pour la
  programmation et le raisonnement mathématique.
- ⚠️ Détails complets non publics ; cf. publications DeepSeek-Coder-V2.

## 7. Fine-tuning

- **Dans Aegis :** utilisé **tel quel** (modèle déjà spécialisé code), piloté par prompt
  (role/goal/backstory CrewAI) + **tools**.
- **Prompt actuel :** basique — **à améliorer** et aligner sur le workflow IA réel.
- **Piste future :** fine-tuning sur paires *vuln → patch* / corpus IaC interne si besoin.

## 8. Tools de l'agent

Définis dans [`src/tools.py`] et attachés au seul Executor :

| Tool | Fonction |
|------|----------|
| `Verify Network Service Endpoint` | Ping un endpoint/port cible, renvoie le statut HTTP + header `Server` (ou test TCP simulé pour les autres ports). |
| `Scan Exposed File Template` | Récupère des templates de config (`nginx.conf`, `Dockerfile`, `pg_hba.conf`) à analyser/corriger. |

> ⚠️ Ces tools sont des **exemples/mocks** (réponses simulées) — à approfondir et brancher
> sur de vrais scanners/checks (note de l'équipe : *"il faudra qu'on creuse plus le sujet"*).

## 9. Entrées / Sorties

**Entrée** — instructions de test & risques produits par le Guider (via `context`).

**Sortie attendue** (`expected_output` de l'execution task) :
```text
Un log de validation & remédiation :
1. Résultats d'exécution des tools et findings
2. Vulnérabilités identifiées + explication technique
3. Blocs de code / modifications de config (patches) prêts à appliquer
```

## 10. Intégration dans Aegis

- **Agent :** `create_executor_agent(tools)` ([`src/agents.py`]).
- **Tâche :** `create_execution_task()` (3ᵉ du process).
- **En amont :** consomme la sortie du Guider. **En aval :** ses résultats alimentent le
  rapport final (rédigé par le Guider).
- **LLM injecté via :** `get_executor_llm()` → `get_llm_for_role("EXECUTOR")`.

## 11. Évaluation & métriques

- ⚠️ À COMPLÉTER (taux de patches valides, % de findings correctement remédiés, régressions).
- Réf. publiques : DeepSeek-Coder-V2 ≈ niveau GPT-4 Turbo sur les benchmarks de code.

## 12. Limites, biais & risques

- Patches générés à **valider humainement** avant prod (risque de correctif incomplet /
  régression / faux sentiment de sécurité).
- Qualité dépendante de la variante déployée (Lite < Full sur les cas complexes).
- Tools actuellement mockés → les "validations" ne reflètent pas encore la réalité.

## 13. Usage & exemples

```bash
# Pré-requis : Ollama avec le modèle
ollama pull deepseek-coder-v2
ollama list   # confirmer variante/quantization

# .env
EXECUTOR_PROVIDER=ollama
EXECUTOR_MODEL=deepseek-coder-v2
EXECUTOR_API_BASE=http://localhost:11434
```
