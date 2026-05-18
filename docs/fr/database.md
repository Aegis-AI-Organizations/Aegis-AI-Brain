# 🗄️ Architecture de la Base de Données & Modèles

Le Aegis AI Brain utilise **SQLAlchemy 2.0** avec le modèle moderne `DeclarativeBase` pour interagir avec la base de données PostgreSQL. Cette couche est conçue pour être strictement compatible avec le schéma SQL géré par l'infrastructure tout en fournissant une interface Python typée et sécurisée.

## 🏗️ Modèles Principaux

Tous les modèles sont situés dans `src/models/` et héritent de `Base`.

### 🏢 Entreprises & Multi-Tenancy
- **`Company`** : Représente une organisation au sein d'Aegis.
  - Champs : `name`, `logo_url`, `is_active`, `deployment_token`.
  - **`deployment_token`** : Hash SHA-256 du token de déploiement brut `ag_` utilisé par les agents externes. Le token brut est retourné une seule fois pendant l'activation du owner ou une rotation manuelle et n'est jamais persisté.
  - Relations :
    - `owner` : Une relation un-à-un avec l'utilisateur (`User`) qui possède l'entreprise.
    - `members` : Une relation un-à-plusieurs avec toutes les entités `User` appartenant à l'entreprise.
    - `agents` : Agents persistants déployés pour cette entreprise.

### 📡 Agents & Statut Runtime
- **`Agent`** : Représente un agent Aegis déployé et rattaché à une entreprise.
  - Champs : `company_id`, `name`, `token_hash`, `status`, `last_seen`, `created_at`.
  - `token_hash` stocke le hash du secret opérationnel de l'agent. Le secret en clair n'est retourné que pendant l'enregistrement de l'agent.
  - `last_seen` est mis à jour par les appels de statut/heartbeat et sert à calculer les agents actifs ou inactifs pour le dashboard.

### 👤 Utilisateurs & Rôles
- **`User`** : Entité logicielle de base pour l'authentification.
  - Champs : `email`, `password_hash`, `role` (Enum), `is_active`, `name`, `avatar_url`.
  - **Rôles Synchronisés (RBAC)** :
    - `superadmin`, `admin`, `billing_aegis`, `technicien`, `support`, `commercial`, `billing_client`, `operateur`, `viewer`.
  - Relations :
    - `company` : L'entreprise à laquelle l'utilisateur appartient.
    - `refresh_tokens` : Sessions actives pour cet utilisateur.

### 🔐 Authentification & Suivi de Session
- **`RefreshToken`** : Utilisé pour la gestion des sessions de type OIDC et la révocation.
  - Champs : `token_hash`, `expires_at`, `revoked`.
  - Logique : La révocation est vérifiée lors de l'utilisation ; le jeton est considéré invalide si le drapeau `revoked` est vrai ou si `expires_at` est dans le passé.

### 🎯 Pentest & Vulnérabilités
- **`Scan`** : Représente une session de test d'intrusion.
  - Champs : `status`, `report_pdf`, `started_at`, `completed_at`.
- **`Vulnerability`** : Découvertes identifiées lors d'un scan.
  - Champs : `vuln_type`, `severity`.
- **`Evidence`** : Preuve d'exploitation pour une vulnérabilité spécifique.
  - Champs : `payload_used`, `loot_data` (JSONB).

## 🛠️ Détails d'Implémentation

### Support JSONB
Pour les fonctionnalités spécifiques à PostgreSQL comme le `JSONB` (utilisé dans `Evidence.loot_data`), nous utilisons `with_variant` pour garantir que les modèles peuvent toujours être testés à l'aide de bases de données SQLite légères dans les environnements de CI/CD.

```python
loot_data = mapped_column(JSON().with_variant(JSONB, "postgresql"))
```

### Sécurité des Mots de Passe
Les mots de passe ne sont jamais stockés en clair. Nous utilisons l'algorithme `bcrypt` via l'utilitaire `auth_utils`.
- **Hachage** : `hash_password(password)`
- **Vérification** : `verify_password(password, hashed_password)`

## 🧪 Tests & Validation
La couche de base de données est validée à l'aide de `pytest` avec un objectif de couverture de 100% pour les mappages de schéma critiques. Nous utilisons SQLite en mémoire pour les tests unitaires rapides et PostgreSQL pour les tests d'intégration dans l'environnement MVP.
