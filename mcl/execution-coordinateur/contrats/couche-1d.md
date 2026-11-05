# Contrat de la couche 1d — registre-reservations (artefact `execution-coordinateur`)

- **Statut** : esquisse (phase 0, 2026-11-05) ; finalisation juste avant la construction de la couche (phase(s) 4 et 5), puis gel par `mcl.py figer`.
- **Consommateurs cartographiés** : couches 2b, 3
- **Dépend de** : couches 0 (réelles et figées) ; amont figé : aucun ; frontières externes doublées : stockage-etat
- **Module** : `src/xpbots/execution/c1d_reservations.py`
- **Sources normatives** : C04, C06, C07, C08, C09, C11.2, C11.5–C11.7, C11.10–C11.13 ; plan maître, section 7.D

---

Unité : registre_reservations
Responsabilité : Réserver et libérer le risque initial de façon atomique et persistante par clé d'intention.
Signature : Registre.reserver(cle, risque, symbole) -> Reservation | Existante ; liberer(cle) ; total() ; occupation()
Entrée : clé d'intention C08, risque Decimal, symbole canonique
Sortie : réservation unique par clé ; totaux et occupation par symbole
Effets de bord : transaction de stockage
Erreurs, exceptions : aucune

---

## Spécification exécutable

- Catégorie 1 (`tests/robot/execution/test_c1d_cat1_*.py`) : réservation atomique avant envoi, idempotence par clé, libération à la clôture seulement.
- Catégorie 2 (`tests/robot/execution/test_c1d_cat2_*.py`) : via 3.

## Comportements documentés (loi de Hyrum)

Les consommateurs ne codent que contre ce qui est écrit ici. Les observables non documentés (ordre d'itération, texte exact des messages) ne sont pas garantis. Toute valeur normative est lue dans `config/`, jamais recopiée.
