"""Le portefeuille reste dans le simulateur figé ; seuls ses appels sont archivés."""
from collections.abc import Mapping
from hashlib import sha256
from types import MappingProxyType

from xpbots.app.c0_configuration import ErreurApplication
from xpbots.execution.c0a_types import RefusExecution
from xpbots.noyau.c1c_domaine import Motif
from xpbots.orchestration.c3_codec import serialiser_valeur,deserialiser_valeur
from xpbots.rejeu.c0a_types import ConditionContrat,TarifCommission
from xpbots.rejeu.c0b_protocole import charger_protocole
from xpbots.rejeu.c1b_simulateur import SimulateurExecution

TYPES_PAPIER=(('papier.ConditionContrat',ConditionContrat),('papier.TarifCommission',TarifCommission))
_OPERATIONS=frozenset(('sur_tick','extraire_reponses','soumettre','enregistrer_contexte',
                       'actualiser_profil','fixer_disponibilite'))


def _encoder(v):return serialiser_valeur(v,types_supplementaires=TYPES_PAPIER)
def _decoder(b):return deserialiser_valeur(b,types_supplementaires=TYPES_PAPIER)
def _empreinte(v):return sha256(_encoder(v)).hexdigest()


class LivrePapier:
    def __init__(self,configuration,conditions,creation_ms,scenario='REFERENCE',*,checkpoint=None,operations=()):
        conditions=tuple(conditions)
        modele=charger_protocole(configuration).scenario(scenario)
        self._simulateur=SimulateurExecution(configuration,conditions,creation_ms,modele)
        self._initialisation=_encoder(dict(schema='xp-livre-papier-initial-v1',
            technique=configuration.technique.empreinte_octets,ia=configuration.ia.empreinte_octets,
            conditions=conditions,creation_ms=creation_ms,scenario=scenario))
        self._signature=sha256(self._initialisation).hexdigest()
        self._disponibles={c.profil.symbole:False for c in conditions}
        self._operations=[];self._chaine=sha256(b'').hexdigest();self._valide=True
        operations=tuple(operations)
        if checkpoint is None:
            if operations:raise ErreurApplication('OPERATIONS_SANS_CHECKPOINT')
            return
        cles={'schema','signature','instant_ms','nombre_operations','empreinte'}
        if (not isinstance(checkpoint,Mapping) or set(checkpoint)!=cles
                or checkpoint['schema']!='xp-livre-papier-checkpoint-v1'
                or checkpoint['signature']!=self._signature
                or type(checkpoint['nombre_operations']) is not int
                or checkpoint['nombre_operations']!=len(operations)):
            raise ErreurApplication('CHECKPOINT_PAPIER_ETRANGER_OU_TRONQUE')
        for b in operations:self._rejouer_operation(b)
        self.avancer_au(checkpoint['instant_ms'])
        if dict(self.checkpoint)!=dict(checkpoint):raise ErreurApplication('CHECKPOINT_PAPIER_ALTERE')

    def _verifier(self):
        if not self._valide:raise ErreurApplication('LIVRE_PAPIER_INVALIDE_REPRISE_REQUISE')

    @property
    def initialisation(self):return _decoder(self._initialisation)
    @property
    def checkpoint(self):
        self._verifier()
        return MappingProxyType(dict(schema='xp-livre-papier-checkpoint-v1',signature=self._signature,
            instant_ms=self.instant_ms,nombre_operations=len(self._operations),empreinte=self._chaine))

    def operations_depuis(self,numero):
        self._verifier()
        if type(numero) is not int or not 0<=numero<=len(self._operations):
            raise ErreurApplication('INDICE_OPERATIONS_PAPIER_INVALIDE')
        return tuple(self._operations[numero:])

    @property
    def instant_ms(self):return self._simulateur.instant_ms
    @property
    def creation_ms(self):return self._simulateur.creation_ms
    @property
    def scenario(self):return self._simulateur.scenario
    @property
    def profil_compte(self):return self._simulateur.profil_compte
    @property
    def positions_ouvertes(self):return self._simulateur.positions_ouvertes
    @property
    def courbe(self):return self._simulateur.courbe
    @property
    def trades(self):return self._simulateur.trades
    @property
    def reponses(self):return self._simulateur.reponses
    @property
    def premiers_remplissages(self):return self._simulateur.premiers_remplissages
    @property
    def prochaine_echeance_ms(self):return self._simulateur.prochaine_echeance_ms

    def avancer_au(self,t):
        self._verifier()
        try:self._simulateur.avancer_au(t)
        except Exception:
            self._valide=False;raise

    def _appliquer(self,nature,args):
        if nature=='fixer_disponibilite':
            symbole,disponible,t=args
            if symbole not in self._disponibles or type(disponible) is not bool or type(t) is not int or t!=self.instant_ms:
                raise ErreurApplication('DISPONIBILITE_PAPIER_INVALIDE')
            self._disponibles[symbole]=disponible
            return None
        return getattr(self._simulateur,nature)(*args)

    def _operation(self,nature,args):
        self._verifier()
        if nature not in _OPERATIONS:raise ErreurApplication('OPERATION_PAPIER_INCONNUE')
        arguments=_encoder(tuple(args));copies=_decoder(arguments)
        try:
            resultat=self._appliquer(nature,copies)
            b=_encoder(dict(schema='xp-operation-papier-v1',numero=len(self._operations)+1,
                instant_ms=self.instant_ms,nature=nature,arguments=arguments,
                resultat_sha256=_empreinte(resultat),precedente=self._chaine))
        except Exception:
            self._valide=False;raise
        self._operations.append(b);self._chaine=sha256(b).hexdigest()
        return resultat

    def _rejouer_operation(self,b):
        d=_decoder(b)
        if (not isinstance(d,Mapping) or set(d)!={'schema','numero','instant_ms','nature','arguments','resultat_sha256','precedente'}
                or d['schema']!='xp-operation-papier-v1' or type(d['numero']) is not int
                or d['numero']!=len(self._operations)+1 or d['precedente']!=self._chaine
                or type(d['nature']) is not str or d['nature'] not in _OPERATIONS):
            raise ErreurApplication('OPERATION_PAPIER_ALTEREE')
        self.avancer_au(d['instant_ms'])
        resultat=self._operation(d['nature'],_decoder(d['arguments']))
        if self._operations[-1]!=b or _empreinte(resultat)!=d['resultat_sha256']:
            self._valide=False;raise ErreurApplication('REJEU_PAPIER_DIVERGENT')

    def sur_tick(self,tick):return self._operation('sur_tick',(tick,))
    def extraire_reponses(self,t):return self._operation('extraire_reponses',(t,))
    def soumettre(self,commandes):return self._operation('soumettre',(tuple(commandes),))
    def enregistrer_contexte(self,cle,contexte):return self._operation('enregistrer_contexte',(cle,contexte))
    def actualiser_profil(self,profil,tarif,instant_ms):
        return self._operation('actualiser_profil',(profil,tarif,instant_ms))
    def fixer_disponibilite(self,symbole,disponible,instant_ms):
        return self._operation('fixer_disponibilite',(symbole,disponible,instant_ms))

    def _non_pret(self):return RefusExecution(Motif.ENVIRONMENT_NOT_READY,'MARCHE_PAPIER_NON_PRET')
    def specifications(self,symbole):
        self._verifier()
        return self._simulateur.specifications(symbole) if self._disponibles.get(symbole) else self._non_pret()
    def controler(self,ordre,compte,remplacement=False):
        self._verifier()
        return self._simulateur.controler(ordre,compte,remplacement) if self._disponibles.get(ordre.cle.symbole) else self._non_pret()
    def profit(self,*args):self._verifier();return self._simulateur.profit(*args)
    def frais_aller_retour(self,*args):self._verifier();return self._simulateur.frais_aller_retour(*args)
    def frais_sortie(self,*args):self._verifier();return self._simulateur.frais_sortie(*args)
    def marge(self,*args):self._verifier();return self._simulateur.marge(*args)
    def etat_compte(self):self._verifier();return self._simulateur.etat_compte()
    def observation(self,cle=None):self._verifier();return self._simulateur.observation(cle)
    def base_utc(self):self._verifier();return self._simulateur.base_utc()
    def tick_decision(self,tick):self._verifier();return self._simulateur.tick_decision(tick)
