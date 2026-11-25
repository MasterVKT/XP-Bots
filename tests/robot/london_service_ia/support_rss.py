"""Flux XML synthétiques officiels, sans accès HTTP."""
from xml.sax.saxutils import escape
from xpbots.service_ia.c0_types import iso
from .support import ressources, document


def url(issuer='FED',chemin='/synthetic/decision'):
    from urllib.parse import urlsplit
    f=next(f for f in ressources().p['feeds'] if f['issuer']==issuer)
    return 'https://'+urlsplit(f['url']).hostname+chemin


def item(texte='The committee did not decide unless conditions change.',
         publication=None,lien=None,titre='Synthetic release',sans_date=False):
    publication=publication or iso(document().publie_ms)
    date='' if sans_date else '<pubDate>'+escape(publication)+'</pubDate>'
    return ('<item><title>'+escape(titre)+'</title><link>'+escape(lien or url())+
            '</link><description>'+escape(texte)+'</description>'+date+'</item>')


def rss(*items):return ('<rss version="2.0"><channel>'+''.join(items)+'</channel></rss>').encode('utf-8')
