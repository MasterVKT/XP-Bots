"""Noyau : deux lignées de construction MCL coexistent dans ce paquet, sans module en commun.

Robot 1 (squelette composite) : modules plats `config`, `decisions`, `journal_schema`, `json_canonique`, `marche`, `ports`,
`temps` (types de couture, ports, motifs, journal C09 et configuration).

Robot London (artefact `noyau`, phase 2, figé ; types et règles partagés, purs, sans entrée-sortie) : une couche = un
sous-paquet, interface publique dans son `__init__.py` : `c0a_temps` (instants), `c0b_nombres` (décimaux sur grille),
`c0c_configuration` (exports figés), `c1a_marche` (ticks, cotations, bougies), `c1b_instrument` (profils C04), `c1c_domaine`
(signaux, issues, motifs), `c2_journal` (journal C09). Carte et contrats : mcl/noyau/.
"""
