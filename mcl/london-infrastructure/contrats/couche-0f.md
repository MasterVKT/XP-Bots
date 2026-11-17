# Couche 0f — fichiers mensuels de ticks
Statut : finalisé le 10/11/2026 avant code. Frontières réelles : fichiers, gzip.
LectureTicks(chemin).lignes() -> itérateur de lignes texte UTF8, fins de ligne
exactes conservées ; sha256_fichier et sha256_contenu disponibles après épuisement.
Lecture binaire par blocs, gzip en flux sans charger le fichier compressé entier.
Le SHA fichier porte les octets compressés exacts ; SHA contenu porte les octets
décompressés exacts. Aucun tri, interpolation, conversion Bid/Ask ou heure.
Le consommateur confronte les deux niveaux au manifeste puis appelle le lecteur
pur de phase 10 avant toute décision. Une lecture inachevée n’est pas qualifiée.
Contexte with/fermer ferme immédiatement tous les descripteurs, même après erreur.
Le fichier doit finir .csv.gz ; la clôture vérifie le flux gzip et sa CRC.
Erreur : ValueError contrat, UnicodeError, gzip.BadGzipFile/OSError source.
Tests : SHA exacts, streaming et CRLF préservés, CRC/troncature, arrêt anticipé.
