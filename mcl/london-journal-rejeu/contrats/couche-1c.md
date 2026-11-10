# Couche 1c — mesures C09/C10 et coûts A13

Unité : metriques ; dépendances 0a/0b et noyau figés. Calculs purs Decimal à la
précision de 0a. ComptageC09(configurations, signaux, refus, entrees, entrees_jours) distingue les
configurations techniques potentielles, signaux en état négociable, refus par
motif et entrées réellement remplies. calculer_mesures(trades, courbe, jours,
comptage, factures=(), methode=None) rend un BilanMesures immuable, avec les sept
mesures C09 séparées : les quatre précédentes, positions closes, résultats nets
et drawdown des fonds propres. Un trade n'est pas un signal ou une configuration.

Résultat courtier = somme des Trade.net ; espérance = somme/nombre de trades
clos ; entrees_jours dénombre les premiers remplissages par date Londres, y
compris ceux encore ouverts, avec somme égale à entrees. profit factor = gains/abs(pertes), None avec statut SANS_PERTE si aucune
perte. Taux de réussite = nombre de nets strictement positifs/nombre clos et R
moyen = moyenne des r_net. Sans trade, espérance et descriptions sont None.
Drawdown = maximum (pic - fonds propres)/pic à partir de la courbe chronologique,
flottant et frais inclus ; la courbe ne se remplace jamais par le solde.
Fréquence = entrées/jours fournis, jours à zéro inclus. Une référence absente ou
nulle donne rétention None/N_A ; une référence sous le seuil min_reference de
0b donne le ratio numérique mais statut TROP_FAIBLE ; sinon EXPLOITABLE. Le ratio
de configurations est exposé séparément par la même fonction retention.

reconcilier_factures déduplique des factures originales identiques par référence,
rejette une même référence réécrite, alloue chaque dépense une seule fois entre
les méthodes consommatrices et conserve RECHERCHE dans le bilan global. La courbe
économique soustrait ces factures à leurs instants de connaissance ; la courbe
native reste distincte. Les deux drawdowns et deux résultats sont exposés ; les
coûts ne sont pas soustraits une seconde fois des trades. Les coûts non réels ne
constituent pas une preuve de consommation IA réelle.

panel_journalier(trades, jours, commun, factures=(), methode=None) inclut chaque jour du
panel, même à zéro, affecte P&L et nombre clos au jour Londres de sortie et coût
IA au jour de sa facture. Un jour de sortie/facture absent du panel est une
erreur, jamais une suppression favorable. Les périodes ne sont pas fusionnées.
commun fournit le fuseau chargé. ventiler_trades(trades, commun) expose méthode, symbole, heure Londres d'entrée, jour de semaine
et sens avec effectifs, P&L, réussite et R moyen, sans nouveau critère de décision.

ErreurRejeu sur chronologie, panel ou comptage incohérent, duplication de clés de
jours et coût réécrit. Tests propres : panel calculé à la main, jours à zéro,
PF sans perte, flottant défavorable, rétention trois statuts, frais sans réserve,
facture partagée/doublonnée et coût à un instant sans tick. Jonctions : vrais
Trade/PointCompte/FactureIA, seuils du protocole chargé, dates Londres en été/hiver.
