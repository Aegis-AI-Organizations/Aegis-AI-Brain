# Graph Report - Aegis-AI-Brain  (2026-07-13)

## Corpus Check
- 105 files · ~38,271 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1237 nodes · 1940 edges · 107 communities (89 shown, 18 thin omitted)
- Extraction: 84% EXTRACTED · 16% INFERRED · 0% AMBIGUOUS · INFERRED: 302 edges (avg confidence: 0.72)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `ee86249b`
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
- [[_COMMUNITY_generate_and_store_pdf_report|generate_and_store_pdf_report]]
- [[_COMMUNITY_download_minio_artifact|download_minio_artifact]]
- [[_COMMUNITY_test_rbac_visibility.py|test_rbac_visibility.py]]
- [[_COMMUNITY_🧠 Aegis AI - Brain Orchestrator|🧠 Aegis AI - Brain Orchestrator]]
- [[_COMMUNITY_.RevokeAgentToken|.RevokeAgentToken]]
- [[_COMMUNITY_sandbox-topology.schema.json|sandbox-topology.schema.json]]
- [[_COMMUNITY_agent_watcher.py|agent_watcher.py]]
- [[_COMMUNITY_test_auth_service_ext.py|test_auth_service_ext.py]]
- [[_COMMUNITY_test_auth_init.py|test_auth_init.py]]
- [[_COMMUNITY_.Logout|.Logout]]
- [[_COMMUNITY_.Refresh|.Refresh]]
- [[_COMMUNITY_container_port|container_port]]
- [[_COMMUNITY_number|number]]
- [[_COMMUNITY_target_port|target_port]]
- [[_COMMUNITY_.SetupPassword|.SetupPassword]]
- [[_COMMUNITY_conftest.py|conftest.py]]
- [[_COMMUNITY_.GetMe|.GetMe]]
- [[_COMMUNITY_.RemoveAvatar|.RemoveAvatar]]
- [[_COMMUNITY_tables|tables]]
- [[_COMMUNITY_.UpdateEmail|.UpdateEmail]]
- [[_COMMUNITY_.UpdatePassword|.UpdatePassword]]
- [[_COMMUNITY_.UpdateProfile|.UpdateProfile]]
- [[_COMMUNITY_.WatchCompanyUpdates|.WatchCompanyUpdates]]
- [[_COMMUNITY_llm-payloads|llm-payloads.md]]
- [[_COMMUNITY_neo4j-graph|neo4j-graph.md]]
- [[_COMMUNITY_llm-payloads|llm-payloads.md]]
- [[_COMMUNITY_neo4j-graph|neo4j-graph.md]]
- [[_COMMUNITY_entrypoint.sh|entrypoint.sh]]
- [[_COMMUNITY_databaseName|databaseName]]
- [[_COMMUNITY_aegis-ai-brain|aegis-ai-brain]]

## God Nodes (most connected - your core abstractions)
1. `User` - 50 edges
2. `CompanyService` - 30 edges
3. `GraphDrivenPentestWorkflow` - 30 edges
4. `AuthService` - 29 edges
5. `Company` - 23 edges
6. `OnboardingInvitation` - 22 edges
7. `MockContext` - 18 edges
8. `get_db_connection()` - 17 edges
9. `$ref` - 16 edges
10. `$defs` - 16 edges

## Surprising Connections (you probably didn't know these)
- `test_update_email_conflict()` --calls--> `User`  [INFERRED]
  tests/test_auth_service_ext.py → src/models/user.py
- `test_update_profile_success()` --calls--> `User`  [INFERRED]
  tests/test_auth_service_ext.py → src/models/user.py
- `test_refresh_success()` --calls--> `User`  [INFERRED]
  tests/test_auth_service.py → src/models/user.py
- `test_list_users_owner_visibility()` --calls--> `User`  [INFERRED]
  tests/test_rbac_visibility.py → src/models/user.py
- `test_generate_and_store_pdf_report_not_found()` --indirect_call--> `generate_and_store_pdf_report()`  [INFERRED]
  tests/test_activities.py → src/activities/db_activities.py

## Import Cycles
- None detected.

## Communities (107 total, 18 thin omitted)

### Community 0 - "GraphDrivenPentestWorkflow"
Cohesion: 0.11
Nodes (24): GraphDrivenPentestWorkflow, Exception, failing_update_scan_status(), mock_build_sandbox_topology(), mock_create_sandbox(), mock_destroy_sandbox(), mock_download_minio_artifact(), mock_generate_and_store_pdf_report() (+16 more)

### Community 1 - "test_email_utils.py"
Cohesion: 0.12
Nodes (30): ABC, create_email_service(), EmailService, _format_from_header(), MailpitEmailService, ProductionEmailService, _build_action_url(), _build_email_parts() (+22 more)

### Community 2 - "BillingService"
Cohesion: 0.07
Nodes (19): AdjustTokensRequest, AdjustTokensResponse, GetBalanceRequest, GetBalanceResponse, GetLedgerRequest, GetLedgerResponse, GetUsageStatsRequest, GetUsageStatsResponse (+11 more)

### Community 3 - "properties"
Cohesion: 0.06
Nodes (31): items, type, $ref, type, type, type, type, type (+23 more)

### Community 4 - "User"
Cohesion: 0.09
Nodes (16): Company, Company model mapped to the 'companies' table., User model mapped to the 'users' table., User, test_create_company_success(), test_create_user_success(), test_list_companies_success(), test_list_users_includes_all_company_owners() (+8 more)

### Community 5 - "AuthService"
Cohesion: 0.12
Nodes (14): LoginRequest, LoginResponse, AuthErrorCode, AuthService, Authenticates user and returns Access + Refresh tokens., Synchronous part of Refresh logic., Synchronous part of GetMe logic., Structured error codes for Auth synchronization methods. (+6 more)

### Community 6 - "properties"
Cohesion: 0.07
Nodes (29): type, type, externalRoute, file, additionalProperties, properties, type, additionalProperties (+21 more)

### Community 7 - "$ref"
Cohesion: 0.08
Nodes (29): items, type, items, type, items, type, items, type (+21 more)

### Community 8 - "CompanyService"
Cohesion: 0.12
Nodes (11): CreateCompanyRequest, CreateCompanyResponse, ListAuditLogsRequest, ListAuditLogsResponse, ListCompaniesRequest, ListCompaniesResponse, OnboardCompanyRequest, OnboardCompanyResponse (+3 more)

### Community 9 - "AgentService"
Cohesion: 0.11
Nodes (13): AgentService, Onboarding of the Rust agent using a deployment token (ag_...).         Returns, Updates the agent's state (IDLE, UPLOADING, etc.) and last_seen timestamp., Generates a presigned MinIO URL for the agent to upload infrastructure files/log, Validates an operational secret against an agent ID.         Used by the Gateway, InternalAuthService, gRPC service for verifying agent deployment tokens. Caching is handled by the AP, Synchronously verifies an agent token and returns the company_id. (+5 more)

### Community 10 - "engine.py"
Cohesion: 0.21
Nodes (24): FPDF, build_report(), _count_by_severity(), _ensure_space(), _extract_target_image_path(), _extract_target_name(), _format_loot_data(), _normalize_severity() (+16 more)

### Community 11 - "BillingService"
Cohesion: 0.08
Nodes (12): BillingService, BillingServiceServicer, BillingServiceStub, BillingService handles token management and consumption history., Constructor.          Args:             channel: A grpc.Channel., BillingService handles token management and consumption history., GetBalance retrieves the current token balance for a company., GetLedger retrieves the history of token transactions for a company. (+4 more)

### Community 13 - "get_db_connection"
Cohesion: 0.11
Nodes (8): Connection, get_db_connection(), Establishes a raw connection to the PostgreSQL database (legacy)., ScanService, VulnerabilityService, Test returning a database connection on success., Test raising ConnectionError when database connection fails., TestDatabaseConnection

### Community 14 - "database_seeding.py"
Cohesion: 0.23
Nodes (18): DatabaseTarget, discover_postgres_targets(), _env_from_container(), _is_postgres_candidate(), _kubernetes_api_base(), _kubernetes_get(), _kubernetes_namespace(), _pod_matches_selector() (+10 more)

### Community 15 - "AuthServiceServicer"
Cohesion: 0.10
Nodes (11): AuthServiceServicer, UpdateProfile updates the authenticated user's profile information., UpdateEmail updates the authenticated user's email address., UpdatePassword updates the authenticated user's password., RemoveAvatar deletes the authenticated user's profile picture., AuthService handles user authentication, session management, and JWT generation., Login authenticates a user and returns an access token and refresh token., Refresh generates a new access token using a valid refresh token. (+3 more)

### Community 16 - "AuthInterceptor"
Cohesion: 0.18
Nodes (13): serve(), AuthInterceptor, gRPC interceptor for JWT validation and verified identity injection., test_grpc_server_mtls_fails_when_certificate_missing(), test_grpc_server_mtls_requires_client_certificate(), test_grpc_server_serve_registration(), MockHandlerCallDetails, test_auth_interceptor_expired_token() (+5 more)

### Community 17 - "sandbox_topology_validation.py"
Cohesion: 0.26
Nodes (16): Path, _extract_topology(), _format_path(), _matches_type(), Any, _resolve_ref(), SandboxTopologyValidationError, _schema() (+8 more)

### Community 18 - "test_grpc_server.py"
Cohesion: 0.18
Nodes (14): PingService, MockContext, test_ping_service(), test_scan_service_list(), test_scan_service_report(), test_scan_service_start(), test_scan_service_start_failure_compensation(), test_scan_service_start_persists_long_topology_target() (+6 more)

### Community 19 - "Neo4jAttackTargetService"
Cohesion: 0.20
Nodes (10): AttackTarget, identify_attack_targets(), Neo4jAttackTargetService, Any, test_identify_attack_targets_falls_back_to_direct_selected_routes(), test_identify_attack_targets_includes_container_image_metadata(), test_identify_attack_targets_omits_agent_id_when_missing(), test_identify_attack_targets_orders_and_normalizes_paths() (+2 more)

### Community 20 - "PentestWorkflow"
Cohesion: 0.18
Nodes (8): PentestWorkflow, Exception, Ask the dedicated Deployer worker to create the sandbox., Execute the actual pentest activity on the Worker., Main orchestration workflow that simulates a pentest., Ask the dedicated Deployer worker to destroy the sandbox., Handles cleanup and status update on workflow failure., Helper to update scan status via activity.

### Community 21 - "object"
Cohesion: 0.12
Nodes (12): object, CompanyServiceStub, Constructor.          Args:             channel: A grpc.Channel., CompanyService handles registration and administrative management of companies., InternalAuthService, InternalAuthServiceServicer, InternalAuthServiceStub, Constructor.          Args:             channel: A grpc.Channel. (+4 more)

### Community 23 - "Base"
Cohesion: 0.13
Nodes (13): DeclarativeBase, Base, Modern SQLAlchemy declarative base for all models., License, License model mapped to the 'licenses' table., Evidence, Scan model mapped to the 'scans' table., Vulnerability model mapped to the 'vulnerabilities' table. (+5 more)

### Community 24 - "properties"
Cohesion: 0.12
Nodes (17): type, properties, type, type, database_name, engine, password, source_container_id (+9 more)

### Community 25 - "AuthService"
Cohesion: 0.12
Nodes (5): AuthService, AuthServiceStub, Constructor.          Args:             channel: A grpc.Channel., AuthService handles user authentication, session management, and JWT generation., AuthService handles user authentication, session management, and JWT generation.

### Community 26 - "db.py"
Cohesion: 0.21
Nodes (7): normalize_persisted_target_image(), get_identity(), Securely extracts identity from verified context or gRPC metadata fallback., Decorator to inject identity into the handler.     Supports both async functions, to_pb_timestamp(), with_identity(), _extract_loot_fields()

### Community 27 - "Neo4jSandboxTopologyService"
Cohesion: 0.26
Nodes (6): build_sandbox_topology(), Neo4jSandboxTopologyService, Any, test_build_sandbox_topology_includes_known_workload_routes(), test_build_sandbox_topology_maps_containers_to_deployer_payload(), test_build_sandbox_topology_uses_default_http_port_when_missing()

### Community 28 - "hash_password"
Cohesion: 0.15
Nodes (14): hash_password(), Verifies a plain-text password against a stored bcrypt hash.      Args:, Hashes a plain-text password using the bcrypt algorithm.      Args:         pass, verify_password(), test_login_db_error(), test_login_inactive_user(), test_login_success(), test_setup_password_collaborator_does_not_return_agent_token() (+6 more)

### Community 29 - "properties"
Cohesion: 0.12
Nodes (16): additionalProperties, properties, type, connection, source, source_name, sourceName, target (+8 more)

### Community 30 - "CompanyServiceServicer"
Cohesion: 0.12
Nodes (9): CompanyServiceServicer, ListAuditLogs retrieves system audit trails (Admin only)., CompanyService handles registration and administrative management of companies., CreateCompany registers a new company in the system., ListCompanies retrieves all companies (SuperAdmin only)., OnboardCompany handles the creation of a new company and its owner in one step., RotateAgentToken generates a new deployment token for a company., RevokeAgentToken invalidates the current deployment token for a company. (+1 more)

### Community 31 - "VulnerabilityService"
Cohesion: 0.12
Nodes (9): Constructor.          Args:             channel: A grpc.Channel., VulnerabilityService handles retrieval of vulnerability data., GetVulnerabilities returns a list of vulnerabilities for a scan., GetEvidences returns the evidence collected for a specific vulnerability., VulnerabilityService handles retrieval of vulnerability data., VulnerabilityService handles retrieval of vulnerability data., VulnerabilityService, VulnerabilityServiceServicer (+1 more)

### Community 32 - "test_models.py"
Cohesion: 0.17
Nodes (15): db_session(), Session, Tests first-login invitation persistence and relationship to a user., Tests the basic License model., In-memory SQLite session for testing models., Tests the Company model creation and its basic fields., Tests the User model, including the role enum and default fields., Tests complex relationships between companies and users (owner/members). (+7 more)

### Community 33 - "properties"
Cohesion: 0.13
Nodes (15): items, type, initContainer, $ref, minLength, type, additionalProperties, properties (+7 more)

### Community 34 - "AgentService"
Cohesion: 0.14
Nodes (5): AgentService, AgentServiceStub, Constructor.          Args:             channel: A grpc.Channel., Missing associated documentation comment in .proto file., Missing associated documentation comment in .proto file.

### Community 35 - "AgentServiceServicer"
Cohesion: 0.14
Nodes (8): AgentServiceServicer, Missing associated documentation comment in .proto file., RegisterAgent is the onboarding call for a new agent using a deployment token., UpdateAgentStatus updates the current state of a persistent agent., GetUploadLink returns a presigned URL for MinIO file uploads., VerifyAgentSecret validates an operational secret against an agent ID., ListAgents returns the persistent agents attached to a company., GetAgentStatusSummary returns aggregated agent status counters for a company.

### Community 36 - "ScanService"
Cohesion: 0.14
Nodes (5): Constructor.          Args:             channel: A grpc.Channel., ScanService handles orchestration of security scans., ScanService handles orchestration of security scans., ScanService, ScanServiceStub

### Community 37 - "ScanServiceServicer"
Cohesion: 0.14
Nodes (8): ScanService handles orchestration of security scans., StartScan initiates a new security scan for a target image., GetScanStatus returns the current status and timing of a scan., ListScans retrieves a history of all scans., GetScanReport returns the PDF report data for a completed scan., WatchScanStatus provides a stream of scan status updates., UpdateScanStatus updates the status of a scan (called by Agents)., ScanServiceServicer

### Community 38 - "OnboardingInvitation"
Cohesion: 0.19
Nodes (10): CompanyCreateError, OnboardingInvitation, One-time token used to activate an onboarded owner account., User roles matching the PostgreSQL Enum 'user_role'., Lifecycle status for user account activation., UserActivationStatus, UserRole, str (+2 more)

### Community 39 - "type"
Cohesion: 0.15
Nodes (13): items, type, items, type, items, type, type, aliases (+5 more)

### Community 41 - "update_scan_status"
Cohesion: 0.19
Nodes (12): Updates the status of a specific scan in the PostgreSQL database., update_scan_status(), Test exception when storing PDF for a missing scan., Test intermediate status updates do not set completed_at., Test activity throwing exception when rowcount is 0., Test activity throwing exception when DB is down., Test updating the status of a scan successfully., test_generate_and_store_pdf_report_not_found() (+4 more)

### Community 42 - "ping_pb2_grpc.py"
Cohesion: 0.15
Nodes (8): PingService, PingServiceServicer, PingServiceStub, Constructor.          Args:             channel: A grpc.Channel., Missing associated documentation comment in .proto file., Missing associated documentation comment in .proto file., Missing associated documentation comment in .proto file., Missing associated documentation comment in .proto file.

### Community 43 - "get_session_factory"
Cohesion: 0.15
Nodes (10): _build_db_url(), get_engine(), get_session(), get_session_factory(), Session, Builds the SQLAlchemy DB URL securely., Lazily initializes and returns the SQLAlchemy engine., Lazily initializes and returns the session factory. (+2 more)

### Community 44 - "🏗️ Core Models"
Cohesion: 0.17
Nodes (11): 📡 Agents & Runtime Status, 🔐 Authentication & Session Tracking, 🏢 Companies & Multi-Tenancy, 🏗️ Core Models, 🗄️ Database Architecture & Models, 🛠️ Implementation Details, JSONB Support, Password Security (+3 more)

### Community 45 - "🏗️ Modèles Principaux"
Cohesion: 0.17
Nodes (11): 📡 Agents & Statut Runtime, 🗄️ Architecture de la Base de Données & Modèles, 🔐 Authentification & Suivi de Session, 🛠️ Détails d'Implémentation, 🏢 Entreprises & Multi-Tenancy, 🏗️ Modèles Principaux, 🎯 Pentest & Vulnérabilités, Support JSONB (+3 more)

### Community 46 - "$defs"
Cohesion: 0.17
Nodes (12): type, additionalProperties, type, $defs, databaseSchema, stringMap, workload, additionalProperties (+4 more)

### Community 47 - "properties"
Cohesion: 0.17
Nodes (12): type, additionalProperties, properties, type, type, databaseColumn, type, type (+4 more)

### Community 48 - "name"
Cohesion: 0.18
Nodes (11): emptyDir, additionalProperties, properties, required, type, minLength, type, minLength (+3 more)

### Community 49 - "db_activities.py"
Cohesion: 0.20
Nodes (10): _execute_save_vulnerabilities(), _execute_status_update(), Saves a list of vulnerabilities and their evidences to the PostgreSQL database., Internal helper to execute the SQL update., Internal helper to insert vulnerabilities and their evidences., save_vulnerabilities(), Test saving empty vulnerabilities list., Test saving vulnerabilities and their evidences. (+2 more)

### Community 51 - "properties"
Cohesion: 0.20
Nodes (10): additionalProperties, properties, type, databaseTable, items, type, items, type (+2 more)

### Community 52 - "Changes Made"
Cohesion: 0.20
Nodes (9): 1. Proto (`Aegis-AI-Proto`), 2. Brain (`Aegis-AI-Brain`), 3. API Gateway (`Aegis-AI-Api-Gateway`), 4. Dashboard (`Aegis-AI-Dashboard`), Changes Made, CI/CD Stabilization, Real-Time Update Flow, Verification (+1 more)

### Community 53 - "columns"
Cohesion: 0.22
Nodes (9): items, type, additionalProperties, properties, type, databaseIndex, columns, unique (+1 more)

### Community 54 - "properties"
Cohesion: 0.22
Nodes (9): additionalProperties, properties, type, databaseForeignKey, referenced_columns, referenced_table, items, type (+1 more)

### Community 55 - "properties"
Cohesion: 0.25
Nodes (9): port, additionalProperties, maximum, minimum, properties, type, port, protocol (+1 more)

### Community 56 - "StatusBroadcaster"
Cohesion: 0.25
Nodes (3): StatusBroadcaster, test_broadcaster(), test_to_pb_timestamp()

### Community 57 - "test_internal_auth.py"
Cohesion: 0.22
Nodes (8): Valid active token returns the associated company_id., Unknown or inactive token returns None., DB error returns None gracefully (does not raise)., Invalid token formats fail before DB lookup., test_verify_token_db_exception(), test_verify_token_invalid_format_skips_database(), test_verify_token_not_found(), test_verify_token_success()

### Community 58 - "The Aegis AI Brain (Orchestrator)"
Cohesion: 0.25
Nodes (7): 1. `PentestWorkflow`, 1. Post-payment Client Onboarding (MVP), Architecture (MVP v2), Service Logic Flows, Temporal Workflows Overview, The Aegis AI Brain (Orchestrator), Zero Trust Security Scope

### Community 59 - "Le Brain Aegis AI (Orchestrateur)"
Cohesion: 0.25
Nodes (7): 1. Onboarding Client Post-Paiement (MVP), 1. `PentestWorkflow`, Architecture (MVP v2), Flux Métier (Workflows de Service), Le Brain Aegis AI (Orchestrateur), Panorama des Workflows Temporal, Périmètre Zero Trust

### Community 60 - "externalMock"
Cohesion: 0.25
Nodes (8): type, externalMock, additionalProperties, properties, type, type, capture, host

### Community 61 - "service"
Cohesion: 0.25
Nodes (8): service, type, headless, type, additionalProperties, properties, type, type

### Community 62 - "generate_and_store_pdf_report"
Cohesion: 0.25
Nodes (8): _execute_generate_and_store_pdf_report(), generate_and_store_pdf_report(), Generates PDF bytes in memory and stores them in scans.report_pdf., Generates a structured PDF report in memory and stores it in scans.report_pdf., Test generating and storing a PDF report successfully., Test PDF report activity when DB connection cannot be established., test_generate_and_store_pdf_report_db_fail(), test_generate_and_store_pdf_report_success()

### Community 63 - "download_minio_artifact"
Cohesion: 0.32
Nodes (7): _artifact_payload(), download_minio_artifact(), parse_minio_reference(), test_artifact_payload_maps_topology_json_to_sandbox_request(), test_download_minio_artifact_reads_object_and_returns_deployable_payload(), test_parse_minio_reference_supports_explicit_and_default_bucket(), ValueError

### Community 65 - "🧠 Aegis AI - Brain Orchestrator"
Cohesion: 0.29
Nodes (6): 🧠 Aegis AI - Brain Orchestrator, 🐳 Deployment (Kubernetes), 🛠️ Development, 🚀 Key Features, 🔐 Security & DevSecOps Mandates, 🏗️ System Architecture & Role

### Community 66 - ".RevokeAgentToken"
Cohesion: 0.29
Nodes (4): RevokeAgentTokenRequest, RevokeAgentTokenResponse, RotateAgentTokenRequest, RotateAgentTokenResponse

### Community 67 - "sandbox-topology.schema.json"
Cohesion: 0.29
Nodes (6): additionalProperties, $id, required, $schema, title, type

### Community 68 - "agent_watcher.py"
Cohesion: 0.43
Nodes (4): AgentWatcher, Starts the Redis keyspace notification listener., Updates the agent status to OFFLINE in the database., start_agent_watcher()

### Community 70 - "test_auth_service_ext.py"
Cohesion: 0.33
Nodes (3): test_update_email_conflict(), test_update_password_invalid_old(), test_update_profile_success()

### Community 71 - "test_auth_init.py"
Cohesion: 0.40
Nodes (4): Verify session_factory is only created on first access., Verify AuthService initializes without triggering DB configuration., test_auth_service_init_is_truly_lazy(), test_auth_service_lazy_factory()

### Community 72 - ".Logout"
Cohesion: 0.50
Nodes (3): LogoutRequest, LogoutResponse, Invalidates a refresh token by marking it as revoked.

### Community 73 - ".Refresh"
Cohesion: 0.50
Nodes (3): RefreshRequest, RefreshResponse, Validates refresh token and returns a new Access token.

### Community 74 - "container_port"
Cohesion: 0.50
Nodes (4): maximum, minimum, type, container_port

### Community 75 - "number"
Cohesion: 0.50
Nodes (4): maximum, minimum, type, number

### Community 76 - "target_port"
Cohesion: 0.50
Nodes (4): target_port, maximum, minimum, type

### Community 77 - ".SetupPassword"
Cohesion: 0.50
Nodes (3): SetupPasswordRequest, SetupPasswordResponse, Activates an invited account and starts a user session.

### Community 83 - "tables"
Cohesion: 0.67
Nodes (3): tables, items, type

## Knowledge Gaps
- **170 isolated node(s):** `entrypoint.sh script`, `aegis-ai-brain`, `$schema`, `$id`, `title` (+165 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **18 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `AuthService` connect `AuthService` to `User`, `OnboardingInvitation`, `.Logout`, `.Refresh`, `test_auth_service.py`, `.SetupPassword`, `.GetMe`, `.RemoveAvatar`, `.UpdateEmail`, `.UpdatePassword`, `.UpdateProfile`?**
  _High betweenness centrality (0.040) - this node is a cross-community bridge._
- **Why does `$defs` connect `$defs` to `properties`, `sandbox-topology.schema.json`, `properties`, `properties`, `name`, `properties`, `service`, `columns`, `properties`, `properties`, `externalMock`, `properties`?**
  _High betweenness centrality (0.028) - this node is a cross-community bridge._
- **Why does `AgentService` connect `AgentService` to `db.py`, `get_session_factory`?**
  _High betweenness centrality (0.026) - this node is a cross-community bridge._
- **Are the 45 inferred relationships involving `User` (e.g. with `AuthErrorCode` and `AuthService`) actually correct?**
  _`User` has 45 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `CompanyService` (e.g. with `AuditLog` and `OnboardingInvitation`) actually correct?**
  _`CompanyService` has 6 INFERRED edges - model-reasoned connections that need verification._
- **Are the 7 inferred relationships involving `GraphDrivenPentestWorkflow` (e.g. with `start_worker()` and `test_graph_driven_pentest_workflow_success()`) actually correct?**
  _`GraphDrivenPentestWorkflow` has 7 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `AuthService` (e.g. with `OnboardingInvitation` and `User`) actually correct?**
  _`AuthService` has 4 INFERRED edges - model-reasoned connections that need verification._