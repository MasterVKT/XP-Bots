# Contrat de la couche 0c — configuration

- **Statut** : finalisé le 05/11/2026 (figé par `mcl.py figer` après gate vert)
- **Consommateurs cartographiés** : couches 1b (`instrument` : compte attendu, univers) et 2 (`journal` :
  empreintes des règles) ; plus tard tous les artefacts, qui lisent leurs paramètres ici
- **Dépend de** : aucune couche ; aucune frontière externe (les octets sont fournis par la coquille)

---

Unité : configuration
Responsabilité : Valider les octets des deux exports figés et exposer des paramètres typés immuables.
Signature : `charger_configuration_figee(octets_technique: bytes, octets_ia: bytes, octets_preuve: bytes) -> ConfigurationFigee` ;
`analyser_export_technique(octets: bytes) -> ExportTechnique` ; `analyser_export_ia(octets: bytes) -> ExportIA` ;
`ParametresCommuns` (73 champs nommés comme les clés de `common`) ; `CLES_COMMUNES` (tuple de ces 73 noms,
dans l'ordre de l'export) ; `ExportTechnique`, `ExportIA`, `ConfigurationFigee` ; `ErreurConfiguration(ValueError)`.
Entrée : octets UTF-8 de `config/parametres_figes_v3.json`, de `config/parametres_IA_integration_v1.json` et de
`docs/validation/conservation_ressources.json` (schéma `xp-bots-resource-preservation-v1`).
Sortie : `ConfigurationFigee(technique, ia)` immuable ; `ExportTechnique(commun, london, ema, empreinte_octets,
empreinte_canonique)` où `commun` est typé clé par clé (entiers, nombres, fractions dans ]0, 1], heures
`datetime.time`, date, tuples, dictionnaire figé des plafonds de spread) et `london`, `ema` sont des
correspondances figées (listes en tuples), typées par leurs artefacts ; `ExportIA(parametres, empreinte_octets,
empreinte_canonique)`. Empreinte des octets : SHA-256 ; empreinte canonique : SHA-256 de la forme JSON à clés
triées, séparateurs `,` et `:`, UTF-8 (égale au `design_sha256` du diagnostic pour l'export technique).
`analyser_*` valide sans comparer à la preuve (tests de non-recopie) ; `charger_configuration_figee` exige en
plus l'égalité des empreintes d'octets avec `frozen_technical_file_sha256` et `frozen_ai_file_sha256`.
Effets de bord : aucun.
Erreurs, exceptions : `ErreurConfiguration` pour des octets non UTF-8 ou précédés d'un BOM, un JSON invalide, une
clé dupliquée, un nombre non fini, une racine autre que `common`, `ema`, `london`, une clé de `common` inconnue
ou manquante, un type ou une borne non respectés, une valeur non prise en charge (`bar_price` ≠ `BID`,
`bar_alignment` ≠ `UTC`, `atr_method` ≠ `WILDER`, `atr_signal_reference` ≠ `PREVIOUS_CLOSED_M15`,
`fundamental_mode` ≠ `EXTERNAL_REQUIRED`, `risk_day_timezone` ≠ `UTC`, toute option `allow_*`, `*_enabled`,
`mandatory_retest` ou `new_indicator_vote_score` à vrai, `local_inference_allowed` ou
`synchronous_llm_on_entry_allowed` à vrai), une incohérence interne (`h1_seconds` non multiple de
`timeframe_seconds`, plafonds de spread ne couvrant pas exactement l'univers, stop maximal inférieur au
minimal, identifiant de stratégie absent de `simultaneous_strategy_priority`), une empreinte différente de la
preuve.

---

## Spécification exécutable

`tests/robot/noyau/test_cat1_c0c_configuration.py` (profondeur 0 : pas de catégorie 2).

## Comportements documentés (loi de Hyrum)

Les nombres gardent le type JSON lu (`int` ou `float`) ; la conversion décimale se fait chez le consommateur par
`nombres.decimal_depuis`. Les messages d'erreur nomment la clé fautive ; leur texte exact n'est pas garanti.
