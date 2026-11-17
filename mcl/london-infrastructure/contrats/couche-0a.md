# Couche 0a — types et conversion qualifiée
Statut : finalisé le 10/11/2026 avant code. Frontière : structures SDK injectées.
Signatures : SegmentServeur(debut_utc_ms,fin_utc_ms,decalage_secondes),
TableHeureServeur(serveur,version,date_releve,mesures,segments),
TableHeureServeur.utc_de_serveur(ms), serveur_de_utc(ms), depuis_document(document).
ProtocoleMT5 décrit les appels utilisés sans importer le paquet. ErreurInfra et
ErreurNative(code) sont ValueError ; jamais de message natif ni identifiant au journal.
Entiers stricts (bool refusé), bornes UTC vérifiées, segments UTC triés sans
chevauchement, couverture non vide, serveur/version/date/mesures explicites.
La conversion cherche exactement un segment compatible ; zéro ou deux candidats
sont ENVIRONMENT_NOT_READY. Aucun offset déduit de l’horloge courante.
nombre_decimal accepte les scalaires natifs finis, entier_natif utilise index et
refuse bool ; champ_natif accepte attributs nommés et lignes NumPy structurées.
Tests : frontières et DST ambigu/hors couverture, précision et scalaires NumPy.

Correction tracee du 10/11/2026 : sur une ligne structuree, un nom present dans dtype.names designe le champ, meme si NumPy expose aussi un attribut Python homonyme (flags, size, dtype). Les namedtuples natifs gardent leur lecture par attribut. Aucune importation NumPy dans le code de production.
