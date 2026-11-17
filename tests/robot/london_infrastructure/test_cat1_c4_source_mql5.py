"""Source MQL5 : convention de modules et frontières, compilation réservée à 13.1."""
from pathlib import Path
import re
import unittest

RACINE = Path(__file__).resolve().parents[3]


class TestSourceMQL5(unittest.TestCase):
    def source(self, nom):
        return (RACINE/'mql5/Services'/nom).read_text(encoding='utf-8')

    def test_service_onstart_et_aucun_ordre_ou_reseau(self):
        main = self.source('XPBotsExport.mq5')
        self.assertIn('#property service', main)
        self.assertIn('void OnStart()', main)
        self.assertIn('while(!IsStopped())', main)
        self.assertNotIn('OnTimer', main)
        self.assertIn('Sleep(100)', main)
        for fichier in (RACINE/'mql5/Services').rglob('*'):
            if fichier.suffix not in ('.mq5', '.mqh'): continue
            texte = fichier.read_text(encoding='utf-8')
            self.assertFalse(re.search(r'\b(OrderSend|WebRequest|OrderCheck|CopyRates|iMA|iRSI)\s*\(', texte), fichier)
            self.assertNotIn('#import', texte)

    def test_includes_etat_mutable_dans_main_uniquement(self):
        attendu = {'XPBotsExport.mq5': {'Atomic', 'TimeTable', 'Calendar', 'Sessions'},
                   'XPBotsExport/Atomic.mqh': set(), 'XPBotsExport/TimeTable.mqh': {'Atomic'},
                   'XPBotsExport/Calendar.mqh': {'Atomic', 'TimeTable'}, 'XPBotsExport/Sessions.mqh': {'Atomic'}}
        for nom, imports in attendu.items():
            s = self.source(nom)
            self.assertEqual(set(re.findall(r'#include "(?:XPBotsExport/)?([A-Za-z]+)\.mqh"', s)), imports)
            # Les déclarations au niveau module sont uniquement propriétés/input/types/fonctions.
            self.assertFalse(re.search(r'^(?:int|long|ulong|bool|string|datetime)\s+\w+\s*=', s, re.M), nom)

    def test_ecriture_utf8_flush_fermeture_remplacement_et_reservation(self):
        s = self.source('XPBotsExport/Atomic.mqh')
        self.assertIn('StringToCharArray(texte,octets,0,WHOLE_ARRAY,CP_UTF8)', s)
        self.assertIn('FileWriteArray(f,octets,0,taille-1)', s)
        self.assertLess(s.index('FileFlush(f)'), s.index('FileClose(f)'))
        self.assertLess(s.index('FileClose(f)'), s.index('FileMove('))
        self.assertIn('FILE_COMMON|FILE_REWRITE', s)
        self.assertIn('version=precedente+1', s)
        self.assertIn('XPEcrireAtomique(ledger,', s)
        self.assertIn('if(publication ||', s)
        main = self.source('XPBotsExport.mq5')
        self.assertIn('execution.lock', main)
        self.assertNotIn('FILE_SHARE_WRITE', main)
        for nom in ('Calendar', 'Sessions'):
            s = self.source('XPBotsExport/'+nom+'.mqh')
            self.assertLess(s.index('XPReserverVersion('), s.index('return XPEcrireAtomique('))

    def test_native_calendrier_complet_heure_qualifiee_et_seances_separees(self):
        c = self.source('XPBotsExport/Calendar.mqh')
        self.assertIn('CalendarValueHistory(valeurs,', c)
        self.assertIn('n<0 || GetLastError()!=0', c)
        self.assertIn('CALENDAR_IMPORTANCE_HIGH', c)
        self.assertIn('CALENDAR_TIMEMODE_DATETIME', c)
        self.assertIn('CalendarCountryById(', c)
        self.assertIn('XPCouverture(debut_utc,fin_utc,segments)', c)
        self.assertIn('XPUTCDepuisServeur(', c)
        self.assertNotIn('TimeTradeServer()-TimeGMT()', c)
        s = self.source('XPBotsExport/Sessions.mqh')
        self.assertIn('SymbolInfoSessionQuote(', s); self.assertIn('SymbolInfoSessionTrade(', s)
        self.assertIn('ERR_MARKET_SESSION_INDEX', s)
        self.assertIn('jour<7', s)
        self.assertIn('SymbolIsSynchronized', s)
