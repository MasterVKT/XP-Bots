# Contrat de la couche 0a — fichiers-et-horloge (artefact `infrastructure`)

- **Statut** : esquisse (phase 0, 2026-11-05) ; finalisation juste avant la construction de la couche (phase(s) 9 et 10), puis gel par `mcl.py figer`.
- **Consommateurs cartographiés** : aucune couche interne
- **Dépend de** : couches aucune (réelles et figées) ; amont figé : amont-contexte-ia, amont-fondamental, amont-journal-rejeu, amont-noyau ; frontières externes doublées : horloge-os, systeme-fichiers
- **Module** : `src/xpbots/infrastructure/fichiers`
- **Sources normatives** : C04, C08 (rapprochement, redémarrage), A04, A08, A10 ; plan maître, section 7.I

---

Unité : horloge_systeme
Responsabilité : Fournir l'instant UTC en millisecondes du système.
Signature : HorlogeSysteme (port Horloge).maintenant() -> Instant
Entrée : —
Sortie : instant UTC ms
Effets de bord : aucun
Erreurs, exceptions : aucune

---

Unité : journal_fichier
Responsabilité : Écrire le journal C09 en JSONL par ajout avec fsync.
Signature : JournalFichier (port Journal).ajouter(ligne)
Entrée : lignes canoniques
Sortie : fichier en ajout seul
Effets de bord : écriture disque
Erreurs, exceptions : aucune

---

Unité : ipc_snapshot_fichier
Responsabilité : Lire le fichier de snapshot IA et le fermer immédiatement.
Signature : LecteurSnapshotFichier.lire() -> bytes | None
Entrée : chemin commondata ou XPBOTS_COMMON_FILES_DIR
Sortie : octets ≤ 32 Kio ou absence
Effets de bord : aucun
Erreurs, exceptions : aucune

---

Unité : ticks_historiques_fichiers
Responsabilité : Lire les fichiers de ticks historiques et leur manifeste.
Signature : SourceTicksFichiers.ouvrir(chemin) -> Iterable[ligne]
Entrée : CSV/CSV.gz du cahier de données
Sortie : lignes brutes et empreintes
Effets de bord : aucun
Erreurs, exceptions : aucune

---

Unité : sources_fondamentales_fichiers
Responsabilité : Lire les permissions et calendriers déposés par le module fondamental (R12, R13).
Signature : SourcePermissionsFichiers ; SourceCalendrierFichiers
Entrée : dossiers configurés
Sortie : messages et versions avec heure de réception
Effets de bord : aucun
Erreurs, exceptions : aucune

---

## Spécification exécutable

- Catégorie 1 (`tests/robot/infrastructure/test_c0a_cat1_*.py`) : remplacement atomique, fsync, fermeture immédiate, horloge UTC ms.
- Catégorie 2 (`tests/robot/infrastructure/test_c0a_cat2_*.py`) : contrats de port communs.

## Comportements documentés (loi de Hyrum)

Les consommateurs ne codent que contre ce qui est écrit ici. Les observables non documentés (ordre d'itération, texte exact des messages) ne sont pas garantis. Toute valeur normative est lue dans `config/`, jamais recopiée.
