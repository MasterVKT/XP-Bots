"""Commandes C10 : mêmes moteurs, contrôles et rapports que le bloc figé."""
from collections.abc import Mapping
from dataclasses import replace,fields
from datetime import datetime,timezone

from xpbots.app.c0_configuration import ErreurApplication
from xpbots.infra.c0a_types import TableHeureServeur
from xpbots.infra.c4_assemblage import ouvrir_ticks
from xpbots.noyau.c0a_temps import instant_depuis_datetime,verifier_instant
from xpbots.noyau.c0c_configuration import ConfigurationFigee
from xpbots.noyau.c1b_instrument import construire_profil_instrument,ProfilInstrument
from xpbots.orchestration.c0_contrats import ReceptionExterne
from xpbots.orchestration.c3_codec import serialiser_valeur,deserialiser_valeur
from xpbots.fondamental.c3_permissions import PermissionsFondamentales
from xpbots.contexte_ia.c0_types import charger_parametres,PolitiqueVeto
from xpbots.contexte_ia.c3_contexte import LecteurContexte
from xpbots.rejeu.c0a_types import (TarifCommission,ConditionContrat,ManifesteTicks,Trade,PointCompte,
    JourMarche,ValeurJour,FactureIA,EcartRejeu)
from xpbots.rejeu.c0b_protocole import BlocC10,ScenarioExecution
from xpbots.rejeu.c2_executeur import (DemandeRejeu,AutorisationReserve,ResultatPilote,ComptageRejeu,
    ResultatBrasRejeu,ResultatExperience,SourceTicks,ControlesRejeu,RegistreReserve,
    executer_experience,appliquer_ecart)
from xpbots.rejeu.c3_rapports import produire_rapport

TYPES_REJEU=tuple(('rejeu.'+c.__name__,c) for c in (
    TarifCommission,ConditionContrat,ManifesteTicks,Trade,PointCompte,JourMarche,ValeurJour,
    FactureIA,EcartRejeu,BlocC10,ScenarioExecution,DemandeRejeu,ResultatPilote,ComptageRejeu,
    ResultatBrasRejeu,ResultatExperience))


def encoder_rejeu(valeur):return serialiser_valeur(valeur,types_supplementaires=TYPES_REJEU)
def decoder_rejeu(octets):return deserialiser_valeur(octets,types_supplementaires=TYPES_REJEU)


def charger_archive(octets,configuration):
    d=decoder_rejeu(octets)
    if (not isinstance(configuration,ConfigurationFigee) or not isinstance(d,Mapping)
            or set(d)!={'schema','resultat','controles','empreintes_source','autorisation_declaree'}
            or d['schema']!='xp-archive-c10-v1' or not isinstance(d['resultat'],ResultatExperience)):
        raise ErreurApplication('ARCHIVE_C10_INVALIDE')
    r=d['resultat']
    if (r.configuration_origine!=configuration
            or r.configuration!=appliquer_ecart(configuration,r.demande.ecart,r.demande.mode)
            or r.demande.autorisation is not None):
        raise ErreurApplication('CONFIGURATION_ARCHIVE_C10_ETRANGERE')
    return d


class _SourceHorodatee:
    def __init__(self,receptions,*,controle=None,lecteur=None):
        self.controle=controle;self.lecteur=lecteur;self._receptions=tuple(receptions);self._position=0
    @property
    def prochaine_reception_ms(self):
        return self._receptions[self._position][0] if self._position<len(self._receptions) else None
    def extraire(self,t):
        resultat=[]
        while self.prochaine_reception_ms is not None and self.prochaine_reception_ms<=t:
            resultat.append(self._receptions[self._position][1]);self._position+=1
        return tuple(resultat)


def fabriquer_controles(configuration,scenario,receptions=(),table_heure=None):
    if scenario not in (None,'TECHNICAL_CONTROL_NEUTRAL'):raise ErreurApplication('SCENARIO_FONDAMENTAL_INVALIDE')
    if not isinstance(receptions,(tuple,list)):raise ErreurApplication('RECEPTIONS_HISTORIQUES_INVALIDES')
    receptions=tuple(receptions);precedent=None
    for paire in receptions:
        if not isinstance(paire,(tuple,list)) or len(paire)!=len(('instant','reception')):
            raise ErreurApplication('RECEPTION_HISTORIQUE_INVALIDE')
        t,r=paire;verifier_instant(t)
        if not isinstance(r,ReceptionExterne) or precedent is not None and t<precedent:
            raise ErreurApplication('RECEPTIONS_HISTORIQUES_NON_CHRONOLOGIQUES')
        precedent=t
    table=TableHeureServeur.depuis_document(table_heure) if scenario is None else None
    def convertir(texte):
        format_='%Y.%m.%d %H:%M:%S'
        dt=datetime.strptime(texte,format_)
        if dt.strftime(format_)!=texte:raise ErreurApplication('HEURE_NATIVE_HISTORIQUE_INVALIDE')
        return table.utc_de_serveur(instant_depuis_datetime(dt.replace(tzinfo=timezone.utc)))
    def fabrique(premier):
        if receptions and receptions[0][0]<premier:raise ErreurApplication('RECEPTION_ANTERIEURE_AU_PRECHARGEMENT')
        lecteur=LecteurContexte(charger_parametres(configuration),PolitiqueVeto(True))
        fond=PermissionsFondamentales(configuration.technique.commun,convertir) if scenario is None else None
        ia=tuple(p for p in receptions if p[1].nature=='SNAPSHOT')
        autres=tuple(p for p in receptions if p[1].nature!='SNAPSHOT')
        if fond is None and autres:raise ErreurApplication('CONTROLES_C05_DANS_SCENARIO_NEUTRE')
        return ControlesRejeu(fondamental=fond,
            source_fondamentale=_SourceHorodatee(autres,controle=fond) if fond is not None else None,
            lecteur_ia=lecteur,source_ia=_SourceHorodatee(ia,lecteur=lecteur),scenario=scenario)
    return fabrique


def lancer_rejeu(configuration,document,fichier,*,autorisation=None):
    cles={'schema','demande','manifeste','conditions','scenario_fondamental','receptions','table_heure','factures'}
    if (not isinstance(configuration,ConfigurationFigee) or not isinstance(document,Mapping) or set(document)!=cles
            or document['schema']!='xp-demande-rejeu-v1' or not isinstance(document['demande'],DemandeRejeu)
            or not isinstance(document['manifeste'],ManifesteTicks) or document['demande'].autorisation is not None):
        raise ErreurApplication('DEMANDE_REJEU_INVALIDE')
    if autorisation is not None and not isinstance(autorisation,AutorisationReserve):
        raise ErreurApplication('AUTORISATION_RESERVE_INVALIDE')
    if not isinstance(document['conditions'],(tuple,list)) or not isinstance(document['factures'],(tuple,list)):
        raise ErreurApplication('COLLECTIONS_REJEU_INVALIDES')
    conditions=tuple(document['conditions'])
    for c in conditions:
        if not isinstance(c,ConditionContrat) or not isinstance(c.profil,ProfilInstrument):
            raise ErreurApplication('CONDITIONS_C04_REQUISES')
        p=c.profil
        valide=construire_profil_instrument({f.name:getattr(p,f.name) for f in fields(p)},configuration.technique.commun)
        if valide.profil is None or encoder_rejeu(valide.profil)!=encoder_rejeu(p):
            raise ErreurApplication('PROFIL_C04_HISTORIQUE_NON_PRET')
    demande=replace(document['demande'],autorisation=autorisation)
    fabrique=fabriquer_controles(configuration,document['scenario_fondamental'],
                               document['receptions'],document['table_heure'])
    empreintes={}
    def lire():
        # Ce corps et l'ouverture physique ne sont atteints qu'après les gardes C10.
        try:
            with ouvrir_ticks(fichier) as lecteur:
                yield from lecteur.lignes()
                empreintes.update(sha256_physique=lecteur.sha256_fichier,sha256_contenu=lecteur.sha256_contenu)
        except EOFError:raise ErreurApplication('FICHIER_TICKS_GZIP_INCOMPLET') from None
    r=executer_experience(configuration,demande,SourceTicks(document['manifeste'],lire),conditions,
        fabrique_controles=fabrique,registre_reserve=RegistreReserve(),factures=document['factures'])
    if not empreintes.get('sha256_physique') or empreintes.get('sha256_contenu')!=document['manifeste'].sha256:
        raise ErreurApplication('INTEGRITE_FICHIER_REJEU_NON_ETABLIE')
    sans_callback=replace(r,demande=replace(r.demande,autorisation=None))
    controle=dict(scenario=document['scenario_fondamental'],receptions=tuple(document['receptions']),
                  table_heure=document['table_heure'])
    trace=None if autorisation is None else dict(option_expresse=autorisation.option_expresse,
                                               empreinte_robot=autorisation.empreinte_robot)
    archive=encoder_rejeu(dict(schema='xp-archive-c10-v1',resultat=sans_callback,controles=controle,
                               empreintes_source=dict(empreintes),autorisation_declaree=trace))
    return dict(resultat=r,rapport=produire_rapport((r,)),archive=archive)
