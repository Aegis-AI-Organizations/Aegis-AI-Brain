# Graph Report - pentest-validation-stabilization  (2026-09-19)

## Corpus Check
- 105 files · ~39,865 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1269 nodes · 1983 edges · 98 communities (83 shown, 15 thin omitted)
- Extraction: 83% EXTRACTED · 17% INFERRED · 0% AMBIGUOUS · INFERRED: 336 edges (avg confidence: 0.71)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `2f7b54ea`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_GraphDrivenPentestWorkflow|GraphDrivenPentestWorkflow]]
- [[_COMMUNITY_test_email_utils.py|test_email_utils.py]]
- [[_COMMUNITY_BillingService|BillingService]]
- [[_COMMUNITY_properties|properties]]
- [[_COMMUNITY_User|User]]
- [[_COMMUNITY_AuthService|AuthService]]
- [[_COMMUNITY_properties|properties]]
- [[_COMMUNITY_$ref|$ref]]
- [[_COMMUNITY_CompanyService|CompanyService]]
- [[_COMMUNITY_AgentService|AgentService]]
- [[_COMMUNITY_engine.py|engine.py]]
- [[_COMMUNITY_BillingService|BillingService]]
- [[_COMMUNITY_test_auth_service.py|test_auth_service.py]]
- [[_COMMUNITY_get_db_connection|get_db_connection]]
- [[_COMMUNITY_database_seeding.py|database_seeding.py]]
- [[_COMMUNITY_AuthServiceServicer|AuthServiceServicer]]
- [[_COMMUNITY_AuthInterceptor|AuthInterceptor]]
- [[_COMMUNITY_sandbox_topology_validation.py|sandbox_topology_validation.py]]
- [[_COMMUNITY_test_grpc_server.py|test_grpc_server.py]]
- [[_COMMUNITY_Neo4jAttackTargetService|Neo4jAttackTargetService]]
- [[_COMMUNITY_PentestWorkflow|PentestWorkflow]]
- [[_COMMUNITY_object|object]]
- [[_COMMUNITY_test_agent_service.py|test_agent_service.py]]
- [[_COMMUNITY_Base|Base]]
- [[_COMMUNITY_properties|properties]]
- [[_COMMUNITY_AuthService|AuthService]]
- [[_COMMUNITY_db.py|db.py]]
- [[_COMMUNITY_Neo4jSandboxTopologyService|Neo4jSandboxTopologyService]]
- [[_COMMUNITY_hash_password|hash_password]]
- [[_COMMUNITY_properties|properties]]
- [[_COMMUNITY_CompanyServiceServicer|CompanyServiceServicer]]
- [[_COMMUNITY_VulnerabilityService|VulnerabilityService]]
- [[_COMMUNITY_test_models.py|test_models.py]]
- [[_COMMUNITY_properties|properties]]
- [[_COMMUNITY_AgentService|AgentService]]
- [[_COMMUNITY_AgentServiceServicer|AgentServiceServicer]]
- [[_COMMUNITY_ScanService|ScanService]]
- [[_COMMUNITY_ScanServiceServicer|ScanServiceServicer]]
- [[_COMMUNITY_OnboardingInvitation|OnboardingInvitation]]
- [[_COMMUNITY_type|type]]
- [[_COMMUNITY_config.py|config.py]]
- [[_COMMUNITY_update_scan_status|update_scan_status]]
- [[_COMMUNITY_ping_pb2_grpc.py|ping_pb2_grpc.py]]
- [[_COMMUNITY_get_session_factory|get_session_factory]]
- [[_COMMUNITY_🏗️ Core Models|🏗️ Core Models]]
- [[_COMMUNITY_🏗️ Modèles Principaux|🏗️ Modèles Principaux]]
- [[_COMMUNITY_$defs|$defs]]
- [[_COMMUNITY_properties|properties]]
- [[_COMMUNITY_name|name]]
- [[_COMMUNITY_db_activities.py|db_activities.py]]
- [[_COMMUNITY_CompanyService|CompanyService]]
- [[_COMMUNITY_properties|properties]]
- [[_COMMUNITY_Changes Made|Changes Made]]
- [[_COMMUNITY_columns|columns]]
- [[_COMMUNITY_properties|properties]]
- [[_COMMUNITY_properties|properties]]
- [[_COMMUNITY_StatusBroadcaster|StatusBroadcaster]]
- [[_COMMUNITY_test_internal_auth.py|test_internal_auth.py]]
- [[_COMMUNITY_The Aegis AI Brain (Orchestrator)|The Aegis AI Brain (Orchestrator)]]
- [[_COMMUNITY_Le Brain Aegis AI (Orchestrateur)|Le Brain Aegis AI (Orchestrateur)]]
- [[_COMMUNITY_externalMock|externalMock]]
- [[_COMMUNITY_service|service]]
- [[_COMMUNITY_update_scan_debug_bundle|update_scan_debug_bundle]]
- [[_COMMUNITY_download_minio_artifact|download_minio_artifact]]
- [[_COMMUNITY_test_rbac_visibility.py|test_rbac_visibility.py]]
- [[_COMMUNITY_sandbox-topology.schema.json|sandbox-topology.schema.json]]
- [[_COMMUNITY_agent_watcher.py|agent_watcher.py]]
- [[_COMMUNITY_test_search_coverage.py|test_search_coverage.py]]
- [[_COMMUNITY_VulnerabilityServiceServicer|VulnerabilityServiceServicer]]
- [[_COMMUNITY_test_auth_init.py|test_auth_init.py]]
- [[_COMMUNITY_.Logout|.Logout]]
- [[_COMMUNITY_.Refresh|.Refresh]]
- [[_COMMUNITY_container_port|container_port]]
- [[_COMMUNITY_number|number]]
- [[_COMMUNITY_target_port|target_port]]
- [[_COMMUNITY_.SetupPassword|.SetupPassword]]
- [[_COMMUNITY_conftest.py|conftest.py]]
- [[_COMMUNITY_.UpdateEmail|.UpdateEmail]]
- [[_COMMUNITY_llm-payloads|llm-payloads.md]]
- [[_COMMUNITY_databaseName|databaseName]]
- [[_COMMUNITY_aegis-ai-brain|aegis-ai-brain]]
- [[_COMMUNITY_agent_pb2.py|agent_pb2.py]]
- [[_COMMUNITY_auth_pb2.py|auth_pb2.py]]
- [[_COMMUNITY_billing_pb2.py|billing_pb2.py]]

## God Nodes (most connected - your core abstractions)
1. `User` - 52 edges
2. `GraphDrivenPentestWorkflow` - 38 edges
3. `Company` - 35 edges
4. `CompanyService` - 33 edges
5. `AuthService` - 29 edges
6. `OnboardingInvitation` - 22 edges
7. `Neo4jSandboxTopologyService` - 19 edges
8. `PentestWorkflow` - 19 edges
9. `get_db_connection()` - 18 edges
10. `MockContext` - 18 edges

## Surprising Connections (you probably didn't know these)
- `test_update_email_conflict()` --calls--> `User`  [INFERRED]
  tests/test_auth_service_ext.py → src/models/user.py
- `test_update_profile_success()` --calls--> `User`  [INFERRED]
  tests/test_auth_service_ext.py → src/models/user.py
- `test_refresh_success()` --calls--> `User`  [INFERRED]
  tests/test_auth_service.py → src/models/user.py
- `test_list_users_owner_visibility()` --calls--> `User`  [INFERRED]
  tests/test_rbac_visibility.py → src/models/user.py
- `test_build_sandbox_topology_includes_database_schemas()` --calls--> `Neo4jSandboxTopologyService`  [INFERRED]
  tests/test_activities.py → src/services/neo4j_sandbox_topology.py

## Import Cycles
- 2-file cycle: `src/models/onboarding_invitation.py -> src/models/user.py -> src/models/onboarding_invitation.py`
- 2-file cycle: `src/models/agent.py -> src/models/company.py -> src/models/agent.py`
- 2-file cycle: `src/models/company.py -> src/models/user.py -> src/models/company.py`

## Communities (98 total, 15 thin omitted)

### Community 0 - "GraphDrivenPentestWorkflow"
Cohesion: 0.08
Nodes (32): GraphDrivenPentestWorkflow, Exception, failing_update_scan_status(), mock_build_sandbox_topology(), mock_capture_run_targeted_pentest(), mock_create_sandbox(), mock_destroy_sandbox(), mock_download_invalid_topology_artifact() (+24 more)

### Community 1 - "test_email_utils.py"
Cohesion: 0.11
Nodes (30): ABC, create_email_service(), EmailService, _format_from_header(), MailpitEmailService, ProductionEmailService, _build_action_url(), _build_email_parts() (+22 more)

### Community 2 - "BillingService"
Cohesion: 0.07
Nodes (19): AdjustTokensRequest, AdjustTokensResponse, GetBalanceRequest, GetBalanceResponse, GetLedgerRequest, GetLedgerResponse, GetUsageStatsRequest, GetUsageStatsResponse (+11 more)

### Community 3 - "properties"
Cohesion: 0.05
Nodes (44): items, type, items, type, description, items, type, description (+36 more)

### Community 4 - "User"
Cohesion: 0.09
Nodes (19): Company, Company model mapped to the 'companies' table., User, test_company_summary_includes_current_company_metadata(), test_create_company_success(), test_create_user_success(), test_list_companies_success(), test_list_users_includes_all_company_owners() (+11 more)

### Community 5 - "AuthService"
Cohesion: 0.06
Nodes (14): CompanyService, CompanyServiceServicer, CompanyServiceStub, ListAuditLogs retrieves system audit trails (Admin only)., Constructor.          Args:             channel: A grpc.Channel., CompanyService handles registration and administrative management of companies., CompanyService handles registration and administrative management of companies., CreateCompany registers a new company in the system. (+6 more)

### Community 6 - "properties"
Cohesion: 0.07
Nodes (29): type, type, externalRoute, file, additionalProperties, properties, type, additionalProperties (+21 more)

### Community 7 - "$ref"
Cohesion: 0.10
Nodes (15): hash_password(), Verifies a plain-text password against a stored bcrypt hash.      Args:, Hashes a plain-text password using the bcrypt algorithm.      Args:         pass, verify_password(), test_login_db_error(), test_login_inactive_user(), test_login_success(), test_refresh_success() (+7 more)

### Community 8 - "CompanyService"
Cohesion: 0.08
Nodes (17): CreateCompanyRequest, CreateCompanyResponse, ListAuditLogsRequest, ListAuditLogsResponse, ListCompaniesRequest, ListCompaniesResponse, OnboardCompanyRequest, OnboardCompanyResponse (+9 more)

### Community 9 - "AgentService"
Cohesion: 0.07
Nodes (20): AgentService, Onboarding of the Rust agent using a deployment token (ag_...).         Returns, Updates the agent's state (IDLE, UPLOADING, etc.) and last_seen timestamp., Generates a presigned MinIO URL for the agent to upload infrastructure files/log, Validates an operational secret against an agent ID.         Used by the Gateway, InternalAuthService, gRPC service for verifying agent deployment tokens. Caching is handled by the AP, Synchronously verifies an agent token and returns the company_id. (+12 more)

### Community 10 - "engine.py"
Cohesion: 0.21
Nodes (25): FPDF, build_report(), _count_by_severity(), _ensure_space(), _extract_target_image_path(), _extract_target_name(), _format_loot_data(), _normalize_severity() (+17 more)

### Community 11 - "BillingService"
Cohesion: 0.08
Nodes (25): $ref, type, type, type, type, type, items, type (+17 more)

### Community 12 - "test_auth_service.py"
Cohesion: 0.17
Nodes (11): DeclarativeBase, Base, Modern SQLAlchemy declarative base for all models., Evidence, Scan model mapped to the 'scans' table., Vulnerability model mapped to the 'vulnerabilities' table., Evidence model mapped to the 'evidences' table., Scan (+3 more)

### Community 13 - "get_db_connection"
Cohesion: 0.06
Nodes (27): Connection, get_db_connection(), PingService, normalize_persisted_target_image(), ScanService, get_identity(), Securely extracts identity from verified context or gRPC metadata fallback., to_pb_timestamp() (+19 more)

### Community 14 - "database_seeding.py"
Cohesion: 0.08
Nodes (12): BillingService, BillingServiceServicer, BillingServiceStub, BillingService handles token management and consumption history., Constructor.          Args:             channel: A grpc.Channel., BillingService handles token management and consumption history., GetBalance retrieves the current token balance for a company., GetLedger retrieves the history of token transactions for a company. (+4 more)

### Community 15 - "AuthServiceServicer"
Cohesion: 0.14
Nodes (13): StatusBroadcaster, AuthInterceptor, gRPC interceptor for JWT validation and verified identity injection., Decorator to inject identity into the handler.     Supports both async functions, with_identity(), MockHandlerCallDetails, test_auth_interceptor_expired_token(), test_auth_interceptor_invalid_token() (+5 more)

### Community 16 - "AuthInterceptor"
Cohesion: 0.10
Nodes (11): AuthServiceServicer, UpdateProfile updates the authenticated user's profile information., UpdateEmail updates the authenticated user's email address., UpdatePassword updates the authenticated user's password., RemoveAvatar deletes the authenticated user's profile picture., AuthService handles user authentication, session management, and JWT generation., Login authenticates a user and returns an access token and refresh token., Refresh generates a new access token using a valid refresh token. (+3 more)

### Community 17 - "sandbox_topology_validation.py"
Cohesion: 0.24
Nodes (13): Path, _extract_topology(), _format_path(), SandboxTopologyValidationError, _schema(), _schema_path(), validate_sandbox_topology(), validate_sandbox_topology_request() (+5 more)

### Community 18 - "test_grpc_server.py"
Cohesion: 0.18
Nodes (7): PentestWorkflow, Helper to update scan status via activity., Ask the dedicated Deployer worker to create the sandbox., Execute the actual pentest activity on the Worker., Main orchestration workflow that simulates a pentest., Ask the dedicated Deployer worker to destroy the sandbox., Handles cleanup and status update on workflow failure.

### Community 19 - "Neo4jAttackTargetService"
Cohesion: 0.18
Nodes (9): AttackTarget, identify_attack_targets(), Neo4jAttackTargetService, test_identify_attack_targets_falls_back_to_direct_selected_routes(), test_identify_attack_targets_includes_container_image_metadata(), test_identify_attack_targets_omits_agent_id_when_missing(), test_identify_attack_targets_orders_and_normalizes_paths(), test_identify_attack_targets_passes_selected_target_filter() (+1 more)

### Community 20 - "PentestWorkflow"
Cohesion: 0.12
Nodes (16): additionalProperties, type, anyOf, $defs, stringMap, workload, $id, required (+8 more)

### Community 21 - "object"
Cohesion: 0.16
Nodes (9): object, InternalAuthService, InternalAuthServiceServicer, InternalAuthServiceStub, Constructor.          Args:             channel: A grpc.Channel., InternalAuthService handles internal authentication and authorization between se, VerifyToken validates a raw JWT token and returns the associated tenant informat, InternalAuthService handles internal authentication and authorization between se (+1 more)

### Community 22 - "test_agent_service.py"
Cohesion: 0.12
Nodes (17): type, type, properties, type, database_name, databaseName, engine, source_container_id (+9 more)

### Community 23 - "Base"
Cohesion: 0.12
Nodes (5): AuthService, AuthServiceStub, Constructor.          Args:             channel: A grpc.Channel., AuthService handles user authentication, session management, and JWT generation., AuthService handles user authentication, session management, and JWT generation.

### Community 24 - "properties"
Cohesion: 0.19
Nodes (10): serve(), main(), AgentWatcher, Starts the Redis keyspace notification listener., Updates the agent status to OFFLINE in the database., start_agent_watcher(), start_worker(), test_grpc_server_mtls_fails_when_certificate_missing() (+2 more)

### Community 25 - "AuthService"
Cohesion: 0.12
Nodes (16): additionalProperties, properties, type, connection, source, source_name, sourceName, target (+8 more)

### Community 26 - "db.py"
Cohesion: 0.12
Nodes (9): Constructor.          Args:             channel: A grpc.Channel., VulnerabilityService handles retrieval of vulnerability data., GetVulnerabilities returns a list of vulnerabilities for a scan., GetEvidences returns the evidence collected for a specific vulnerability., VulnerabilityService handles retrieval of vulnerability data., VulnerabilityService handles retrieval of vulnerability data., VulnerabilityService, VulnerabilityServiceServicer (+1 more)

### Community 27 - "Neo4jSandboxTopologyService"
Cohesion: 0.22
Nodes (7): build_sandbox_topology(), Neo4jSandboxTopologyService, Any, test_build_sandbox_topology_includes_known_workload_routes(), test_build_sandbox_topology_loads_database_schemas_for_route_selected_containers(), test_build_sandbox_topology_maps_containers_to_deployer_payload(), test_build_sandbox_topology_uses_default_http_port_when_missing()

### Community 28 - "hash_password"
Cohesion: 0.13
Nodes (15): items, type, initContainer, $ref, minLength, type, additionalProperties, properties (+7 more)

### Community 29 - "properties"
Cohesion: 0.14
Nodes (5): AgentService, AgentServiceStub, Constructor.          Args:             channel: A grpc.Channel., Missing associated documentation comment in .proto file., Missing associated documentation comment in .proto file.

### Community 30 - "CompanyServiceServicer"
Cohesion: 0.14
Nodes (8): AgentServiceServicer, Missing associated documentation comment in .proto file., RegisterAgent is the onboarding call for a new agent using a deployment token., UpdateAgentStatus updates the current state of a persistent agent., GetUploadLink returns a presigned URL for MinIO file uploads., VerifyAgentSecret validates an operational secret against an agent ID., ListAgents returns the persistent agents attached to a company., GetAgentStatusSummary returns aggregated agent status counters for a company.

### Community 31 - "VulnerabilityService"
Cohesion: 0.14
Nodes (5): Constructor.          Args:             channel: A grpc.Channel., ScanService handles orchestration of security scans., ScanService handles orchestration of security scans., ScanService, ScanServiceStub

### Community 32 - "test_models.py"
Cohesion: 0.16
Nodes (14): _execute_generate_and_store_pdf_report(), generate_and_store_pdf_report(), Generates PDF bytes in memory and stores them in scans.report_pdf., Generates a structured PDF report in memory and stores it in scans.report_pdf., Test saving vulnerabilities and their evidences., Test generating and storing a PDF report successfully., Test exception when storing PDF for a missing scan., Test PDF report activity when DB connection cannot be established. (+6 more)

### Community 33 - "properties"
Cohesion: 0.14
Nodes (8): ScanService handles orchestration of security scans., StartScan initiates a new security scan for a target image., GetScanStatus returns the current status and timing of a scan., ListScans retrieves a history of all scans., GetScanReport returns the PDF report data for a completed scan., WatchScanStatus provides a stream of scan status updates., UpdateScanStatus updates the status of a scan (called by Agents)., ScanServiceServicer

### Community 34 - "AgentService"
Cohesion: 0.15
Nodes (13): items, type, items, type, items, type, type, aliases (+5 more)

### Community 35 - "AgentServiceServicer"
Cohesion: 0.07
Nodes (9): URL, _build_db_url(), get_engine(), get_session(), get_session_factory(), Builds the SQLAlchemy DB URL securely., Lazily initializes and returns the SQLAlchemy engine., Lazily initializes and returns the session factory. (+1 more)

### Community 36 - "ScanService"
Cohesion: 0.15
Nodes (8): PingService, PingServiceServicer, PingServiceStub, Constructor.          Args:             channel: A grpc.Channel., Missing associated documentation comment in .proto file., Missing associated documentation comment in .proto file., Missing associated documentation comment in .proto file., Missing associated documentation comment in .proto file.

### Community 37 - "ScanServiceServicer"
Cohesion: 0.15
Nodes (12): db_session(), Tests first-login invitation persistence and relationship to a user., Tests the basic License model., In-memory SQLite session for testing models., Tests the Company model creation and its basic fields., Tests the User model, including the role enum and default fields., Tests the RefreshToken model and its relationship to a user., test_company_creation() (+4 more)

### Community 38 - "OnboardingInvitation"
Cohesion: 0.12
Nodes (10): str, CompanyCreateError, OnboardingInvitation, One-time token used to activate an onboarded owner account., User roles matching the PostgreSQL Enum 'user_role'., Lifecycle status for user account activation., UserActivationStatus, UserRole (+2 more)

### Community 39 - "type"
Cohesion: 0.17
Nodes (11): 📡 Agents & Runtime Status, 🔐 Authentication & Session Tracking, 🏢 Companies & Multi-Tenancy, 🏗️ Core Models, 🗄️ Database Architecture & Models, 🛠️ Implementation Details, JSONB Support, Password Security (+3 more)

### Community 40 - "config.py"
Cohesion: 0.22
Nodes (8): identify_attack_targets(), _artifact_payload(), download_minio_artifact(), parse_minio_reference(), test_artifact_payload_maps_topology_json_to_sandbox_request(), test_download_minio_artifact_reads_object_and_returns_deployable_payload(), test_parse_minio_reference_supports_explicit_and_default_bucket(), ValueError

### Community 41 - "update_scan_status"
Cohesion: 0.17
Nodes (12): _execute_status_update(), Internal helper to execute the SQL update., Updates the status of a specific scan in the PostgreSQL database., update_scan_status(), Test activity throwing exception when rowcount is 0., Test activity throwing exception when DB is down., Test updating the status of a scan successfully., Test intermediate status updates do not set completed_at. (+4 more)

### Community 42 - "ping_pb2_grpc.py"
Cohesion: 0.17
Nodes (11): 📡 Agents & Statut Runtime, 🗄️ Architecture de la Base de Données & Modèles, 🔐 Authentification & Suivi de Session, 🛠️ Détails d'Implémentation, 🏢 Entreprises & Multi-Tenancy, 🏗️ Modèles Principaux, 🎯 Pentest & Vulnérabilités, Support JSONB (+3 more)

### Community 43 - "get_session_factory"
Cohesion: 0.17
Nodes (12): type, additionalProperties, properties, type, type, databaseColumn, type, type (+4 more)

### Community 44 - "🏗️ Core Models"
Cohesion: 0.18
Nodes (11): emptyDir, additionalProperties, properties, required, type, minLength, type, minLength (+3 more)

### Community 45 - "🏗️ Modèles Principaux"
Cohesion: 0.20
Nodes (10): additionalProperties, properties, type, databaseTable, items, type, items, type (+2 more)

### Community 46 - "$defs"
Cohesion: 0.20
Nodes (9): 1. Proto (`Aegis-AI-Proto`), 2. Brain (`Aegis-AI-Brain`), 3. API Gateway (`Aegis-AI-Api-Gateway`), 4. Dashboard (`Aegis-AI-Dashboard`), Changes Made, CI/CD Stabilization, Real-Time Update Flow, Verification (+1 more)

### Community 47 - "properties"
Cohesion: 0.22
Nodes (9): items, type, additionalProperties, properties, type, databaseIndex, columns, unique (+1 more)

### Community 48 - "name"
Cohesion: 0.22
Nodes (9): additionalProperties, properties, type, databaseForeignKey, referenced_columns, referenced_table, items, type (+1 more)

### Community 49 - "db_activities.py"
Cohesion: 0.23
Nodes (11): _dedupe_evidences(), _dedupe_vulnerabilities(), _execute_save_vulnerabilities(), Internal helper to insert vulnerabilities and their evidences., Saves a list of vulnerabilities and their evidences to the PostgreSQL database., save_vulnerabilities(), _stable_json(), Duplicate findings/evidences in a single run are stored once. (+3 more)

### Community 50 - "CompanyService"
Cohesion: 0.20
Nodes (6): datetime, Establishes a raw connection to the PostgreSQL database (legacy)., Agent model mapped to the 'agents' table., License, License model mapped to the 'licenses' table., User model mapped to the 'users' table.

### Community 51 - "properties"
Cohesion: 0.25
Nodes (9): port, additionalProperties, maximum, minimum, properties, type, port, protocol (+1 more)

### Community 52 - "Changes Made"
Cohesion: 0.25
Nodes (7): 1. `PentestWorkflow`, 1. Post-payment Client Onboarding (MVP), Architecture (MVP v2), Service Logic Flows, Temporal Workflows Overview, The Aegis AI Brain (Orchestrator), Zero Trust Security Scope

### Community 53 - "columns"
Cohesion: 0.25
Nodes (7): 1. Onboarding Client Post-Paiement (MVP), 1. `PentestWorkflow`, Architecture (MVP v2), Flux Métier (Workflows de Service), Le Brain Aegis AI (Orchestrateur), Panorama des Workflows Temporal, Périmètre Zero Trust

### Community 54 - "properties"
Cohesion: 0.25
Nodes (8): type, externalMock, additionalProperties, properties, type, type, capture, host

### Community 55 - "properties"
Cohesion: 0.25
Nodes (8): service, type, headless, type, additionalProperties, properties, type, type

### Community 57 - "test_internal_auth.py"
Cohesion: 0.29
Nodes (6): 🧠 Aegis AI - Brain Orchestrator, 🐳 Deployment (Kubernetes), 🛠️ Development, 🚀 Key Features, 🔐 Security & DevSecOps Mandates, 🏗️ System Architecture & Role

### Community 58 - "The Aegis AI Brain (Orchestrator)"
Cohesion: 0.33
Nodes (3): test_update_email_conflict(), test_update_password_invalid_old(), test_update_profile_success()

### Community 59 - "Le Brain Aegis AI (Orchestrateur)"
Cohesion: 0.40
Nodes (4): Verify session_factory is only created on first access., Verify AuthService initializes without triggering DB configuration., test_auth_service_init_is_truly_lazy(), test_auth_service_lazy_factory()

### Community 60 - "externalMock"
Cohesion: 0.50
Nodes (4): maximum, minimum, type, container_port

### Community 61 - "service"
Cohesion: 0.50
Nodes (4): maximum, minimum, type, number

### Community 62 - "update_scan_debug_bundle"
Cohesion: 0.25
Nodes (8): _execute_update_scan_debug_bundle(), Internal helper to persist the latest sandbox debug bundle reference., Stores the latest Deployer debug bundle reference for a scan., update_scan_debug_bundle(), Test storing a sandbox debug bundle reference., Test empty debug bundle references do not touch the database., test_update_scan_debug_bundle_skips_empty_reference(), test_update_scan_debug_bundle_success()

### Community 63 - "download_minio_artifact"
Cohesion: 0.50
Nodes (4): target_port, maximum, minimum, type

### Community 67 - "sandbox-topology.schema.json"
Cohesion: 0.67
Nodes (3): additionalProperties, type, databaseSchema

### Community 68 - "agent_watcher.py"
Cohesion: 0.07
Nodes (22): GetMeResponse, LoginRequest, LoginResponse, RemoveAvatarRequest, RemoveAvatarResponse, UpdatePasswordRequest, UpdatePasswordResponse, UpdateProfileRequest (+14 more)

### Community 69 - "test_search_coverage.py"
Cohesion: 0.67
Nodes (3): tables, items, type

### Community 72 - ".Logout"
Cohesion: 0.50
Nodes (3): LogoutRequest, LogoutResponse, Invalidates a refresh token by marking it as revoked.

### Community 73 - ".Refresh"
Cohesion: 0.50
Nodes (3): RefreshRequest, RefreshResponse, Validates refresh token and returns a new Access token.

### Community 77 - ".SetupPassword"
Cohesion: 0.50
Nodes (3): SetupPasswordRequest, SetupPasswordResponse, Activates an invited account and starts a user session.

## Knowledge Gaps
- **178 isolated node(s):** `entrypoint.sh script`, `aegis-ai-brain`, `$schema`, `$id`, `title` (+173 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **15 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `AuthService` connect `agent_watcher.py` to `User`, `OnboardingInvitation`, `.Logout`, `.Refresh`, `.SetupPassword`, `CompanyService`, `.UpdateEmail`?**
  _High betweenness centrality (0.041) - this node is a cross-community bridge._
- **Why does `Establishes a raw connection to the PostgreSQL database (legacy).` connect `CompanyService` to `BillingService`, `AgentService`, `get_db_connection`, `db_activities.py`, `properties`?**
  _High betweenness centrality (0.030) - this node is a cross-community bridge._
- **Why does `$defs` connect `PentestWorkflow` to `sandbox-topology.schema.json`, `properties`, `get_session_factory`, `🏗️ Core Models`, `🏗️ Modèles Principaux`, `properties`, `name`, `properties`, `properties`, `properties`, `AuthService`, `hash_password`?**
  _High betweenness centrality (0.029) - this node is a cross-community bridge._
- **Are the 47 inferred relationships involving `User` (e.g. with `AuthErrorCode` and `AuthService`) actually correct?**
  _`User` has 47 INFERRED edges - model-reasoned connections that need verification._
- **Are the 9 inferred relationships involving `GraphDrivenPentestWorkflow` (e.g. with `SandboxTopologyValidationError` and `test_graph_driven_pentest_workflow_success()`) actually correct?**
  _`GraphDrivenPentestWorkflow` has 9 INFERRED edges - model-reasoned connections that need verification._
- **Are the 21 inferred relationships involving `Company` (e.g. with `._adjust_tokens_db_sync()` and `._get_balance_db_sync()`) actually correct?**
  _`Company` has 21 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `CompanyService` (e.g. with `AuditLog` and `OnboardingInvitation`) actually correct?**
  _`CompanyService` has 6 INFERRED edges - model-reasoned connections that need verification._