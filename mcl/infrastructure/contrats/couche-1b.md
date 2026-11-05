# Contrat de la couche 1b — ia-adaptateurs (artefact `infrastructure`)

- **Statut** : esquisse (phase 0, 2026-11-05) ; finalisation juste avant la construction de la couche (phase(s) 9 et 10), puis gel par `mcl.py figer`.
- **Consommateurs cartographiés** : aucune couche interne
- **Dépend de** : couches 0d (réelles et figées) ; amont figé : aucun ; frontières externes doublées : aucune
- **Module** : `src/xpbots/infrastructure/ia_adaptateurs.py`
- **Sources normatives** : C04, C08 (rapprochement, redémarrage), A04, A08, A10 ; plan maître, section 7.I

---

Unité : collecteur_rss
Responsabilité : Collecter les flux RSS officiels de façon conditionnelle.
Signature : CollecteurRSS.collecter(flux) -> list[TexteBrut]
Entrée : flux Fed, BCE, BoE configurés
Sortie : textes bruts datés
Effets de bord : aucun
Erreurs, exceptions : SourceRefusee (repli 600 s)

---

Unité : clients_llm
Responsabilité : Appeler les API Groq, Gemini et OpenAI facultative selon A08.
Signature : ClientLLM.classer(dossier, schema) -> ReponseBrute
Entrée : requête construite par le service
Sortie : réponse brute et usage
Effets de bord : aucun
Erreurs, exceptions : 401/403, 429, 5xx, délai

---

## Spécification exécutable

- Catégorie 1 (`tests/robot/infrastructure/test_c1b_cat1_*.py`) : RSS conditionnel, clients Groq/Gemini/OpenAI factices.
- Catégorie 2 (`tests/robot/infrastructure/test_c1b_cat2_*.py`) : conformité manuelle avec les clés de l'utilisateur.

## Comportements documentés (loi de Hyrum)

Les consommateurs ne codent que contre ce qui est écrit ici. Les observables non documentés (ordre d'itération, texte exact des messages) ne sont pas garantis. Toute valeur normative est lue dans `config/`, jamais recopiée.
