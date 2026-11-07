"""Port C04/C07 synthétique, sans terminal, ordre, fichier ou réseau. Les formules sont vérifiables à la main."""
from decimal import Decimal as D,Context,localcontext
from xpbots.execution.c0a_types import EtatCompte,ControleNatif
from robot.outils.execution_partagee import profil,T

class CalculSynthetique:
    def __init__(self,compte=None,profil_=None,*,autres_frais=D(0),marge_unitaire=D(1)):
        self.compte=compte or EtatCompte(T,D(100),D(100),D(0))
        self.profil=profil_ or profil()
        self.autres_frais=autres_frais
        self.marge_unitaire=marge_unitaire
        self.appels=[]
    def profit(self,profil,sens,volume,entree,sortie):
        self.appels.append(('profit',volume,entree,sortie))
        with localcontext(Context(prec=48)): return D(sens.signe)*volume*profil.taille_contrat*(sortie-entree)
    def frais_aller_retour(self,profil,sens,volume):
        self.appels.append(('frais_aller_retour',volume))
        with localcontext(Context(prec=48)):
            cote=max(profil.commission_par_lot_par_cote*volume,profil.commission_minimum_par_ordre)
            return cote+cote+self.autres_frais
    def marge(self,profil,sens,volume,entree):
        self.appels.append(('marge',volume))
        return volume*self.marge_unitaire
    def frais_sortie(self,profil,sens,volume):
        self.appels.append(('frais_sortie',volume))
        return max(profil.commission_par_lot_par_cote*volume,profil.commission_minimum_par_ordre)+self.autres_frais
    def controler(self,ordre,compte,remplacement=False):
        self.appels.append(('controler',ordre.volume,remplacement))
        ancienne=next((p.volume*self.marge_unitaire for p in compte.positions if p.cle==ordre.cle),D(0)) if remplacement else D(0)
        marge=compte.marge_utilisee-ancienne+ordre.volume*self.marge_unitaire
        return ControleNatif(True,marge,compte.fonds_propres-marge,True,'SYNTHETIQUE')
    def specifications(self,symbole):
        self.appels.append(('specifications',symbole)); return self.profil
    def etat_compte(self):
        self.appels.append(('etat_compte',));return self.compte
