"""Attestation physique du gel ; la décision d'accès reste dans l'exécuteur C10."""
from xpbots.app.c0_configuration import ErreurApplication
from xpbots.infra.c4_assemblage import lire_configuration,lire_fichier,ecrire_fichier,empreinte_robot
from xpbots.noyau.c0a_temps import verifier_instant
from xpbots.rejeu.c3_rapports import serialiser_rapport


def joindre(racine,relatif):return str(racine).rstrip('/\\')+'/'+relatif

def octets_document(valeur):return (serialiser_rapport(valeur)+'\n').encode('utf-8')

def contexte(application):
    r=application.registre
    return dict(commit=r['commit'],empreintes=dict(r['empreintes']))


def creer_gel(application,racine,instant_ms,plafond,origine):
    # Le fichier chargé doit appartenir à l'arbre dont on atteste l'inventaire.
    lire_fichier(origine,plafond,racine=joindre(racine,'src/xpbots'))
    return dict(schema='xp-gel-robot-v1',**contexte(application),instant_utc_ms=instant_ms,
                inventaire=empreinte_robot(racine,plafond))


class AttestationReserve:
    """Appelé sous le verrou du projet ; aucune lecture de prix dans ce port."""
    def __init__(self,application,racine,fichier,horloge,plafond,origine,experience):
        self.application=application;self.racine=racine;self.fichier=fichier;self.horloge=horloge
        self.plafond=plafond;self.origine=origine;self.experience=experience
        self.registre=joindre(racine,'.local/validation/registre_reserve.json')
        self.raison_refus=None;self.trace=[]
        d=self._gel();self.empreinte=d['inventaire']['sha256']

    def _gel(self):
        d=lire_configuration(self.fichier,self.plafond);attendu=contexte(self.application)
        if (type(d) is not dict or set(d)!={'schema','commit','empreintes','instant_utc_ms','inventaire'}
                or d['schema']!='xp-gel-robot-v1'
                or any(d[k]!=v for k,v in attendu.items())):
            raise ErreurApplication('GEL_CONTEXTE_ETRANGER')
        verifier_instant(d['instant_utc_ms'])
        if d['instant_utc_ms']>self.horloge.utc_ms():raise ErreurApplication('GEL_DATE_FUTURE')
        courant=creer_gel(self.application,self.racine,d['instant_utc_ms'],self.plafond,self.origine)
        # La représentation JSON compare aussi les noms et le nombre de fichiers.
        if octets_document(courant)!=octets_document(d):raise ErreurApplication('GEL_ROBOT_DIFFERENT')
        return d

    def _evenement(self,action,empreinte,numero):
        return dict(numero=numero,action=action,experience=self.experience,
                    instant_utc_ms=self.horloge.utc_ms(),empreinte_robot=empreinte)

    def _charger_etat(self):
        d=lire_configuration(self.registre,self.plafond)
        cles={'schema','commit','empreintes','empreinte_robot','historique'}
        if (type(d) is not dict or set(d)!=cles or d['schema']!='xp-registre-reserve-v1'
                or type(d['historique']) is not list or not d['historique']):
            raise ErreurApplication('REGISTRE_RESERVE_INVALIDE')
        precedent=None
        for n,e in enumerate(d['historique'],1):
            if (type(e) is not dict or set(e)!={'numero','action','experience','instant_utc_ms','empreinte_robot'}
                    or type(e['numero']) is not int or e['numero']!=n or type(e['experience']) is not str
                    or e['action'] not in ('OUVERTURE_RESERVE','CONSULTATION_RESERVE','REFUS_RESERVE')
                    or (e['action']=='OUVERTURE_RESERVE')!=(n==1)
                    or e['action']!='REFUS_RESERVE' and e['empreinte_robot']!=d['empreinte_robot']):
                raise ErreurApplication('REGISTRE_RESERVE_INVALIDE')
            verifier_instant(e['instant_utc_ms'])
            if precedent is not None and e['instant_utc_ms']<precedent:raise ErreurApplication('REGISTRE_RESERVE_INVALIDE')
            precedent=e['instant_utc_ms']
        if precedent>self.horloge.utc_ms():raise ErreurApplication('HORLOGE_REGISTRE_RESERVE_EN_RECUL')
        return d

    def __call__(self,empreinte):
        self.raison_refus=None
        try:
            gel=self._gel()
            if empreinte!=self.empreinte or gel['inventaire']['sha256']!=empreinte:
                raise ErreurApplication('GEL_ROBOT_DIFFERENT')
            initial=dict(schema='xp-registre-reserve-v1',**contexte(self.application),
                empreinte_robot=empreinte,historique=[self._evenement('OUVERTURE_RESERVE',empreinte,1)])
            try:
                ecrire_fichier(self.registre,octets_document(initial))
                self.trace.append(initial['historique'][0]);return True
            except ValueError as erreur:
                if str(erreur)!='FICHIER_EXISTANT':raise
            d=self._charger_etat();ctx=contexte(self.application)
            concordant=d['empreinte_robot']==empreinte and all(d[k]==v for k,v in ctx.items())
            e=self._evenement('CONSULTATION_RESERVE' if concordant else 'REFUS_RESERVE',empreinte,len(d['historique'])+1)
            d['historique'].append(e);b=octets_document(d)
            if len(b)>self.plafond:raise ErreurApplication('REGISTRE_RESERVE_TROP_VOLUMINEUX')
            ecrire_fichier(self.registre,b,ecraser=True);self.trace.append(e)
            if not concordant:self.raison_refus='GEL_RESERVE_DIFFERENT'
            return concordant
        except (ValueError,OSError,TypeError,KeyError):
            self.raison_refus='ATTESTATION_RESERVE_INDISPONIBLE'
            return False
