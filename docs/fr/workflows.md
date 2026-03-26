# [FR] # Workflows | Aegis-AI-Brain

## Point d'Entrée : Serveur gRPC
Le composant Brain inclut désormais un **Serveur gRPC** embarqué.
- Il reçoit les requêtes de l'API Gateway via les services `ScanService` et `VulnerabilityService`.
- Il initialise les enregistrements en base de données de manière asynchrone (`psycopg`).
- Il interagit avec le client Temporal (`temporalio`) pour lancer les exécutions de `PentestWorkflow`.

## PentestWorkflow sequence

1. Update scan status to `PROVISIONING`
2. Deploy target sandbox in Kubernetes
3. Update scan status to `IN_PROGRESS`
4. Run pentest activity (`run_pentest`) on `PENTEST_TASK_QUEUE`
5. Save discovered vulnerabilities in PostgreSQL
6. Generate a structured PDF report and store it in `scans.report_pdf`
7. Cleanup sandbox resources
8. Update scan status to `COMPLETED`

## PDF report storage

The Brain worker now runs `generate_and_store_pdf_report(scan_id, vulnerabilities)`
after `save_vulnerabilities` succeeds.

- The report is generated in memory with `fpdf2`
- The final report follows a pentest-style structure:
  - cover page with report title, target snapshot/name, scan ID, and generation date
  - executive summary with total findings and severity breakdown
  - vulnerability summary table (type, severity, endpoint, short description)
  - detailed vulnerability sections with title, severity, endpoint, description,
    payload used, and evidence/loot blocks
- Severity is visually highlighted with colored labels
- Payload and evidence content is rendered in boxed blocks for readability
- PDF bytes are persisted with:

```sql
UPDATE scans SET report_pdf = %s WHERE id = %s
```
