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


from robot.points_entree.test_cat1_c1c_rejeu import HarnaisCommandeRejeu

class TestJonctionCommandeRejeu(HarnaisCommandeRejeu,unittest.TestCase):
    def test_archive_du_vrai_london_rejouee_sans_backend(self):
        d,lignes=demande_fixture(london=True)
        r=self.executer(d,lignes);archive=charger_archive(r['archive'],C)
        self.assertIsNone(archive['resultat'].demande.autorisation)
        self.assertEqual(archive['resultat'].pilote.entrees,r['resultat'].pilote.entrees)
        self.assertEqual(r['rapport']['statut'],'NON_VALIDE')
        c=archive['controles']
        rejoues,entrees,_=rejouer_experience(archive['resultat'],fabrique_controles=
            fabriquer_controles(C,c['scenario'],c['receptions'],c['table_heure']))
        self.assertEqual(tuple(serialiser(e) for e in rejoues),
                         tuple(serialiser(e) for e in r['resultat'].pilote.enregistrements))
        self.assertEqual(entrees,r['resultat'].pilote.entrees)

    def test_permissions_et_calendrier_historiques_recoivent_leurs_vrais_instants(self):
        from robot.outils.fondamental import message,calendrier,octets,table_importance
        d,lignes=demande_fixture();t=d['manifeste'].intervalle.debut_ms
        iso=instant_vers_iso
        d['scenario_fondamental']=None
        d['table_heure']=dict(schema='xp-heure-serveur-v1',serveur='SERVEUR_FIXTURE',version=1,
            date_releve=iso(t),mesures=['S01_SYNTHETIQUE_NON_QUALIFIE'],segments=[
                dict(debut_utc=iso(t-86400000),fin_utc=iso(t+86400000*8),decalage_secondes=7200)])
        permission=message(issued_at_utc=iso(t),known_at_utc=iso(t),valid_from_utc=iso(t),
            valid_until_utc=iso(t+int(C.technique.commun.fundamental_max_validity_seconds*1000)))
        d['receptions']=((t,ReceptionExterne('PERMISSION',octets(permission),symbole='EURUSD')),
                         (t,ReceptionExterne('CALENDRIER',octets(calendrier(export_ms=t)),table=table_importance())))
        r=self.executer(d,lignes)
        self.assertEqual(r['resultat'].regime_fondamental,'PERMISSIONS_EXTERNES')
        recus=tuple((e.entree.instant_ms,p.nature) for e in r['resultat'].pilote.entrees for p in e.entree.receptions)
        self.assertEqual(recus,((t,'PERMISSION'),(t,'CALENDRIER')))
        self.assertEqual(r['rapport']['statut'],'NON_VALIDE')
