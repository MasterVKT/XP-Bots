# Couche 1a — validation des ticks

Unité : analyse_ticks. Dépendance : 0a et noyau figés. Aucune frontière physique.
analyser_lignes_ticks(lignes, manifeste) reçoit des lignes UTF-8 conservant leurs
fins de ligne et un ManifesteTicks. Il calcule le SHA-256 de leur concaténation
exacte et valide tout le lot avant de rendre HistoriqueTicks(ticks, manifeste).
Ce résultat immuable est itérable ; aucun préfixe utilisable ne sort d'un lot dont
la fin ou l'empreinte est invalide. Une unité de collecte bornée peut être fournie
par lot ; aucun fichier ni prix manquant ne sont créés par cette couche.

L'en-tête est canonical_symbol,broker_symbol,time_utc_ms,sequence,bid,ask.
Les six colonnes sont obligatoires. Les symboles correspondent exactement au
manifeste ; les entiers sont ASCII, sans signe, et les instants appartiennent à
l'intervalle et à une période couverte, jamais à un trou. La clé globale
(instant, séquence) est strictement croissante, sans tri correctif. La séquence
native est exigée ; en mode ORDRE_ORIGINAL, seul un champ vide est remplacé par
l'indice ordinal original de la ligne. Aucune séquence n'est reconstruite depuis
les prix. Bid et Ask sont finis, positifs et Ask >= Bid ; une conversion vers le
Tick canonique qui perdrait une décimale significative est refusée. L'heure de
réception du rejeu est l'heure fournisseur, convention P-04.

jours_marche(manifeste, periode, fenetres, commun) rend des JourMarche dans
l'ordre Londres. fenetres associe les seuls symboles Forex du dénominateur à leurs
fenêtres locales d'entrée, transmises depuis la configuration. commun fournit le
fuseau et les jours ouvrés de la configuration chargée. Un jour ouvré est
retenu si une séance native d'au moins un symbole recoupe sa fenêtre, après
soustraction des fermetures déclarées. Les jours sans tick et les trous de
collecte restent au dénominateur ; des horaires non qualifiés pour la fenêtre
font échouer le calcul. Zone Europe/London, jamais de décalage UTC constant.

ErreurRejeu signale format, intégrité, ordre, provenance ou horaire insuffisant.
Tests propres : CRC/SHA, fin invalide sans préfixe, séquences égales et recul,
millisecondes, prix, symboles et trous. Jonctions : types et Tick réels, jours à
zéro et changement d'heure Londres, registre conservé sans interpolation.
