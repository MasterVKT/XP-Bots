"""Acces physiques de la coquille, avec refus des fichiers d'environnement."""
from pathlib import Path
from hashlib import sha256
import json
from xpbots.infra.c0a_types import ErreurInfra
from xpbots.infra.c0d_journal import lire_json,lire_octets,ecrire_atomique
from xpbots.infra.c0f_ticks import LectureTicks


def _chemin(chemin):
    try:
        p=Path(chemin)
        if p.name.casefold()=='.env' or p.name.casefold().startswith('.env.'):
            raise ErreurInfra('FICHIER_ENV_INTERDIT')
        p=p.resolve()
        if p.name.casefold()=='.env' or p.name.casefold().startswith('.env.'):
            raise ErreurInfra('FICHIER_ENV_INTERDIT')
        return p
    except (OSError,TypeError,ValueError) as e:
        if isinstance(e,ErreurInfra):raise
        raise ErreurInfra('CHEMIN_DOCUMENT_INVALIDE') from None


def lire_configuration(chemin,max_octets):
    p=_chemin(chemin)
    if p.suffix.casefold()!='.json':raise ErreurInfra('DOCUMENT_JSON_REQUIS')
    try:return lire_json(p,max_octets)
    except (OSError,ValueError):raise ErreurInfra('LECTURE_CONFIGURATION_REFUSEE') from None


def ecrire_fichier(chemin,octets,*,ecraser=False):
    p=_chemin(chemin)
    if type(ecraser) is not bool or type(octets) is not bytes:raise ErreurInfra('ECRITURE_DOCUMENT_INVALIDE')
    if p.exists() and not ecraser:raise ErreurInfra('FICHIER_EXISTANT')
    try:ecrire_atomique(p,octets)
    except (OSError,ValueError):raise ErreurInfra('ECRITURE_DOCUMENT_REFUSEE') from None


def ouvrir_ticks(chemin):
    p=_chemin(chemin)
    if p.suffixes[-len(('csv','gz')):]!=['.csv','.gz']:raise ErreurInfra('FICHIER_TICKS_GZIP_REQUIS')
    return LectureTicks(p)


def lire_fichier(chemin,max_octets,*,racine=None):
    """Octets bornés, sans décodage ; empreintes sur le fichier effectivement lu."""
    p=_chemin(chemin)
    if racine is not None:
        r=_chemin(racine)
        if not r.is_dir() or not p.is_relative_to(r):raise ErreurInfra('CHEMIN_HORS_RACINE')
    try:return lire_octets(p,max_octets)
    except (OSError,ValueError):raise ErreurInfra('LECTURE_FICHIER_REFUSEE') from None


def empreinte_robot(racine,max_octets):
    """Gel des sources et ressources d'exécution ; aucune donnée privée ou Git."""
    if type(max_octets) is not int or max_octets<=0:raise ErreurInfra('PLAFOND_GEL_INVALIDE')
    r=_chemin(racine);candidats=[]
    for dossier,suffixes in (('src/xpbots',('.py',)),('mql5',('.mq5','.mqh')),
                              ('config',('.json',)),('schemas',('.json',)),('prompts',('.json',))):
        p=r/dossier
        if not p.is_dir() or not p.resolve().is_relative_to(r):raise ErreurInfra('RACINE_ROBOT_INCOMPLETE')
        trouves=[]
        for f in p.rglob('*'):
            if f.is_symlink():raise ErreurInfra('LIEN_SOURCE_NON_QUALIFIE')
            if f.is_file() and f.suffix.casefold() in suffixes:trouves.append(f)
        if not trouves:raise ErreurInfra('RACINE_ROBOT_INCOMPLETE')
        candidats.extend(trouves)
    total=0;fichiers=[]
    for f in sorted(candidats,key=lambda p:p.relative_to(r).as_posix()):
        b=lire_fichier(f,max(1,max_octets-total),racine=r);total+=len(b)
        if total>max_octets:raise ErreurInfra('PLAFOND_GEL_DEPASSE')
        fichiers.append((f.relative_to(r).as_posix(),sha256(b).hexdigest()))
    corps=json.dumps(dict(schema='xp-empreinte-robot-v1',fichiers=fichiers),
                     ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
    return dict(schema='xp-empreinte-robot-v1',sha256=sha256(corps).hexdigest(),fichiers=tuple(fichiers),octets=total)
