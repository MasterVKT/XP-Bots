"""Seules frontières doublées : SDK et horloge ; fichiers/SQLite/blocs réels."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import os
from robot.outils.orchestration import C
from robot.outils.faux_mt5 import FauxMT5
from robot.outils.qualification_mt5 import T
from robot.outils.assemblage_mt5 import parametres,installer_controles
from robot.points_entree.test_cat1_c0_configuration import registre
from xpbots.app.c0_configuration import analyser_registre
from xpbots.app.c2_boucle_direct import BoucleDirect
from xpbots.infra.c4_assemblage import InfrastructurePhysique


class HarnaisDirect:
    def setUp(self):
        self.temp=TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve();self.commun=self.root/'commun'
        self.temps=T;self.monotone=0;self.attentes=[]
        for nom,fonction in (('time.time_ns',lambda:self.temps*1000000),
                              ('time.monotonic_ns',lambda:self.monotone),('time.sleep',self.dormir)):
            p=patch(nom,side_effect=fonction);p.start();self.addCleanup(p.stop)
        p=patch.dict(os.environ,{'XPBOTS_COMMON_FILES_DIR':''});p.start();self.addCleanup(p.stop)
        self.infras=[];self.addCleanup(lambda:[i.fermer(1000) for i in reversed(self.infras)])

    def avancer(self,ms):
        self.temps+=ms;self.monotone+=ms*1000000
        if hasattr(self,'sdk'):self.sdk.instant_ms=self.temps

    def dormir(self,secondes):
        self.attentes.append(secondes);self.avancer(round(secondes*1000))

    def nouveau(self,mode='PAPER',*,sdk=None,document=None,qualification=None,table=None):
        self.sdk=sdk or FauxMT5(self.commun,instant_ms=self.temps)
        d=registre(mode) if document is None else document
        d['chemins']['racine']=str(self.root)
        self.app=analyser_registre(d,C,self.temps)
        i=InfrastructurePhysique(C.technique.commun,self.app.meta,self.app.liaisons,racine=self.root,
            max_octets_echange=self.app.ingenierie['max_octets_echange'],snapshot_max_octets=C.ia.parametres['snapshot_max_bytes'],sdk=self.sdk,
            common_files_attendu=str(self.commun/'Files'))
        self.infras.append(i)
        t,q,_=parametres(self.sdk)
        self.table=t if table is None else table;self.q=q if qualification is None else qualification
        if not (Path(i.session.etat.common_files)/'XPBots/export/v1/calendrier.json').exists():
            installer_controles(i.session.etat.common_files,t=self.temps)
        self.infra=i;self.boucle=BoucleDirect(self.app,i,self.table,self.q)
        return self.boucle
