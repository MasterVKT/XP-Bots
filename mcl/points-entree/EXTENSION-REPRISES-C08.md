# P11-17 — conserver les reprises dans le journal d'incident

Le test de boucle native synthétique atteint un vrai signal London, les deux
COMMIT et le faux SDK. Un TIMEOUT conserve l'intention inconnue et la reprise
ne la renvoie pas. Le rapport d'incident après cette reprise échoue toutefois
par REJEU_INCIDENT_DIVERGENT : le constructeur C08 a modifié l'état courant,
mais aucune entrée n'indique où refaire cette transformation.

Les extensions additives formelles de 1b et 1f enregistrent et vérifient un
marqueur de checkpoint court au préfixe concerné. Le rejeu repasse par les vrais
constructeurs C08 ; il compare le résultat au marqueur, sans injecter son état.
Le journal conserve les anciennes entrées, calculs et C09. Le snapshot régulier
reste incrémental. Aucun contrat de l'orchestration ou du coordinateur ne change.

Le cas C11.14 natif est conservé comme sonde rouge pendant la construction des
deux supports parallèles. Son assertion finale sera réintégrée à la catégorie 2
de la boucle après leurs gels et le raccordement de 1e/2, avant le gate de 2.
Le double COMMIT et le refus de renvoi restent dans la suite active. Les preuves
de travail sont phase11_c2_pannes_natif.log et la copie de la sonde sous .local.
La phase 11 demeure incomplète tant que cette jonction n'est pas verte.

Après les gels des deux supports (1 380 tests, 14 contrats physiques différés),
le raccordement 1e/2 réintègre l'assertion native : le rapport après TIMEOUT et
redémarrage est IDENTIQUE. Retirer le marqueur de cette archive provoque bien
REJEU_INCIDENT_DIVERGENT. Deux reprises A/B successives passent aussi sur les
vrais journaux et livres. Les sources 1e/2 restent en attente de leurs gates ;
ces résultats ciblés ne valent pas encore gel de l'enveloppe.
