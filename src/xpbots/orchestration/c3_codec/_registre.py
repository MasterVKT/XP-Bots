"""Registre fermé : noms et constructeurs publics, sans import issu des données."""
from xpbots.noyau.c0a_temps import CleEvenement
from xpbots.noyau.c0c_configuration import ConfigurationFigee, ExportIA, ExportTechnique, ParametresCommuns
from xpbots.noyau.c1a_marche import Bougie, Cotation, Tick
from xpbots.noyau.c1b_instrument import HorairesCotation, Intervalle, ProfilCompte, ProfilInstrument, ResultatProfil
from xpbots.noyau.c1c_domaine import AbsenceDeSignal, CauseCloture, CleIntention, ContexteIA, DecisionContexteIA, DecisionFondamentale, Issue, Motif, NatureIssue, Sens, SignalTechnique
from xpbots.noyau.c2_journal import Enregistrement, Enveloppe, TypeEnregistrement
from xpbots.donnees.c0a_types import AnomalieDonnees, BougieEnrichie, ChangementTrou, IdentitePrechargement, IndicateursBougie, NatureTrou, StatutCouverture, UniteTemps
from xpbots.donnees.c1a_constructeur import BougieBrute, SortieConstructeur
from xpbots.donnees.c1b_indicateurs import EtatIndicateurs, ResultatIndicateurs
from xpbots.donnees.c2a_validation import ResultatValidation
from xpbots.execution.c0a_types import RefusExecution, EtatIntention, PositionCompte, EtatCompte, Reservation, EtatReservations, EtatGardes, ControleNatif, OrdreCalcule
from xpbots.execution.c0c_cotation import EtatCotation, VerdictCotation
from xpbots.execution.c0d_prix import NiveauxExecutables, RefusPrix
from xpbots.execution.c0e_echeances import EcheanceSortie
from xpbots.execution.c1b_gardes import MouvementCompte, BaseReconstituee
from xpbots.execution.c2a_risque import MesureRisque
from xpbots.execution.c2b_arbitrage import CandidatArbitrage
from xpbots.execution.c3_dimensionnement import PlanDimensionnement
from xpbots.execution.c4_cycle import IdentiteCourtier, NatureCommande, NatureReponse, StatutAccuse, CommandeExecution, ReponseCourtier, PreuvePersistance, PreuveAbsence, EtatCycle, TraceCycle, EffetsCycle
from xpbots.execution.c5a_sorties import SortieObligatoire, PlanSorties
from xpbots.execution.c5b_reprise import CyclePersiste, EtatReprise, PositionNative, OrdreNatif, ObservationNative, BilanReprise
from xpbots.execution.c6_coordinateur import TentativeCotation, DossierIntention, EtatCoordinateur, LotCoordinateur
from xpbots.fondamental.c0_types import Annonce, DirectionFondamentale, EtatRisque, MessagePermission, TableImportance, VersionCalendrier
from xpbots.fondamental.c1b_annonces import EtatCalendrier, ReceptionCalendrier
from xpbots.fondamental.c2_etat_permissions import ConsultationPermission, EtatPermissions, EvenementSuivi, InterruptionPermission, PermissionRecue, ReceptionPermission, SuiviHeartbeat
from xpbots.fondamental.c3_permissions import EtatFondamental
from xpbots.contexte_ia.c0_types import ParametresContexte, PolitiqueVeto, SnapshotIA, SnapshotRecu, Veto, VetoConnu
from xpbots.contexte_ia.c2_cache import EtatCache, ReceptionSnapshot
from xpbots.orchestration.c0_contrats import Deploiement, ReceptionExterne, MiseAJourBras, EntreeMoteur, SortieMoteur, SortieEvenement, AppelCalcul, EntreeJournalisee
from xpbots.orchestration.c1_bras import EtatBras, TraceStrategie
from xpbots.orchestration.c2_moteur import EtatMoteur, CheckpointMoteur, CheckpointJournalMoteur

TYPES_PUBLICS = (
    ('xpbots.orchestration.c2_moteur.CheckpointJournalMoteur', CheckpointJournalMoteur),
    ('xpbots.noyau.c0a_temps.CleEvenement', CleEvenement),
    ('xpbots.noyau.c0c_configuration.ConfigurationFigee', ConfigurationFigee),
    ('xpbots.noyau.c0c_configuration.ExportIA', ExportIA),
    ('xpbots.noyau.c0c_configuration.ExportTechnique', ExportTechnique),
    ('xpbots.noyau.c0c_configuration.ParametresCommuns', ParametresCommuns),
    ('xpbots.noyau.c1a_marche.Bougie', Bougie),
    ('xpbots.noyau.c1a_marche.Cotation', Cotation),
    ('xpbots.noyau.c1a_marche.Tick', Tick),
    ('xpbots.noyau.c1b_instrument.HorairesCotation', HorairesCotation),
    ('xpbots.noyau.c1b_instrument.Intervalle', Intervalle),
    ('xpbots.noyau.c1b_instrument.ProfilCompte', ProfilCompte),
    ('xpbots.noyau.c1b_instrument.ProfilInstrument', ProfilInstrument),
    ('xpbots.noyau.c1b_instrument.ResultatProfil', ResultatProfil),
    ('xpbots.noyau.c1c_domaine.AbsenceDeSignal', AbsenceDeSignal),
    ('xpbots.noyau.c1c_domaine.CauseCloture', CauseCloture),
    ('xpbots.noyau.c1c_domaine.CleIntention', CleIntention),
    ('xpbots.noyau.c1c_domaine.ContexteIA', ContexteIA),
    ('xpbots.noyau.c1c_domaine.DecisionContexteIA', DecisionContexteIA),
    ('xpbots.noyau.c1c_domaine.DecisionFondamentale', DecisionFondamentale),
    ('xpbots.noyau.c1c_domaine.Issue', Issue),
    ('xpbots.noyau.c1c_domaine.Motif', Motif),
    ('xpbots.noyau.c1c_domaine.NatureIssue', NatureIssue),
    ('xpbots.noyau.c1c_domaine.Sens', Sens),
    ('xpbots.noyau.c1c_domaine.SignalTechnique', SignalTechnique),
    ('xpbots.noyau.c2_journal.Enregistrement', Enregistrement),
    ('xpbots.noyau.c2_journal.Enveloppe', Enveloppe),
    ('xpbots.noyau.c2_journal.TypeEnregistrement', TypeEnregistrement),
    ('xpbots.donnees.c0a_types.AnomalieDonnees', AnomalieDonnees),
    ('xpbots.donnees.c0a_types.BougieEnrichie', BougieEnrichie),
    ('xpbots.donnees.c0a_types.ChangementTrou', ChangementTrou),
    ('xpbots.donnees.c0a_types.IdentitePrechargement', IdentitePrechargement),
    ('xpbots.donnees.c0a_types.IndicateursBougie', IndicateursBougie),
    ('xpbots.donnees.c0a_types.NatureTrou', NatureTrou),
    ('xpbots.donnees.c0a_types.StatutCouverture', StatutCouverture),
    ('xpbots.donnees.c0a_types.UniteTemps', UniteTemps),
    ('xpbots.donnees.c1a_constructeur.BougieBrute', BougieBrute),
    ('xpbots.donnees.c1a_constructeur.SortieConstructeur', SortieConstructeur),
    ('xpbots.donnees.c1b_indicateurs.EtatIndicateurs', EtatIndicateurs),
    ('xpbots.donnees.c1b_indicateurs.ResultatIndicateurs', ResultatIndicateurs),
    ('xpbots.donnees.c2a_validation.ResultatValidation', ResultatValidation),
    ('xpbots.execution.c0a_types.RefusExecution', RefusExecution),
    ('xpbots.execution.c0a_types.EtatIntention', EtatIntention),
    ('xpbots.execution.c0a_types.PositionCompte', PositionCompte),
    ('xpbots.execution.c0a_types.EtatCompte', EtatCompte),
    ('xpbots.execution.c0a_types.Reservation', Reservation),
    ('xpbots.execution.c0a_types.EtatReservations', EtatReservations),
    ('xpbots.execution.c0a_types.EtatGardes', EtatGardes),
    ('xpbots.execution.c0a_types.ControleNatif', ControleNatif),
    ('xpbots.execution.c0a_types.OrdreCalcule', OrdreCalcule),
    ('xpbots.execution.c0c_cotation.EtatCotation', EtatCotation),
    ('xpbots.execution.c0c_cotation.VerdictCotation', VerdictCotation),
    ('xpbots.execution.c0d_prix.NiveauxExecutables', NiveauxExecutables),
    ('xpbots.execution.c0d_prix.RefusPrix', RefusPrix),
    ('xpbots.execution.c0e_echeances.EcheanceSortie', EcheanceSortie),
    ('xpbots.execution.c1b_gardes.MouvementCompte', MouvementCompte),
    ('xpbots.execution.c1b_gardes.BaseReconstituee', BaseReconstituee),
    ('xpbots.execution.c2a_risque.MesureRisque', MesureRisque),
    ('xpbots.execution.c2b_arbitrage.CandidatArbitrage', CandidatArbitrage),
    ('xpbots.execution.c3_dimensionnement.PlanDimensionnement', PlanDimensionnement),
    ('xpbots.execution.c4_cycle.IdentiteCourtier', IdentiteCourtier),
    ('xpbots.execution.c4_cycle.NatureCommande', NatureCommande),
    ('xpbots.execution.c4_cycle.NatureReponse', NatureReponse),
    ('xpbots.execution.c4_cycle.StatutAccuse', StatutAccuse),
    ('xpbots.execution.c4_cycle.CommandeExecution', CommandeExecution),
    ('xpbots.execution.c4_cycle.ReponseCourtier', ReponseCourtier),
    ('xpbots.execution.c4_cycle.PreuvePersistance', PreuvePersistance),
    ('xpbots.execution.c4_cycle.PreuveAbsence', PreuveAbsence),
    ('xpbots.execution.c4_cycle.EtatCycle', EtatCycle),
    ('xpbots.execution.c4_cycle.TraceCycle', TraceCycle),
    ('xpbots.execution.c4_cycle.EffetsCycle', EffetsCycle),
    ('xpbots.execution.c5a_sorties.SortieObligatoire', SortieObligatoire),
    ('xpbots.execution.c5a_sorties.PlanSorties', PlanSorties),
    ('xpbots.execution.c5b_reprise.CyclePersiste', CyclePersiste),
    ('xpbots.execution.c5b_reprise.EtatReprise', EtatReprise),
    ('xpbots.execution.c5b_reprise.PositionNative', PositionNative),
    ('xpbots.execution.c5b_reprise.OrdreNatif', OrdreNatif),
    ('xpbots.execution.c5b_reprise.ObservationNative', ObservationNative),
    ('xpbots.execution.c5b_reprise.BilanReprise', BilanReprise),
    ('xpbots.execution.c6_coordinateur.TentativeCotation', TentativeCotation),
    ('xpbots.execution.c6_coordinateur.DossierIntention', DossierIntention),
    ('xpbots.execution.c6_coordinateur.EtatCoordinateur', EtatCoordinateur),
    ('xpbots.execution.c6_coordinateur.LotCoordinateur', LotCoordinateur),
    ('xpbots.fondamental.c0_types.Annonce', Annonce),
    ('xpbots.fondamental.c0_types.DirectionFondamentale', DirectionFondamentale),
    ('xpbots.fondamental.c0_types.EtatRisque', EtatRisque),
    ('xpbots.fondamental.c0_types.MessagePermission', MessagePermission),
    ('xpbots.fondamental.c0_types.TableImportance', TableImportance),
    ('xpbots.fondamental.c0_types.VersionCalendrier', VersionCalendrier),
    ('xpbots.fondamental.c1b_annonces.EtatCalendrier', EtatCalendrier),
    ('xpbots.fondamental.c1b_annonces.ReceptionCalendrier', ReceptionCalendrier),
    ('xpbots.fondamental.c2_etat_permissions.ConsultationPermission', ConsultationPermission),
    ('xpbots.fondamental.c2_etat_permissions.EtatPermissions', EtatPermissions),
    ('xpbots.fondamental.c2_etat_permissions.EvenementSuivi', EvenementSuivi),
    ('xpbots.fondamental.c2_etat_permissions.InterruptionPermission', InterruptionPermission),
    ('xpbots.fondamental.c2_etat_permissions.PermissionRecue', PermissionRecue),
    ('xpbots.fondamental.c2_etat_permissions.ReceptionPermission', ReceptionPermission),
    ('xpbots.fondamental.c2_etat_permissions.SuiviHeartbeat', SuiviHeartbeat),
    ('xpbots.fondamental.c3_permissions.EtatFondamental', EtatFondamental),
    ('xpbots.contexte_ia.c0_types.ParametresContexte', ParametresContexte),
    ('xpbots.contexte_ia.c0_types.PolitiqueVeto', PolitiqueVeto),
    ('xpbots.contexte_ia.c0_types.SnapshotIA', SnapshotIA),
    ('xpbots.contexte_ia.c0_types.SnapshotRecu', SnapshotRecu),
    ('xpbots.contexte_ia.c0_types.Veto', Veto),
    ('xpbots.contexte_ia.c0_types.VetoConnu', VetoConnu),
    ('xpbots.contexte_ia.c2_cache.EtatCache', EtatCache),
    ('xpbots.contexte_ia.c2_cache.ReceptionSnapshot', ReceptionSnapshot),
    ('xpbots.orchestration.c0_contrats.Deploiement', Deploiement),
    ('xpbots.orchestration.c0_contrats.ReceptionExterne', ReceptionExterne),
    ('xpbots.orchestration.c0_contrats.MiseAJourBras', MiseAJourBras),
    ('xpbots.orchestration.c0_contrats.EntreeMoteur', EntreeMoteur),
    ('xpbots.orchestration.c0_contrats.SortieMoteur', SortieMoteur),
    ('xpbots.orchestration.c0_contrats.SortieEvenement', SortieEvenement),
    ('xpbots.orchestration.c0_contrats.AppelCalcul', AppelCalcul),
    ('xpbots.orchestration.c0_contrats.EntreeJournalisee', EntreeJournalisee),
    ('xpbots.orchestration.c1_bras.EtatBras', EtatBras),
    ('xpbots.orchestration.c1_bras.TraceStrategie', TraceStrategie),
    ('xpbots.orchestration.c2_moteur.EtatMoteur', EtatMoteur),
    ('xpbots.orchestration.c2_moteur.CheckpointMoteur', CheckpointMoteur),
)
