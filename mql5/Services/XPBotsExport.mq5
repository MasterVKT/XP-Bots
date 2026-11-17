#property service
#property version "1.00"
#property description "Export D12 uniquement : calendrier HIGH et séances ; aucun trading."

#include "XPBotsExport/Atomic.mqh"
#include "XPBotsExport/TimeTable.mqh"
#include "XPBotsExport/Calendar.mqh"
#include "XPBotsExport/Sessions.mqh"

input string FichierParametres="parametres_service.tsv";

void OnStart()
{
   // Verrou exclusif détenu jusqu’à l’arrêt : deux services ne réservent pas la même version.
   int verrou=FileOpen(XPRacine()+"execution.lock",FILE_READ|FILE_WRITE|FILE_BIN|FILE_COMMON);
   if(verrou==INVALID_HANDLE) { Print("XPBOTS_EXPORT_VERROU_INDISPONIBLE"); return; }
   string serveur,symboles[];
   XPSegment segments[];
   long version_table,couverture;
   if(!XPParametres(FichierParametres,serveur,version_table,couverture,segments,symboles)
      || serveur!=AccountInfoString(ACCOUNT_SERVER))
   {
      Print("XPBOTS_EXPORT_PARAMETRES_INVALIDES");
      FileClose(verrou);
      return;
   }
   ulong prochain_calendrier=0,prochaines_seances=0;
   while(!IsStopped())
   {
      ulong maintenant=GetTickCount64();
      if(TerminalInfoInteger(TERMINAL_CONNECTED))
      {
         datetime gmt=TimeGMT(),heure_serveur=TimeTradeServer();
         long controle;
         bool couvert=XPServeurDepuisUTC((long)gmt,segments,controle);
         if(couvert && maintenant>=prochain_calendrier)
         {
            if(!XPCalendrier(heure_serveur,gmt,couverture,segments)) Print("XPBOTS_EXPORT_CALENDRIER_ECHEC");
            prochain_calendrier=GetTickCount64()+60000;
         }
         if(couvert && maintenant>=prochaines_seances)
         {
            for(int i=0;i<ArraySize(symboles);i++)
               if(!XPSeances(symboles[i],heure_serveur,gmt)) Print("XPBOTS_EXPORT_SEANCES_ECHEC");
            prochaines_seances=GetTickCount64()+3600000;
         }
      }
      Sleep(100);
   }
   FileClose(verrou);
}
