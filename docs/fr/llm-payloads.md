# 🧠 Assistance LLM aux payloads

Le Brain peut utiliser une logique assistée par LLM pour aider à générer des
payloads candidats et des explications de remédiation. Cette capacité reste bornée
par des contrôles de sûreté et ne remplace jamais la validation déterministe.

---

## Usage prévu

- Suggérer des payloads candidats pour les classes de vulnérabilités supportées.
- Adapter les entrées de test au comportement observé du service.
- Résumer les preuves techniques pour les rapports.
- Aider à produire des recommandations de remédiation après confirmation d'une
  vulnérabilité.

---

## Limites de sûreté

- Ne jamais envoyer de secrets, d'identifiants client, de tokens ou de données
  privées brutes à des fournisseurs de modèles externes.
- N'exécuter des payloads offensifs qu'à l'intérieur de workflows de scan /
  sandbox contrôlés.
- Stocker les preuves produites par le worker, pas les affirmations du modèle.
- Exiger une validation déterministe avant qu'une vulnérabilité ne soit marquée
  confirmée.

---

## Interaction avec le worker

Le Worker Pentest traite la sortie du modèle comme des **candidats d'entrée**. Le
worker reste responsable de l'exécution des requêtes, de la capture des réponses,
de l'extraction des preuves, de la classification de sévérité, de l'upload des
preuves et du reporting du statut final.

---

## Données de prompt

Le contexte de prompt autorisé se limite à des métadonnées techniques : type de
service, version, classe d'erreur, motifs de codes de statut HTTP et extraits de
réponse assainis.

---

*Aegis AI Brain — Decision Center — 2026*
