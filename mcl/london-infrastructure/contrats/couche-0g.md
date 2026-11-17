# Couche 0g — sources physiques C05 et D12
Statut : finalisé le 10/11/2026 avant code. Frontière réelle : fichiers en lecture seule.
SourcesControles(dossier_commun,liaisons,max_octets).lire(instant_ms)
-> tuple ReceptionFichier(nature,symbole,octets,instant_ms,erreur).
Chemins exacts XPBots/fondamental/v1/permission_<CANONIQUE>.json (D11) et
XPBots/export/v1/calendrier.json, seances_<courtier>.json,
fermetures_exceptionnelles.json (D12), conformes au document 01 §2.1/2.2.
Chaque appel ouvre, lit au plus max+1 et ferme ; absence/erreur/trop grand donne
octets None et code statique, pas un message système potentiellement sensible.
L’instant injecté date la lecture, jamais mtime. Aucun cache ni parsing métier :
séquences, known_at et non-renouvellement des contenus identiques relèvent de la
coquille et des vrais blocs C05/IA. Les fichiers ne sont jamais écrits ici.
Noms sans traversals/chemins absolus, liaisons fixes, un symbole courtier par
sous-jacent déjà qualifié. Tests sur dossiers temporaires réels, manquants,
plafonds et mises à jour ; test de contrat futur du vrai dossier commun.
