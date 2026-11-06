# Contrat de la couche 2 — journal (enveloppe du noyau)

- **Statut** : finalisé le 05/11/2026 (figé par `mcl.py figer` après gate vert)
- **Consommateurs cartographiés** : squelette (enchaînement minimal, segment S6) ; plus tard `orchestration`,
  `execution-coordinateur` (enregistrements d'intention), `infrastructure` (écriture) et `journal-rejeu`
  (relecture, C11.14)
- **Dépend de** : couches 0a (`instant`), 0c (`configuration`), 1a (`marche`), 1b (`instrument`), 1c (`domaine`),
  réelles et figées ; aucune frontière externe (aucune écriture). La dépendance vers 0a, omise à la première
  finalisation, est rétablie par le défigeage « correction » du 05/11/2026 (journal MCL)

---

Unité : journal
Responsabilité : Définir les enregistrements C09 et leur sérialisation canonique.
Signature : `VERSION_SCHEMA = 'xp-journal-v1'` ; `TypeEnregistrement` (`CLOTURE`, `INTENTION`, `ORDRE`,
`REPONSE`, `EXECUTION`, `PROTECTION`, `CLOTURE_POSITION`, `COMPTE`, `ALERTE`, `DEMARRAGE`, `ARRET`,
`RAPPROCHEMENT`) ; `MODES`, `BRAS` ; `CHAMPS_OBLIGATOIRES: Mapping[TypeEnregistrement, frozenset[str]]` ;
`empreintes_regles(configuration: ConfigurationFigee) -> Mapping[str, str]` ;
`Enveloppe(deploiement, bras, mode, numero, instant_utc_ms, empreinte_regles)` ;
`Enregistrement(type, enveloppe, contenu)` avec `vers_dict() -> dict` ;
`enregistrement(type_, enveloppe, contenu) -> Enregistrement` ;
`enregistrement_cloture(enveloppe, *, bougie, resultat, profil, indicateurs, etat_strategie, permission, version_calendrier, snapshot_ia) -> Enregistrement` ;
`enregistrement_intention(enveloppe, *, cle, longueur_empreinte, tentatives, issue, cout_ia_usd, details=None) -> Enregistrement` ;
`serialiser(enregistrement) -> str` ; `ErreurJournal(ValueError)`.
Entrée : enveloppe : déploiement non vide, bras `REFERENCE` ou `IA`, mode `REJEU`, `PAPER`, `PAPER_AB`, `DEMO` ou
`REEL`, numéro entier ≥ 1, instant UTC (0a), empreintes `{technique, ia}` de 64 caractères hexadécimaux ;
contenu : correspondance à clés textuelles, sans clé réservée à l'enveloppe, valeurs JSON, décimaux, énumérations
textuelles, tuples ou correspondances figées ; bougie (1a), résultat technique (1c), profil d'instrument (1b) ou
`None`, issue (1c).
Sortie : `Enregistrement` immuable. `CHAMPS_OBLIGATOIRES` exige pour `CLOTURE` : `strategie`, `symbole`,
`instrument`, `bougie`, `indicateurs`, `etat_strategie`, `signal`, `motif`, `detail`, `permission`,
`version_calendrier`, `snapshot_ia` ; pour `INTENTION` : `cle`, `empreinte_cle`, `strategie`, `symbole`, `sens`,
`tentatives`, `issue`, `motif`, `detail`, `cout_ia_usd` ; aucun champ propre pour les autres types. Un `motif`
non nul est contrôlé avec son `detail` par `verifier_motif` (1c). `vers_dict` fusionne `type`,
`version_schema`, l'enveloppe et le contenu. `serialiser` rend une ligne JSON : clés triées, séparateurs `,` et
`:` sans espace, UTF-8 non échappé, aucun nombre non fini, décimaux en texte sans exposant (`0.00010`),
énumérations par leur valeur, tuples en listes ; `json.loads` puis re-sérialisation rend la même ligne.
Effets de bord : aucun ; aucune écriture.
Erreurs, exceptions : `ErreurJournal` pour une enveloppe invalide, un champ obligatoire absent, une clé réservée
dans le contenu, un motif ou un détail refusés, une incohérence (symbole ou clôture différents entre bougie,
résultat et profil ; issue d'une autre intention), une valeur non sérialisable.

---

## Spécification exécutable

`tests/robot/noyau/test_cat1_c2_journal.py` et `tests/robot/noyau/test_cat2_c2_journal.py`.

## Comportements documentés (loi de Hyrum)

Le nom des clés du contenu est celui de ce contrat ; les champs ajoutés par un appelant dans `contenu` sont
conservés. Le texte des messages d'erreur n'est pas garanti.
