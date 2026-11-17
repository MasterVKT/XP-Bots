# P11-20 — horodatage UTC des ticks du SDK

Le contrôle de sortie a révélé une erreur du contrat de frontière du document 08,
puis de sa composition en 3 : une même table était imposée au flux SDK et aux
exports MQL5 sans choix de convention par source. Les
fonctions Python `copy_ticks_from` et `copy_ticks_range` demandent des dates UTC
et rendent des ticks UTC, sans décalage du serveur :
[référence from](https://www.mql5.com/en/docs/python_metatrader5/mt5copyticksfrom_py),
[référence range](https://www.mql5.com/en/docs/python_metatrader5/mt5copyticksrange_py).
`symbol_info_tick` rend le dernier tick de ce même flux. Le plan S-01 prévoit
cependant explicitement de qualifier la base horaire sur le poste, les sources
du forum étant contradictoires. Cette qualification est conservée : la table
D12 seule ne permet pas de déduire la convention des ticks SDK.

La sonde avant correction injecte un tick SDK UTC à 09:00 avec une table D12
serveur à +1 h. L'ancien lecteur interroge 10:00 et rend un lot vide déclaré à
jour, alors que le tick de 09:00 existe. Une conversion identique de la cotation
de défense la vieillit artificiellement et peut empêcher une clôture prioritaire.
La preuve RED est conservée sous `.local/reports/phase11_p20_ticks_utc_avant.json`.
Aucun terminal ni SDK réel n'a été appelé.

Les défigeages correctifs de 2b et 2d, puis les extensions de 2a et 3 sont tracés
avant leurs changements de contrat. Il s'agit de rétablir l'invariant C03 de
temps fournisseur UTC et la fraîcheur C06 tout en conservant S-01. Aucun seuil
ou comportement de stratégie n'est modifié.

La preuve C04 exige désormais `convention_ticks=UTC` ou `SERVEUR_S01`, sous ses
bornes de connaissance et de validité ; un choix absent ou inconnu refuse.
Le courtier lit le choix validé par l'API 2a et le fournit aux deux adaptateurs.
UTC conserve les epochs SDK dans recherches, curseurs, préfixes et couvertures ;
SERVEUR_S01 applique la table qualifiée comme auparavant. Les API autonomes
gardent ce dernier défaut pour leurs appelants déjà munis d'une table S01 de
leur source. La composition de production ne remplace jamais un choix manquant
par ce défaut. Le choix engage les signatures de reprise, sans migration
silencieuse. Les formats publics d'état, lots pleins et multiplicités restent
inchangés. 2d emploie la même convention pour le dernier tick de clôture et
conserve les gardes de fraîcheur.

La table serveur demeure nécessaire pour les textes et séances MQL5 D12, et les
faits de compte/transactions dont la conversion relève de S01/S08. Cette
correction n'invente pas leur sémantique : leur confrontation au poste reste
requise en 13.1. Aucun offset ou changement de convention n'est inféré pour
rendre une donnée acceptable. Un changement requiert une nouvelle preuve et
ne permet pas de reprendre l'ancien curseur sous une autre interprétation.

Rayon : 2b/2d → courtier 3 → assemblage 4 → direct 2 et principal 3. Les nouveaux
tests emploient des tables D12 non nulles, les vrais lecteurs et transport, le
faux SDK, des dossiers temporaires et les contrôles réels. Les consommateurs
inchangés sont revalidés par la régression complète après chaque gel, puis par
un nouveau gate global et checkpoint. Les mutations restent suspendues jusque-là.
