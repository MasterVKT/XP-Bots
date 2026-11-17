# Couche 0e — lecture physique du snapshot
Statut : finalisé le 10/11/2026 avant code. Frontière réelle : fichiers.
LecteurSnapshot(chemin,max_octets).lire(instant_ms) -> (bytes|None,int,str|None).
Le plafond est injecté depuis l’export IA ; lecture binaire max+1, fermeture
immédiate par with, jamais de fichier ouvert pendant la décision du cœur.
Absent, trop grand ou erreur de lecture -> absence et code statique ; l’appelant
livre l’absence au vrai lecteur IA, dont la panne vaut NEUTRAL. Pas de parsing,
cache, durée inventée, renouvellement de fraîcheur ni décision de veto ici.
L’instant est celui de lecture fourni par l’horloge de la coquille, jamais mtime.
Tests : plafond exact/+1, absent, remplacement après lecture et fermeture garantie.
