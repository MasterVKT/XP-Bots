# Couche 0b — horloge physique
Statut : finalisé le 10/11/2026 avant code. Frontière réelle : time.
HorlogeSysteme.utc_ms() -> int, monotone_ns() -> int, attendre_ms(duree) -> None.
UTC = time_ns // 1_000_000 ; le temps monotone n’est jamais une date de marché.
Attente finie positive ou nulle, bool et nombres non finis refusés (ValueError).
Seule cette couche lit une horloge physique ; le cœur reçoit des instants injectés.
Tests : doublure de la seule frontière time, conversion exacte et refus des bornes.
