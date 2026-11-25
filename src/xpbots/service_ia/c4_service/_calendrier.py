"""D12 physique et disponibilités causales ; aucune donnée de compte lue."""
from pathlib import Path
from threading import RLock
from dataclasses import asdict
from xpbots.infra.c0d_journal import lire_octets
from xpbots.fondamental.c0_types import TableImportance
from xpbots.fondamental.c1b_annonces import GardeAnnonces
from xpbots.service_ia.c0_types import ErreurService, canonique, decoder, empreinte, instant, entier
from xpbots.service_ia.c2a_veto import TableAppariement


class CalendrierService:
    def __init__(self,ressources,depot,chemin,convertir_serveur,table_importance,table_appariement,horloge,*,max_octets):
        if not isinstance(table_importance,TableImportance) or not isinstance(table_appariement,TableAppariement):
            raise ErreurService('TABLES_CALENDRIER_REQUISES')
        entier(max_octets,1)
        self.depot=depot;self.chemin=Path(chemin);self.h=horloge;self.max=max_octets
        self.importance=table_importance;self.mapping=table_appariement;self._lock=RLock()
        self._commun=ressources.configuration.technique.commun;self._convertir=convertir_serveur
        self.garde=GardeAnnonces(ressources.configuration.technique.commun,convertir_serveur);self._statuts=[]
        lignes=depot.transaction(lambda t:tuple(v for k,v in t['feed_state'].items() if k.startswith('calendar:')))
        compteur=depot.transaction(lambda t:t['schedule_state'].get('calendar_sequence'))
        if (lignes or compteur is not None) and (type(compteur) is not dict
                or type(compteur.get('sequence')) is not int or compteur['sequence']!=len(lignes)):
            raise ErreurService('COMPTEUR_CALENDRIER_PERDU')
        sequences=[]
        for v in sorted(lignes,key=lambda v:v['sequence']):
            entier(v['sequence'],1);instant(v['known_at_ms']);sequences.append(v['sequence'])
            if v['sequence']!=len(sequences) or self._statuts and v['known_at_ms']<self._statuts[-1][0]:
                raise ErreurService('HISTORIQUE_CALENDRIER_EN_RECUL')
            if v['raw'] is not None:
                table=TableImportance(**v['importance'])
                reception=self.garde.recevoir(bytes.fromhex(v['raw']),v['known_at_ms'],table)
                if not (reception.acceptee or reception.ignoree):raise ErreurService('HISTORIQUE_CALENDRIER_INVALIDE')
            self._statuts.append((v['known_at_ms'],v['available']))

    def actualiser(self):
        now=instant(self.h.maintenant_ms());b=None
        try:b=lire_octets(self.chemin,self.max)
        except (OSError,ValueError):pass
        with self._lock:
            if self._statuts and now<self._statuts[-1][0]:raise ErreurService('CALENDRIER_EN_RECUL')
            candidat=GardeAnnonces(self._commun,self._convertir,self.garde.etat)
            resultat=candidat.recevoir(b,now,self.importance) if b is not None else None
            valide=resultat is not None and (resultat.acceptee or resultat.ignoree)
            nouvelle=resultat is not None and resultat.acceptee
            if not self._statuts or self._statuts[-1][1]!=valide or nouvelle:
                importance=dict(fournisseur=self.importance.fournisseur,version=self.importance.version,hautes=sorted(self.importance.hautes))
                ligne=dict(known_at_ms=now,available=valide,raw=b.hex() if nouvelle else None,
                    importance=importance,mapping=asdict(self.mapping))
                def archiver(t):
                    compteur=t['schedule_state'].setdefault('calendar_sequence',dict(sequence=0))
                    entier(compteur['sequence']);compteur['sequence']+=1
                    ligne['sequence']=compteur['sequence']
                    t['feed_state']['calendar:'+str(ligne['sequence'])]=ligne
                self.depot.transaction(archiver)
                self.garde=candidat
                self._statuts.append((now,valide))
            return valide

    def __call__(self,t):
        instant(t)
        with self._lock:
            disponible=next((ok for connu,ok in reversed(self._statuts) if connu<=t),False)
            return self.garde,self.mapping,disponible
