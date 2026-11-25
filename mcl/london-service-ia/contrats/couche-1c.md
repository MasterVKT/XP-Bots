# Couche 1c — normalisation des flux officiels

Statut : contrat finalisé le 17/11/2026 après gel de 0 et avant code.
Consommateurs cartographiés : collecteur 2c.
Dépend de : types 0 ; aucune autre unité de niveau 1.

Unité : normalisation.
Responsabilité : transformer un flux officiel borné en documents immuables, sans renouveler leur première connaissance.
Signature : nettoyer_html(texte), canoniser_url(ressources,issuer,url,base=None),
normaliser_flux(ressources,issuer,xml,recu_ms,connus=()) -> FluxNormalise ;
FluxNormalise(documents,couverture,anomalies=()).
Entrée : ressources chargées, issuer configuré, XML RSS/Atom/RDF en octets
UTF-8, réception UTC et documents connus au plus tard à cette réception.
Sortie : documents nettoyés et horodatés, URL canonique officielle, empreinte
du texte, identité stable et couverture COMPLETE ou PARTIAL du flux.
Effets de bord : aucun transport, fichier, base ni horloge ; aucun article,
pièce jointe ou lien n’est téléchargé.
Erreurs, exceptions : ErreurService pour taille, encodage, XML invalide,
DTD/entité, racine non RSS/Atom/RDF, source inconnue et historique futur.
Un item invalide est signalé et ignoré sans perdre les autres items.

## Spécification exécutable

test_cat1_c1c_normalisation.py couvre formats, HTML, dates, tailles, origines,
DTD, dédoublonnage et corrections. test_cat2_c1c_normalisation.py traverse les
ressources et DocumentIA réels, avec réceptions successives et préfixes causaux.

## Comportements documentés

Les plafonds de téléchargement et texte proviennent de l’export IA. Un texte
nettoyé trop long est ignoré et produit une couverture partielle ; il n’est
jamais tronqué puis classifié. Les scripts et styles ne sont pas du texte
visible. Le nettoyage garde les mots, notamment négations et conditions.
Les URL utilisent HTTPS et le domaine configuré pour l’issuer ; fragments et
port HTTPS par défaut sont normalisés, sans suppression arbitraire de query.
L’issuer est imposé par la configuration, jamais extrait d’une affirmation du
corps. Aucun identifiant de connexion dans l’URL n’est accepté.

La publication vient de pubDate, published ou date ; updated ne remplace pas
une publication absente. Une date absente ou non convertible donne UNDATED,
une date future FUTURE. Ces documents restent documentaires. Les dates munies
d’un fuseau sont converties en UTC ; aucun fuseau n’est déduit de la machine.
Les dates sont conservées à la milliseconde, comme le noyau canonique.

Pour un issuer, une même empreinte de texte réutilise le premier document,
même sous une autre URL. Une correction de texte à URL identique possède une
nouvelle identité, mais conserve la publication et première connaissance de
la publication initiale. Toutes les versions restent disponibles à l’archive.
La collecte change seulement collecte_ms ; elle n’ouvre aucune nouvelle fenêtre
de veto. L’ordre d’items et l’historique fourni sont explicites et déterministes.
COMPLETE signifie que le flux reçu est lisible et ses items retenus complets,
sans déclaration d’exhaustivité des nouvelles du marché. Une anomalie d’item
ou une date non qualifiée rend la couverture du flux PARTIAL.
