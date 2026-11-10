# Couche 1d — bootstrap apparié par journées

Unité : bootstrap ; dépendances 0a/0b et noyau figés. Aucun prix ni simulateur.
indices_bootstrap(jours, parametres) utilise exclusivement random.Random(graine).
jours est un panel chronologique unique de JourMarche. Tous les blocs contigus
de bloc_jours journées sont construits dans chaque période continue, sans passer
une frontière de période. Chaque réplication tire avec remise ceil(n/bloc_jours)
blocs, concatène leurs indices puis tronque à n. Un panel sans bloc complet est
refusé, pas remplacé par un bootstrap individuel. L'index est commun aux séries
appariées ; les méthodes et symboles sont regroupés dans le panel d'entrée.

bootstrap_apparie(reference, candidat, parametres, capital_initial) reçoit deux
tuples de ValeurJour sur exactement les mêmes jours/périodes. Il rend les
distributions d'espérance du candidat et de différence candidat-référence, gain
net incrémental et différence de drawdown des courbes journalières reconstruites
depuis le même capital. P&L et trades sont rééchantillonnés ensemble ; aucune
ligne de prix n'est recollée. Une réplication sans trade candidat invalide son
espérance ; sans trade dans un des bras elle invalide la différence d'espérance.
Les nombres de réplications invalides sont distincts et explicites.

percentile(valeurs, pourcentage) trie une copie et interpole linéairement à
l'indice (n-1)*pourcentage/100. Les bornes lues de 0b sont rendues avec chaque
distribution et None si aucune réplication valide. Paramètres, graine, nombre de
jours et indices sont reproductibles. Aucune conclusion financière n'est prise
par cette couche : le rapport exige séparément les preuves réservées et réelles.

ErreurRejeu sur panel non apparié, ordre ou période répétée après interruption,
paramètres invalides et capital non positif. Tests propres : tous les blocs sur
un petit panel, tirage calculé indépendamment à la main, troncature, remise,
frontières, graine reproductible, percentiles connus, invalides et drawdowns.
Jonctions : jours et valeurs 0a réels, paramètres 0b réellement chargés, panel
commun incluant les jours à zéro ; aucun hasard hors de cette couche.
