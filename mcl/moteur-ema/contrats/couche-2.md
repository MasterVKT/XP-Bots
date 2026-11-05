# Contrat de la couche 2 — machine-etats (artefact `moteur-ema`)

- **Statut** : esquisse (phase 0, 2026-11-05) ; finalisation juste avant la construction de la couche (phase(s) 3), puis gel par `mcl.py figer`.
- **Consommateurs cartographiés** : couches 3
- **Dépend de** : couches 1a, 1b, 1c (réelles et figées) ; amont figé : amont-noyau ; frontières externes doublées : aucune
- **Module** : `src/xpbots/moteur_ema/c2_machine_etats.py`
- **Sources normatives** : S01.1 à S01.6, C03.8–C03.11, C06 (conversion), A07 ; plan maître, section 7.B

---

Unité : machine_etats_ema
Responsabilité : Gérer armement, contact, repli de 1 à 8 bougies, cooldown, position possédée et compteur journalier par symbole.
Signature : MachineEtatsEMA.etape(bougie_enrichie) -> Transition ; appliquer_issue(issue) ; notifier_sortie(instant) ; exporter_etat() ; importer_etat(etat)
Entrée : BougieEnrichie au statut OK ; issues ; instants de sortie
Sortie : état (IDLE, ARMED_*, PULLBACK_*, COOLDOWN, OWNED_POSITION) et événement AUCUN ou REPRISE(sens, extrêmes, âge)
Effets de bord : état interne exportable
Erreurs, exceptions : IssueInattendue si une issue arrive sans signal en attente

---

## Spécification exécutable

- Catégorie 1 (`tests/robot/moteur_ema/test_c2_cat1_*.py`) : transitions T1 à T12 une par une (plan maître 7.B), R1, R2.
- Catégorie 2 (`tests/robot/moteur_ema/test_c2_cat2_*.py`) : équivalence avec reference.technical.ema_setups sur séries synthétiques.

## Comportements documentés (loi de Hyrum)

Les consommateurs ne codent que contre ce qui est écrit ici. Les observables non documentés (ordre d'itération, texte exact des messages) ne sont pas garantis. Toute valeur normative est lue dans `config/`, jamais recopiée.
