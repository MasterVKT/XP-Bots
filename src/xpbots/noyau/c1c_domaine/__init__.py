"""Couche 1c du noyau — `domaine` : sens, signaux, intentions, issues, décisions des contrôles, motifs fermés.

Interface publique figée ; contrat : mcl/noyau/contrats/couche-1c.md.
"""
from xpbots.noyau.c1c_domaine._impl import (DETAILS_ENUMERES, MOTIFS_A_DETAIL_LIBRE, VERSION_DETAILS,
                                            AbsenceDeSignal, CauseCloture, CleIntention, ContexteIA,
                                            DecisionContexteIA, DecisionFondamentale, ErreurDomaine, Issue, Motif,
                                            NatureIssue, ResultatTechnique, Sens, SignalTechnique, verifier_motif)

__all__ = ['DETAILS_ENUMERES', 'MOTIFS_A_DETAIL_LIBRE', 'VERSION_DETAILS', 'AbsenceDeSignal', 'CauseCloture',
           'CleIntention', 'ContexteIA', 'DecisionContexteIA', 'DecisionFondamentale', 'ErreurDomaine', 'Issue',
           'Motif', 'NatureIssue', 'ResultatTechnique', 'Sens', 'SignalTechnique', 'verifier_motif']
