# 🕸️ Neo4j Topology Graph

The Brain stores infrastructure and security relationships in **Neo4j**, where
they are easier to analyze as a graph than as isolated relational rows.

---

## Purpose

- Represent hosts, containers, services, images, namespaces, vulnerabilities and
  evidences.
- Connect agent-discovered topology with scan findings.
- Support attack-path and impact analysis.
- Provide context for remediation and report generation.

---

## Typical nodes

| Node            | Description                                       |
| --------------- | ---------------------------------------------- |
| `Company`       | Tenant owner of the graph data                   |
| `Agent`         | Deployed infrastructure probe                    |
| `Host`          | Machine or node discovered by an agent           |
| `Container`     | Runtime workload                                 |
| `Service`       | Exposed service or application endpoint          |
| `Scan`          | Pentest execution                                |
| `Vulnerability` | Security finding linked to a scan or asset       |

## Typical relationships

| Relationship   | Meaning                           |
| -------------- | ------------------------------- |
| `OWNS`         | Company ownership boundary         |
| `OBSERVED`     | Agent observed an asset            |
| `RUNS`         | Host runs a container or service   |
| `EXPOSES`      | Workload exposes an endpoint       |
| `FOUND`        | Scan found a vulnerability         |
| `EVIDENCED_BY` | Vulnerability has technical proof  |

---

## Operational rule

Graph data must never bypass tenant scoping. Every query that materializes graph
data for the Dashboard, reports, or workers must be constrained by company
context (`company_id`).

---

*Aegis AI Brain — Graph Intelligence — 2026*
