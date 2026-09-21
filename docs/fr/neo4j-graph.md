# 🕸️ Graphe de topologie Neo4j

Le Brain stocke les relations d'infrastructure et de sécurité dans **Neo4j**, où
elles sont plus faciles à analyser sous forme de graphe que sous forme de lignes
relationnelles isolées.

---

## Objectif

- Représenter hôtes, conteneurs, services, images, namespaces, vulnérabilités et
  preuves.
- Relier la topologie découverte par l'agent aux vulnérabilités des scans.
- Supporter l'analyse de chemins d'attaque et d'impact.
- Fournir du contexte pour la remédiation et la génération de rapports.

---

## Nœuds typiques

| Nœud            | Description                                       |
| --------------- | ---------------------------------------------- |
| `Company`       | Tenant propriétaire des données du graphe         |
| `Agent`         | Sonde d'infrastructure déployée                   |
| `Host`          | Machine ou nœud découvert par un agent            |
| `Container`     | Charge de travail runtime                         |
| `Service`       | Service ou endpoint applicatif exposé             |
| `Scan`          | Exécution de pentest                              |
| `Vulnerability` | Vulnérabilité liée à un scan ou à un asset        |

## Relations typiques

| Relation       | Signification                        |
| -------------- | --------------------------------- |
| `OWNS`         | Frontière de propriété entreprise    |
| `OBSERVED`     | Un agent a observé un asset           |
| `RUNS`         | Un hôte exécute un conteneur ou service |
| `EXPOSES`      | Une charge expose un endpoint         |
| `FOUND`        | Un scan a trouvé une vulnérabilité    |
| `EVIDENCED_BY` | Une vulnérabilité a une preuve technique |

---

## Règle opérationnelle

Les données du graphe ne doivent jamais contourner le cloisonnement tenant. Toute
requête qui matérialise des données de graphe pour le Dashboard, les rapports ou
les workers doit être contrainte par le contexte entreprise (`company_id`).

---

*Aegis AI Brain — Graph Intelligence — 2026*
