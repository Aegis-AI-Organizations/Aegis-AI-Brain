# 🗄️ Database Architecture & Models

The Aegis AI Brain uses **SQLAlchemy 2.0** with the modern `DeclarativeBase` pattern to interact with the PostgreSQL database. This layer is designed to be strictly compatible with the infrastructure-managed SQL schema while providing a type-safe Pythonic interface.

## 🏗️ Core Models

All models are located in `src/models/` and inherit from `Base`.

### 🏢 Companies & Multi-Tenancy
- **`Company`**: Represents an organization within Aegis.
  - Fields: `name`, `logo_url`, `is_active`, `deployment_token`.
  - **`deployment_token`**: Unique 32-character hex string prefixed with `ag_` used by external probes.
  - Relationships:
    - `owner`: A One-to-One relationship to the `User` who owns the company.
    - `members`: A One-to-Many relationship to all `User` entities belonging to the company.

### 👤 Users & Roles
- **`User`**: Core authentication entity.
  - Fields: `email`, `password_hash`, `role` (Enum), `is_active`, `name`, `avatar_url`.
  - **Synchronized Roles (RBAC)**:
    - `superadmin`, `admin`, `billing_aegis`, `technicien`, `support`, `commercial`, `billing_client`, `operateur`, `viewer`.
  - Relationships:
    - `company`: The company the user belongs to.
    - `refresh_tokens`: Active sessions for this user.

### 🔐 Authentication & Session Tracking
- **`RefreshToken`**: Used for OIDC-like session management and revocation.
  - Fields: `token_hash`, `expires_at`, `revoked`.
  - Logic: Revocation is checked upon use; the token is considered invalid if the `revoked` flag is true or if `expires_at` is in the past.

### 🎯 Pentest & Vulnerabilities
- **`Scan`**: Represents a penetration testing session.
  - Fields: `status`, `report_pdf`, `started_at`, `completed_at`.
- **`Vulnerability`**: Findings discovered during a scan.
  - Fields: `vuln_type`, `severity`.
- **`Evidence`**: Proof of exploitation for a specific vulnerability.
  - Fields: `payload_used`, `loot_data` (JSONB).

## 🛠️ Implementation Details

### JSONB Support
For PostgreSQL-specific features like `JSONB` (used in `Evidence.loot_data`), we use `with_variant` to ensure the models can still be tested using lightweight SQLite databases in CI/CD environments.

```python
loot_data = mapped_column(JSON().with_variant(JSONB, "postgresql"))
```

### Password Security
Passwords are never stored in plain text. We use the `bcrypt` algorithm via the `auth_utils` utility.
- **Hashing**: `hash_password(password)`
- **Verification**: `verify_password(password, hashed_password)`

## 🧪 Testing & Validation
The database layer is validated using `pytest` with a 100% coverage goal for critical schema mappings. We use in-memory SQLite for rapid unit testing and PostgreSQL for integration testing in the MVP environment.
