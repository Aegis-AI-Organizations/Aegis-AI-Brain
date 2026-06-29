# Model Card — Guider · WhiteRabbitNeo

> **Agent 2 du Crew (Guider)** — le cerveau offensif. Modélise les vulnérabilités, propose
> les vecteurs d'exploitation/payloads, dirige l'Executor, et compile le rapport final.

---

## 1. Vue d'ensemble

- **Modèle :** WhiteRabbitNeo
- **Agent CrewAI :** `Guider` — rôle *"Cybersecurity Pentesting Guider and Risk Assessor"*
- **Tag déployé :** `whiterabbitneo` (Ollama, cf. `.env.example`)
- **Mission :** pour chaque composant ciblé, faire une évaluation de risque, identifier les
  vulnérabilités potentielles (injection, exposition de ports, dépendances…) et écrire des
  instructions de test précises pour l'Executor. **Rédige aussi le rapport final.**
- **Délégation :** activée (`allow_delegation=True`) — seul agent autorisé à déléguer.

> **Pourquoi ce choix (benchmark) :** les modèles classiques (GPT, Claude, Gemini) ont des
> **guardrails** qui les empêchent de faire du pentest. WhiteRabbitNeo **lève cette
> barrière** : nativement non-censuré pour l'offensive, expert en payloads, conçu **par et
> pour des hackers éthiques**, et **auto-hébergeable**.

## 2. Informations générales

| Champ | Valeur |
|-------|--------|
| Nom | WhiteRabbitNeo |
| Spécialité | Cybersécurité **offensive** / pentest (DevSecOps) |
| Type | LLM fine-tuné spécialisé sécurité, "uncensored" pour l'usage offensif |
| Modèle de base | ⚠️ Dépend de la version (familles Llama / Qwen selon la release) — **À CONFIRMER** |
| Taille | ⚠️ À CONFIRMER (plusieurs tailles existent : 7B / 13B / 33B / 70B selon version) |
| Licence | ⚠️ À CONFIRMER (selon version/base ; usage restreint à la sécurité éthique) |
| Hébergement Aegis | Local via **Ollama** |

> ⚠️ Le tag Ollama `whiterabbitneo` ne fige ni la version ni la taille : **à préciser** selon
> ce qui est réellement pull côté serveur (`ollama list`).

## 3. Architecture du modèle

- **Approche :** modèle généraliste open-weights **fine-tuné** sur des datasets orientés
  sécurité offensive (exploits, payloads, threat-hunting), avec **réduction des refus**
  (alignement "uncensored" pour le pentest).
- ⚠️ **À CONFIRMER** : base exacte + méthode de fine-tuning de la version déployée.

## 4. Spécifications techniques

| Spec | Valeur |
|------|--------|
| Context window | Dépend de la base : ~4k (Llama 2) → 32k+ (Qwen 2.5) — voir §5.A |
| Paramètres | 7B / 13B / 33B selon la version retenue — voir §5.A |
| Runtime d'inférence | Ollama (local) ; bascule OpenAI-compatible possible |
| Quantization | Q4_K_M (défaut) · Q8_0 · fp16 — voir §5.B |
| Hardware | de ~6 GB VRAM (7B Q4) à ~40 GB (70B Q4) — voir §5.A |
| Format de poids | GGUF (via Ollama) |

## 5. Options de déploiement (à arbitrer plus tard)

WhiteRabbitNeo existe en **plusieurs releases** (bases et tailles différentes) : le choix est
laissé ouvert. ⚠️ **Vérifier la disponibilité réelle** sur HuggingFace (`WhiteRabbitNeo/…`)
ou Ollama — le tag générique `whiterabbitneo` ne pointe pas vers un modèle officiel unique.

### A. Version / base / taille (exemples représentatifs)
| Release (exemple) | Base | Taille | Context approx. | VRAM approx. (Q4) |
|-------------------|------|--------|-----------------|-------------------|
| WhiteRabbitNeo-7B / V3 | Qwen 2.5 Coder | 7B | ~32k | ~6 GB |
| WhiteRabbitNeo-13B-v1 | Llama 2 | 13B | ~4k | ~9 GB |
| WhiteRabbitNeo-33B-v1 | DeepSeek-Coder 33B | 33B | ~16k | ~20 GB |
| (variantes 70B selon release) | Llama 3.x | 70B | ~128k | ~40 GB |

> Les versions évoluent vite — **à valider** au moment du déploiement. Privilégier une base
> récente (Qwen 2.5 Coder / Llama 3.x) pour un meilleur context window et de meilleures perfs.

### B. Quantization
| Suffixe | Précision | Compromis |
|---------|-----------|-----------|
| **`q4_K_M`** | 4-bit | Meilleur ratio taille/qualité (**défaut**) |
| `q8_0` | 8-bit | Qualité ≈ fp16, ~2× la VRAM |
| `fp16` | 16-bit | Qualité maximale |

### C. Mode d'hébergement
| Mode | Stack | `PROVIDER` | Note |
|------|-------|-----------|------|
| **Local** | **Ollama** | `ollama` | Souveraineté (**défaut**). ⚠️ tag souvent **absent de la lib officielle** → importer un GGUF HuggingFace via un `Modelfile` |
| Self-host scalable | vLLM / TGI | `openai_compatible` | Charger les poids HF directement |
| Cloud (si dispo) | endpoint OpenAI-compatible | `openai_compatible` | Vérifier qu'un provider héberge la version voulue |

> ⚠️ **Action déploiement** : comme `whiterabbitneo` n'est pas garanti dans la librairie
> Ollama par défaut, prévoir l'import du GGUF (Modelfile) ou un pull communautaire, puis
> figer le tag exact via `ollama list`.

## 6. Données d'entraînement

- **Nature :** corpus de cybersécurité offensive — write-ups, exploits, payloads, analyses
  de vulnérabilités, threat intelligence.
- ⚠️ **À CONFIRMER** : sources/volume exacts (dépend de la version WhiteRabbitNeo).

## 7. Fine-tuning

- **Le modèle EST déjà un fine-tune** spécialisé sécurité offensive (c'est tout l'intérêt vs
  un LLM généraliste).
- **Dans Aegis :** utilisé **tel quel**, spécialisé par prompt (role/goal/backstory CrewAI).
- **Prompt actuel :** basique — **à améliorer** et aligner sur le workflow IA réel.
- ⚠️ **À CONFIRMER** : méthode/dataset du fine-tune upstream.

## 8. Entrées / Sorties

**Entrée** — plan de test produit par le Planner (passé via `context`).

**Sortie attendue** (`expected_output` de la guider task) :
```text
Une liste d'évaluation de risque complète :
1. Failles potentielles par composant
2. Directions de test / idées de payloads précises (endpoints, paramètres à vérifier)
3. Instructions pour l'agent Executor afin de valider ces risques
```

**Rapport final** (`report task`, aussi assignée au Guider) :
```text
Rapport pentest exécutif markdown : executive summary, table des findings notés
(High/Medium/Low), détail technique par vuln (evidence/logs), guide de remédiation.
```

## 9. Intégration dans Aegis

- **Agent :** `create_guider_agent()` ([`src/agents.py`]).
- **Tâches :** `create_guider_task()` (2ᵉ) **et** `create_report_task()` (4ᵉ).
- **En amont :** consomme la sortie du Planner. **En aval :** dirige l'Executor.
- **LLM injecté via :** `get_guider_llm()` → `get_llm_for_role("GUIDER")`.

## 10. Évaluation & métriques

- ⚠️ À COMPLÉTER (qualité/pertinence des vecteurs proposés, taux de faux positifs).

## 11. Limites, biais & risques

- ⚠️ **Modèle offensif non-censuré** → **usage strictement encadré** : cibles autorisées /
  sandbox uniquement. Risque légal/éthique si mal utilisé.
- Peut **halluciner** des vulnérabilités plausibles mais inexistantes → la validation par
  l'Executor (tools réels) est essentielle.
- Garde-fous & traçabilité (scope, logs, sandbox K8s) : ⚠️ À CONFIRMER côté infra.

## 12. Usage & exemples

```bash
# Pré-requis : Ollama avec le modèle (vérifier le tag/version réellement dispo)
ollama pull whiterabbitneo
ollama list   # confirmer la taille/quantization

# .env
GUIDER_PROVIDER=ollama
GUIDER_MODEL=whiterabbitneo
GUIDER_API_BASE=http://localhost:11434
```
