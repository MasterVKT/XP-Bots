# Contrat de la couche 0d — http (artefact `infrastructure`)

- **Statut** : esquisse (phase 0, 2026-11-05) ; finalisation juste avant la construction de la couche (phase(s) 9 et 10), puis gel par `mcl.py figer`.
- **Consommateurs cartographiés** : couches 1b
- **Dépend de** : couches aucune (réelles et figées) ; amont figé : amont-service-ia ; frontières externes doublées : reseau
- **Module** : `src/xpbots/infrastructure/http`
- **Sources normatives** : C04, C08 (rapprochement, redémarrage), A04, A08, A10 ; plan maître, section 7.I

---

Unité : transport_http
Responsabilité : Envoyer des requêtes HTTPS bornées.
Signature : TransportHTTP.envoyer(requete) -> Reponse
Entrée : requête HTTPS, délai, taille maximale
Sortie : réponse ou erreur typée
Effets de bord : aucun
Erreurs, exceptions : DelaiDepasse ; ReponseTropGrande ; RedirectionRefusee

---

## Spécification exécutable

- Catégorie 1 (`tests/robot/infrastructure/test_c0d_cat1_*.py`) : HTTPS seul, délais, taille maximale, redirections bornées.
- Catégorie 2 (`tests/robot/infrastructure/test_c0d_cat2_*.py`) : transport factice.

## Comportements documentés (loi de Hyrum)

Les consommateurs ne codent que contre ce qui est écrit ici. Les observables non documentés (ordre d'itération, texte exact des messages) ne sont pas garantis. Toute valeur normative est lue dans `config/`, jamais recopiée.
