"""Commandes C10 : gzip réel, archive fermée et garde réservée avant ouverture."""
from dataclasses import replace
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
import gzip,unittest
from unittest.mock import patch

from robot.outils.orchestration import C
from robot.outils.rejeu import experience_courte,experience_london
from xpbots.app.c0_configuration import ErreurApplication
from xpbots.app.c1c_cli_rejeu import lancer_rejeu,encoder_rejeu,decoder_rejeu,charger_archive,fabriquer_controles
from xpbots.rejeu.c2_executeur import rejouer_experience,AutorisationReserve
from xpbots.rejeu.c0b_protocole import charger_protocole
from xpbots.noyau.c2_journal import serialiser
from xpbots.noyau.c0a_temps import instant_vers_iso
from xpbots.orchestration.c0_contrats import ReceptionExterne


def demande_fixture(london=False,**options):
    if london:d,source,conditions,_=experience_london(date(2026,11,9),**options)
    else:d,source,conditions,_,_=experience_courte(**options)
    return dict(schema='xp-demande-rejeu-v1',demande=replace(d,autorisation=None),manifeste=source.manifeste,
        conditions=conditions,scenario_fondamental='TECHNICAL_CONTROL_NEUTRAL',receptions=(),table_heure=None,factures=()),tuple(source.lire())


class HarnaisCommandeRejeu:
    def setUp(self):
        self.temp=TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.fichier=Path(self.temp.name)/'fixture.csv.gz'

    def executer(self,document,lignes):
        self.fichier.write_bytes(gzip.compress(''.join(lignes).encode('utf-8'),mtime=0))
        return lancer_rejeu(C,document,self.fichier)



class TestCommandeRejeu(HarnaisCommandeRejeu,unittest.TestCase):
    def test_reserve_refuse_avant_ouverture_meme_si_fichier_absent(self):
        d,_=demande_fixture(jour=date(2025,1,2))
        with patch('xpbots.app.c1c_cli_rejeu._impl.ouvrir_ticks',side_effect=AssertionError('LECTURE_INTERDITE')) as ouvrir:
            with self.assertRaisesRegex(ValueError,'verrouill'):lancer_rejeu(C,d,self.fichier)
            ouvrir.assert_not_called()

    def test_configuration_forgee_avec_empreintes_inchangees_refusee(self):
        d,lignes=demande_fixture();r=self.executer(d,lignes);a=decoder_rejeu(r['archive'])
        faux=replace(C,technique=replace(C.technique,commun=replace(C.technique.commun,account_currency='INVENTEE')))
        a['resultat']=replace(a['resultat'],configuration_origine=faux)
        with self.assertRaisesRegex(ErreurApplication,'CONFIGURATION_ARCHIVE'):charger_archive(encoder_rejeu(a),C)

    def test_stress_toujours_explicitement_c10_et_integrite_gzip(self):
        d,lignes=demande_fixture(scenario='STRESS');r=self.executer(d,lignes)
        a=charger_archive(r['archive'],C)
        self.assertEqual(a['resultat'].demande.scenario,'STRESS')
        self.assertEqual(a['empreintes_source']['sha256_contenu'],d['manifeste'].sha256)
        self.assertEqual(len(a['empreintes_source']['sha256_physique']),64)
        self.assertIsNone(a['autorisation_declaree'])

    def test_callback_runtime_retire_et_archive_sans_pouvoir_d_autorisation(self):
        d,lignes=demande_fixture()
        self.fichier.write_bytes(gzip.compress(''.join(lignes).encode(),mtime=0))
        autorisation=AutorisationReserve(True,'b'*64,lambda _:True)
        r=lancer_rejeu(C,d,self.fichier,autorisation=autorisation)
        a=charger_archive(r['archive'],C)
        self.assertIs(r['resultat'].demande.autorisation,autorisation)
        self.assertIsNone(a['resultat'].demande.autorisation)
        self.assertEqual(a['autorisation_declaree'],{'option_expresse':True,'empreinte_robot':'b'*64})
        reserve=next(b for b in charger_protocole(C).blocs if b.usage=='RESERVE')
        d['demande']=replace(a['resultat'].demande,bloc=reserve)
        with patch('xpbots.app.c1c_cli_rejeu._impl.ouvrir_ticks',side_effect=AssertionError('LECTURE_INTERDITE')) as ouvrir:
            with self.assertRaisesRegex(ValueError,'verrouill'):lancer_rejeu(C,d,self.fichier)
            ouvrir.assert_not_called()

    def test_fichier_physique_tronque_ne_produit_aucune_archive(self):
        d,lignes=demande_fixture()
        self.fichier.write_bytes(gzip.compress(''.join(lignes).encode(),mtime=0)[:-8])
        with self.assertRaisesRegex(ErreurApplication,'GZIP_INCOMPLET'):lancer_rejeu(C,d,self.fichier)

    def test_profil_aux_frais_inconnus_refuse_avant_la_lecture(self):
        d,_=demande_fixture();c=d['conditions'][0]
        d['conditions']=(replace(c,profil=replace(c.profil,commission_nulle_confirmee=False)),)
        with patch('xpbots.app.c1c_cli_rejeu._impl.ouvrir_ticks',side_effect=AssertionError('LECTURE_INTERDITE')) as ouvrir:
            with self.assertRaisesRegex(ErreurApplication,'PROFIL_C04_HISTORIQUE'):lancer_rejeu(C,d,self.fichier)
            ouvrir.assert_not_called()
