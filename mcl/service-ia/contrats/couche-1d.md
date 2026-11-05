# Contrat de la couche 1d — budget (artefact `service-ia`)

- **Statut** : esquisse (phase 0, 2026-11-05) ; finalisation juste avant la construction de la couche (phase(s) 10), puis gel par `mcl.py figer`.
- **Consommateurs cartographiés** : couches 2b
- **Dépend de** : couches 0 (réelles et figées) ; amont figé : aucun ; frontières externes doublées : stockage-ia
- **Module** : `src/xpbots/service_ia/c1d_budget.py`
- **Sources normatives** : A02, A04 à A11, A14 ; plan maître, section 7.G

---

Unité : registre_budget
Responsabilité : Réserver et rapprocher coûts, tentatives et tokens de façon transactionnelle.
Signature : Budget.reserver(route, borne) -> Reservation | Refus ; rapprocher(...)
Entrée : route, bornes de tokens et de coût
Sortie : réservation Decimal ou refus
Effets de bord : transaction exclusive
Erreurs, exceptions : aucune

---

## Spécification exécutable

- Catégorie 1 (`tests/robot/service_ia/test_c1d_cat1_*.py`) : 24, 18, 150 000, 3 USD, 15 USD aux bornes ; coût inconnu conservé ; Gemini payant jamais gratuit.
- Catégorie 2 (`tests/robot/service_ia/test_c1d_cat2_*.py`) : concurrence via 0e.

## Comportements documentés (loi de Hyrum)

Les consommateurs ne codent que contre ce qui est écrit ici. Les observables non documentés (ordre d'itération, texte exact des messages) ne sont pas garantis. Toute valeur normative est lue dans `config/`, jamais recopiée.
