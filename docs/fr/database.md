# 🗄️ Architecture de la Base de Données & Modèles

Le Aegis AI Brain utilise **SQLAlchemy 2.0** avec le modèle moderne `DeclarativeBase` pour interagir avec la base de données PostgreSQL. Cette couche est conçue pour être strictement compatible avec le schéma SQL géré par l'infrastructure tout en fournissant une interface Python typée et sécurisée.

## 🏗️ Modèles Principaux

Tous les modèles sont situés dans `src/models/` et héritent de `Base`.

### 🏢 Entreprises & Multi-Tenancy
- **`Company`** : Représente une organisation au sein d'Aegis.
  - Champs : `name`, `logo_url`, `is_active`.
  - Relations :
    - `owner` : Une relation un-à-un avec l'utilisateur (`User`) qui possède l'entreprise.
    - `members` : Une relation un-à-plusieurs avec toutes les entités `User` appartenant à l'entreprise.

### 👤 Utilisateurs & Rôles
- **`User`** : Entité logicielle de base pour l'authentification.
  - Champs : `email`, `password_hash`, `role` (Enum), `is_active`.
  - Rôles : `superadmin`, `owner`, `operator`, `viewer`.
  - Relations :
    - `company` : L'entreprise à laquelle l'utilisateur appartient.
    - `refresh_tokens` : Sessions actives pour cet utilisateur.

### 🔐 Authentification & Suivi de Session
- **`RefreshToken`** : Utilisé pour la gestion des sessions de type OIDC et la révocation.
  - Champs : `token_hash`, `expires_at`, `revoked`.
  - Logique : Révoqué automatiquement si l'utilisateur est supprimé ou si le jeton expire.

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
