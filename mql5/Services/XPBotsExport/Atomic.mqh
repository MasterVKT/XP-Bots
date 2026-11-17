#ifndef XPBOTS_EXPORT_ATOMIC_MQH
#define XPBOTS_EXPORT_ATOMIC_MQH

// Toutes les écritures restent dans cette seule racine FILE_COMMON.
string XPRacine() { return "XPBots\\export\\v1\\"; }

bool XPNomSur(const string nom)
{
   if(StringLen(nom)==0 || nom=="." || nom=="..") return false;
   string interdits="/\\:\"<>|?*";
   for(int i=0;i<StringLen(nom);i++)
   {
      ushort c=StringGetCharacter(nom,i);
      if(c<32 || StringFind(interdits,ShortToString(c))>=0) return false;
   }
   ushort fin=StringGetCharacter(nom,StringLen(nom)-1);
   return fin!='.' && fin!=' ';
}

bool XPEntier(const string texte,long &valeur,const bool signe=false)
{
   int n=StringLen(texte),debut=0; bool negatif=false;
   if(n==0) return false;
   if(signe && StringGetCharacter(texte,0)=='-') { negatif=true; debut=1; }
   if(debut==n || (n-debut>1 && StringGetCharacter(texte,debut)=='0')) return false;
   long v=0;
   for(int i=debut;i<n;i++)
   {
      int chiffre=(int)StringGetCharacter(texte,i)-'0';
      if(chiffre<0 || chiffre>9 || v>(9223372036854775807-chiffre)/10) return false;
      v=v*10+chiffre;
   }
   valeur=negatif ? -v : v;
   return true;
}

string XPJSON(const string texte)
{
   string r="\"";
   for(int i=0;i<StringLen(texte);i++)
   {
      ushort c=StringGetCharacter(texte,i);
      if(c=='"') r+="\\\"";
      else if(c=='\\') r+="\\\\";
      else if(c<32) r+=StringFormat("\\u%04x",(int)c);
      else r+=ShortToString(c);
   }
   return r+"\"";
}

bool XPEcrireAtomique(const string nom,const string texte)
{
   if(!XPNomSur(nom)) return false;
   uchar octets[];
   int taille=StringToCharArray(texte,octets,0,WHOLE_ARRAY,CP_UTF8);
   if(taille<=0) return false;
   string temporaire=XPRacine()+nom+".tmp";
   ResetLastError();
   int f=FileOpen(temporaire,FILE_WRITE|FILE_BIN|FILE_COMMON);
   if(f==INVALID_HANDLE) return false;
   uint ecrits=FileWriteArray(f,octets,0,taille-1); // aucun NUL terminal
   FileFlush(f);
   int erreur=GetLastError();
   FileClose(f);
   if(ecrits!=(uint)(taille-1) || erreur!=0) return false;
   ResetLastError();
   return FileMove(temporaire,FILE_COMMON,XPRacine()+nom,FILE_COMMON|FILE_REWRITE);
}

bool XPLireTexte(const string nom,const int plafond,string &texte)
{
   if(!XPNomSur(nom) || plafond<=0) return false;
   int f=FileOpen(XPRacine()+nom,FILE_READ|FILE_BIN|FILE_COMMON|FILE_SHARE_READ);
   if(f==INVALID_HANDLE) return false;
   ulong taille=FileSize(f);
   if(taille==0 || taille>(ulong)plafond) { FileClose(f); return false; }
   uchar octets[]; ArrayResize(octets,(int)taille);
   uint lus=FileReadArray(f,octets,0,(int)taille);
   FileClose(f);
   if(lus!=(uint)taille) return false;
   texte=CharArrayToString(octets,0,(int)taille,CP_UTF8);
   uchar retour[];
   int n=StringToCharArray(texte,retour,0,WHOLE_ARRAY,CP_UTF8);
   if(n!=(int)taille+1) return false;
   for(int i=0;i<(int)taille;i++) if(octets[i]!=retour[i]) return false;
   return true;
}

bool XPReserverVersion(const string nom,long &version)
{
   if(!XPNomSur(nom)) return false;
   string ledger=nom+".version";
   ResetLastError();
   bool existe=FileIsExist(XPRacine()+ledger,FILE_COMMON);
   int erreur_existence=GetLastError();
   if(!existe && erreur_existence!=0 && erreur_existence!=ERR_FILE_NOT_EXIST) return false;
   long precedente=0;
   if(existe)
   {
      string texte,prefixe="xp-export-version-v1\n";
      if(!XPLireTexte(ledger,128,texte) || StringFind(texte,prefixe)!=0 || StringSubstr(texte,StringLen(texte)-1)!="\n") return false;
      string numero=StringSubstr(texte,StringLen(prefixe),StringLen(texte)-StringLen(prefixe)-1);
      if(!XPEntier(numero,precedente) || precedente<=0) return false;
   }
   else
   {
      ResetLastError();
      bool publication=FileIsExist(XPRacine()+nom,FILE_COMMON);
      erreur_existence=GetLastError();
      if(publication || (erreur_existence!=0 && erreur_existence!=ERR_FILE_NOT_EXIST)) return false;
   }
   if(precedente==9223372036854775807) return false;
   version=precedente+1;
   // Réservation durable avant publication : un saut est admis, jamais un retour.
   return XPEcrireAtomique(ledger,"xp-export-version-v1\n"+IntegerToString(version)+"\n");
}

#endif
