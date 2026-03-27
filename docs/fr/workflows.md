# Le Brain Aegis AI (Orchestrateur)

Le "Cerveau" est l'orchestrateur asynchrone principal de l'écosystème Aegis. Conçu en Python robuste via le client PostgreSQL synchrone `psycopg` et `temporalio`, il reçoit les ordres d'audit de sécurité massifs en gRPC et coordonne une armée de 'workers' à travers des Workflows Temporal.

## Architecture (MVP v2)
Dans la version 2 du framework, le Brain assume **le rôle exclusif** de commandeur de système :
1. **Couche gRPC Serveur (`aegis.v2`)** : Écoute sans répit les impulsions relais provenant de l'API Gateway.
2. **Client PostgreSQL (`psycopg`)** : Consigne l'état des scans, gère la génération des UUID, accumule les vulnérabilités trouvées en temps réel.
3. **Client Temporal** : Lance les workflows asynchrones distribués à destination de la grille de microservices workers (`pentest-worker`, `ingest-worker`, etc.).

## Panorama des Workflows Temporal

### 1. `PentestWorkflow`
Le workflow le plus critique d'Aegis. Une fois éveillé par `StartScan`, le Brain décline ses étapes tactiques :

- **`deploy_sandbox_target` (Activité K8s)** : Forge dynamiquement un "bac à sable" stérile dans le cluster (`aegis-war-room-{scan_id}`). L'image cible y est injectée et isolée hermétiquement des autres applications internes de la plateforme.
- **`run_pentest` (Pentest Worker)** : Simultanément, la commande de déploiement pousse le worker défensif à arroser de payloads la cible. Le worker expédie les objets `Evidences` au fil de l'eau dans l'historique Temporal.
- **`cleanup_sandbox` (Activité K8s)** : Démolition intégrale du "war-room" ciblé pour restaurer l'intégrité et la mémoire vive sur le cluster après la réussite de l'attaque.

## Périmètre Zero Trust
Le Brain tourne dans l'enclave aveugle `aegis-system`. Protégé par les contraintes réseaux de Cilium, il reste **le seul et unique composant** formellement apte à adresser la base de données `aegis-postgres-mvp`.
