#ifndef XPBOTS_EXPORT_CALENDAR_MQH
#define XPBOTS_EXPORT_CALENDAR_MQH
#include "Atomic.mqh"
#include "TimeTable.mqh"

bool XPCalendrier(const datetime serveur,const datetime gmt,const long couverture,const XPSegment &segments[])
{
   if(gmt<86400 || serveur<=0 || couverture<=0) return false;
   long debut_utc=((long)gmt/86400-1)*86400,fin_utc=(long)gmt+couverture;
   long debut_serveur,fin_serveur;
   if(fin_utc<=(long)gmt || !XPCouverture(debut_utc,fin_utc,segments)
      || !XPServeurDepuisUTC(debut_utc,segments,debut_serveur)
      || !XPServeurDepuisUTC(fin_utc,segments,fin_serveur)) return false;
   string devises[]={"USD","EUR","GBP"},evenements="";
   ulong identifiants[];
   for(int d=0;d<ArraySize(devises);d++)
   {
      MqlCalendarValue valeurs[];
      ResetLastError();
      int n=CalendarValueHistory(valeurs,(datetime)debut_serveur,(datetime)fin_serveur,NULL,devises[d]);
      if(n<0 || GetLastError()!=0 || n>ArraySize(valeurs)) return false;
      for(int i=0;i<n;i++)
      {
         MqlCalendarEvent e;
         ResetLastError();
         if(!CalendarEventById(valeurs[i].event_id,e) || GetLastError()!=0) return false;
         if(e.importance!=CALENDAR_IMPORTANCE_HIGH) continue;
         if(e.time_mode!=CALENDAR_TIMEMODE_DATETIME || valeurs[i].time<=0 || valeurs[i].revision<0) return false;
         MqlCalendarCountry pays;
         ResetLastError();
         if(e.country_id>9223372036854775807 || !CalendarCountryById((long)e.country_id,pays) || GetLastError()!=0 || pays.currency!=devises[d]) return false;
         long heure_utc;
         if(!XPUTCDepuisServeur((long)valeurs[i].time,segments,heure_utc)) return false;
         if(heure_utc<debut_utc || heure_utc>=fin_utc) continue;
         if(valeurs[i].id==0 || valeurs[i].event_id==0 || e.event_code=="" || e.name=="") return false;
         for(int k=0;k<ArraySize(identifiants);k++) if(identifiants[k]==valeurs[i].id) return false;
         int k=ArraySize(identifiants); ArrayResize(identifiants,k+1); identifiants[k]=valeurs[i].id;
         if(evenements!="") evenements+=",";
         evenements+="{\"id_valeur\":"+StringFormat("%I64u",valeurs[i].id)
            +",\"id_evenement\":"+StringFormat("%I64u",valeurs[i].event_id)
            +",\"code\":"+XPJSON(e.event_code)+",\"nom\":"+XPJSON(e.name)
            +",\"devise\":"+XPJSON(pays.currency)+",\"importance\":"+XPJSON(EnumToString(e.importance))
            +",\"type\":"+XPJSON(EnumToString(e.type))+",\"secteur\":"+XPJSON(EnumToString(e.sector))
            +",\"heure_serveur\":"+XPJSON(TimeToString(valeurs[i].time,TIME_DATE|TIME_SECONDS))
            +",\"revision\":"+IntegerToString(valeurs[i].revision)+"}";
      }
   }
   long version;
   if(!XPReserverVersion("calendrier.json",version)) return false;
   string json="{\"schema\":\"xp-export-calendrier-v1\",\"version\":"+IntegerToString(version)
      +",\"export_serveur\":"+XPJSON(TimeToString(serveur,TIME_DATE|TIME_SECONDS))
      +",\"export_gmt\":"+XPJSON(TimeToString(gmt,TIME_DATE|TIME_SECONDS))
      +",\"fenetre_debut_serveur\":"+XPJSON(TimeToString((datetime)debut_serveur,TIME_DATE|TIME_SECONDS))
      +",\"fenetre_fin_serveur\":"+XPJSON(TimeToString((datetime)fin_serveur,TIME_DATE|TIME_SECONDS))
      +",\"evenements\":["+evenements+"]}";
   return XPEcrireAtomique("calendrier.json",json);
}

#endif
