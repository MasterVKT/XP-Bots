# Contrat de la couche 1b — tokens (artefact `service-ia`)

- **Statut** : esquisse (phase 0, 2026-11-05) ; finalisation juste avant la construction de la couche (phase(s) 10), puis gel par `mcl.py figer`.
- **Consommateurs cartographiés** : couches 2b
- **Dépend de** : couches 0 (réelles et figées) ; amont figé : aucun ; frontières externes doublées : aucune
- **Module** : `src/xpbots/service_ia/c1b_tokens.py`
- **Sources normatives** : A02, A04 à A11, A14 ; plan maître, section 7.G

---

Unité : borne_tokens
Responsabilité : Calculer la borne conservatrice de tokens d'une requête.
Signature : borne_entree(corps_sans_secret) -> int
Entrée : corps sérialisé
Sortie : borne ≤ 4 096 ou refus
Effets de bord : aucun
Erreurs, exceptions : aucune

---

## Spécification exécutable

- Catégorie 1 (`tests/robot/service_ia/test_c1b_cat1_*.py`) : borne octets + 512 ≤ 4 096 ; raccourcissement sans perte de négation.
- Catégorie 2 (`tests/robot/service_ia/test_c1b_cat2_*.py`) : via 2b.

## Comportements documentés (loi de Hyrum)

Les consommateurs ne codent que contre ce qui est écrit ici. Les observables non documentés (ordre d'itération, texte exact des messages) ne sont pas garantis. Toute valeur normative est lue dans `config/`, jamais recopiée.
