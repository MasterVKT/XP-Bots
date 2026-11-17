#ifndef XPBOTS_EXPORT_TIMETABLE_MQH
#define XPBOTS_EXPORT_TIMETABLE_MQH
#include "Atomic.mqh"

struct XPSegment
{
   long debut_utc;
   long fin_utc;
   long decalage_secondes;
};

bool XPServeurDepuisUTC(const long utc,const XPSegment &segments[],long &serveur)
{
   for(int i=0;i<ArraySize(segments);i++)
      if(segments[i].debut_utc<=utc && utc<segments[i].fin_utc)
      { serveur=utc+segments[i].decalage_secondes; return serveur>=0; }
   return false;
}

bool XPUTCDepuisServeur(const long serveur,const XPSegment &segments[],long &utc)
{
   int candidats=0;
   for(int i=0;i<ArraySize(segments);i++)
   {
      long t=serveur-segments[i].decalage_secondes;
      if(segments[i].debut_utc<=t && t<segments[i].fin_utc) { utc=t; candidats++; }
   }
   return candidats==1;
}

bool XPCouverture(const long debut,const long fin,const XPSegment &segments[])
{
   long curseur=debut;
   for(int i=0;i<ArraySize(segments) && curseur<fin;i++)
   {
      if(segments[i].fin_utc<=curseur) continue;
      if(segments[i].debut_utc>curseur) return false;
      curseur=segments[i].fin_utc;
   }
   return curseur>=fin;
}

bool XPParametres(const string fichier,string &serveur,long &version_table,long &couverture,
                 XPSegment &segments[],string &symboles[])
{
   if(!XPNomSur(fichier)) return false;
   string texte;
   if(!XPLireTexte(fichier,131072,texte) || StringFind(texte,"\r")>=0 || StringSubstr(texte,StringLen(texte)-1)!="\n") return false;
   string lignes[];
   StringSplit(StringSubstr(texte,0,StringLen(texte)-1),'\n',lignes);
   if(ArraySize(lignes)<6 || lignes[0]!="schema\txp-parametres-export-v1") return false;
   string champs[];
   if(StringSplit(lignes[1],'\t',champs)!=2 || champs[0]!="serveur" || champs[1]=="") return false;
   serveur=champs[1];
   if(StringSplit(lignes[2],'\t',champs)!=2 || champs[0]!="version_table" || !XPEntier(champs[1],version_table) || version_table<=0) return false;
   if(StringSplit(lignes[3],'\t',champs)!=2 || champs[0]!="couverture_future_secondes" || !XPEntier(champs[1],couverture) || couverture<=0) return false;
   bool symboles_commences=false;
   for(int i=4;i<ArraySize(lignes);i++)
   {
      int n=StringSplit(lignes[i],'\t',champs);
      if(n==4 && champs[0]=="segment" && !symboles_commences)
      {
         XPSegment s;
         if(!XPEntier(champs[1],s.debut_utc) || !XPEntier(champs[2],s.fin_utc) || !XPEntier(champs[3],s.decalage_secondes,true) || s.fin_utc<=s.debut_utc) return false;
         int k=ArraySize(segments);
         if(k>0 && segments[k-1].fin_utc>s.debut_utc) return false;
         ArrayResize(segments,k+1); segments[k]=s;
      }
      else if(n==2 && champs[0]=="symbole" && XPNomSur(champs[1]))
      {
         symboles_commences=true;
         for(int k=0;k<ArraySize(symboles);k++) if(symboles[k]==champs[1]) return false;
         int k=ArraySize(symboles); ArrayResize(symboles,k+1); symboles[k]=champs[1];
      }
      else return false;
   }
   return ArraySize(segments)>0 && ArraySize(symboles)>0;
}

#endif
