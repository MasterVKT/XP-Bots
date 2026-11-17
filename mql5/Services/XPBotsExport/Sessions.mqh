#ifndef XPBOTS_EXPORT_SESSIONS_MQH
#define XPBOTS_EXPORT_SESSIONS_MQH
#include "Atomic.mqh"

string XPHeureSeance(const datetime valeur,const bool fin)
{
   // L’API donne une heure de la journée ; seule la fin 86400 représente 24:00.
   if(fin && (long)valeur==86400) return "24:00:00";
   return TimeToString(valeur,TIME_SECONDS);
}

bool XPIntervalles(const string symbole,const ENUM_DAY_OF_WEEK jour,const bool cotation,string &json)
{
   json="[";
   for(uint indice=0;;indice++)
   {
      datetime debut,fin;
      ResetLastError();
      bool ok=cotation ? SymbolInfoSessionQuote(symbole,jour,indice,debut,fin)
                       : SymbolInfoSessionTrade(symbole,jour,indice,debut,fin);
      if(!ok)
      {
         int erreur=GetLastError();
         if(erreur!=0 && erreur!=ERR_MARKET_SESSION_INDEX) return false;
         break;
      }
      if(indice>0) json+=",";
      json+="{\"debut\":"+XPJSON(XPHeureSeance(debut,false))+",\"fin\":"+XPJSON(XPHeureSeance(fin,true))+"}";
      if(indice==UINT_MAX) return false;
   }
   json+="]";
   return true;
}

bool XPSeances(const string symbole,const datetime serveur,const datetime gmt)
{
   if(!XPNomSur(symbole) || !SymbolSelect(symbole,true) || !SymbolIsSynchronized(symbole)) return false;
   string jours="";
   for(int jour=0;jour<7;jour++)
   {
      string cotation,negociation;
      if(!XPIntervalles(symbole,(ENUM_DAY_OF_WEEK)jour,true,cotation)
         || !XPIntervalles(symbole,(ENUM_DAY_OF_WEEK)jour,false,negociation)) return false;
      if(jour>0) jours+=",";
      jours+="{\"jour\":"+IntegerToString(jour)+",\"cotation\":"+cotation+",\"negociation\":"+negociation+"}";
   }
   string nom="seances_"+symbole+".json";
   long version;
   if(!XPReserverVersion(nom,version)) return false;
   string json="{\"schema\":\"xp-export-seances-v1\",\"version\":"+IntegerToString(version)
      +",\"export_serveur\":"+XPJSON(TimeToString(serveur,TIME_DATE|TIME_SECONDS))
      +",\"export_gmt\":"+XPJSON(TimeToString(gmt,TIME_DATE|TIME_SECONDS))
      +",\"symbole\":"+XPJSON(symbole)+",\"jours\":["+jours+"]}";
   return XPEcrireAtomique(nom,json);
}

#endif
