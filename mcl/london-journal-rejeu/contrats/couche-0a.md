# Couche 0a — types

Statut : finalisé avant source. Consommateurs : 1a, 1b, 1c, 1d, 2 et 3.
Dépend de : types canoniques du noyau figé ; aucune autre unité du composant.

Unité : types_rejeu. Responsabilité : valeurs immuables de données et résultats.
Signatures publiques : ErreurRejeu(ValueError), instant, entier, texte, montant,
TarifCommission, ConditionContrat,
ManifesteTicks, Trade, PointCompte, JourMarche, ValeurJour, FactureIA et EcartRejeu.
Les instants sont des entiers UTC en ms ; bool n’est pas un entier. Les montants
sont des Decimal finis, avec positivité selon leur rôle. Les collections sont
copiées en tuples et mappings non modifiables. Aucun effet de bord.

TarifCommission(identifiant, entree_par_lot, minimum_entree, sortie_par_lot,
minimum_sortie) reçoit quatre coûts non négatifs explicitement connus. entree(v)
et sortie(v) rendent max(minimum, par_lot×volume), sans arrondi caché. Le volume
est strictement positif. ConditionContrat(debut_ms, fin_ms, connu_ms, profil,
tarif) exige un intervalle non vide, un ProfilInstrument et ce tarif réel. La
condition n’est exploitable que si date d’effet et date de connaissance le permettent.

ManifesteTicks(source, symboles, intervalle, couverture, trous, sha256,
date_recuperation, extraction, precision_prix, horaires, *, sequence_origine=
'NATIVE', resolution_ms=1, fuseau_original='UTC', conversion_utc_qualifiee=True,
usage='FIXTURE_SYNTHETIQUE') décrit les lignes exactes à analyser. symboles relie
chaque nom canonique à un unique nom courtier ; horaires porte les mêmes clés.
L’empreinte est SHA-256 minuscule. Couverture et trous sont des intervalles triés,
non chevauchants et contenus dans l’intervalle source ; ils ne se recouvrent pas.
Une milliseconde est requise ; ordre natif ou ordre original absent déclaré.
Les usages sont FIXTURE_SYNTHETIQUE, COURTIER_HISTORIQUE, TIERS_CONTREFACTUEL.
Une conversion UTC non qualifiée est refusée, jamais devinée.

Trade(cle, entree_ms, sortie_ms, volume, prix_entree, prix_sortie, profit_brut,
frais_entree, frais_sortie, risque_initial, cause, contexte={}) décrit une position
complètement close. La clé et la cause sont canoniques ; sortie≥entrée≥clôture
du signal ; volume, prix et risque initial sont strictement positifs. net vaut
profit_brut−frais_entree−frais_sortie, R net vaut net/risque_initial. Le contexte
est figé récursivement. Aucune réserve de dimensionnement n’est retranchée ici.

PointCompte(instant_ms, fonds_propres, solde, marge_utilisee) conserve le flottant
dans les fonds propres ; fonds propres et solde peuvent devenir négatifs après
un gap, la marge est non négative. JourMarche(jour, periode) porte une journée
qualifiée en amont ; ValeurJour(jour, periode, pnl_net, trades_clos) accepte les
jours à zéro et garde la période continue distincte pour le bootstrap.

FactureIA(reference, instant_ms, montant_usd, methodes, nature, reelle=True)
exige des méthodes uniques et un montant non négatif. Les natures sont EVENEMENT,
BRIEFING, JOURNAL, RECHERCHE. allocation() répartit exactement le montant entre
les méthodes consommatrices ; le total ne change pas. La déduplication et le
rapprochement des factures appartiennent aux consommateurs. Les dépenses IA sont
un poste économique distinct des frais natifs ; aucun débit implicite du courtier.

EcartRejeu(nom, champ, valeur) porte un diagnostic explicite : OBJECTIF ou BUFFER
avec coefficient Decimal positif, DUREE avec secondes entières positives. Le
consommateur vérifie l’appartenance aux six écarts prescrits et l’usage en rejeu.

Erreurs : ErreurRejeu sur type, nombre non fini, booléen interdit, chronologie,
intervalle, doublon ou donnée incohérente. Catégorie 1 : constructions valides,
bornes et refus, immutabilité profonde, commissions minimales, net sans réserve,
allocations exactes et provenance. Pas de catégorie 2 entre nouvelles couches.
