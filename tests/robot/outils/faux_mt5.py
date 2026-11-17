"""Frontière externe MT5 de test, constantes issues du texte officiel épinglé."""
from collections import namedtuple, defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
import json
import numpy as np

_FAITS = json.loads((Path(__file__).resolve().parents[1]/'fixtures/mt5_5_0_6231_constantes.json').read_text(encoding='utf-8'))
globals().update(_FAITS['constantes'])
AccountInfo = namedtuple('AccountInfo', 'trade_mode leverage margin_mode currency balance equity margin margin_free margin_level margin_so_mode margin_so_call margin_so_so trade_allowed trade_expert limit_orders company server login', defaults=(None,)*18)
TerminalInfo = namedtuple('TerminalInfo', 'connected trade_allowed tradeapi_disabled commondata_path build', defaults=(None,)*5)
SymbolInfo = namedtuple('SymbolInfo', 'name trade_tick_size point digits trade_contract_size trade_tick_value volume_min volume_max volume_step volume_limit trade_stops_level trade_freeze_level filling_mode order_mode trade_mode trade_exemode trade_calc_mode currency_base currency_profit currency_margin chart_mode margin_initial margin_maintenance spread_float swap_long swap_short', defaults=(None,)*26)
TickInfo = namedtuple('Tick', 'time bid ask last volume time_msc flags volume_real', defaults=(0,)*8)
TradePosition = namedtuple('TradePosition', 'ticket time time_msc time_update time_update_msc type magic identifier reason volume price_open sl tp price_current swap profit symbol comment external_id', defaults=(None,)*19)
TradeOrder = namedtuple('TradeOrder', 'ticket time_setup time_setup_msc time_done time_done_msc time_expiration type type_time type_filling state magic position_id position_by_id reason volume_initial volume_current price_open sl tp price_current price_stoplimit symbol comment external_id', defaults=(None,)*24)
TradeDeal = namedtuple('TradeDeal', 'ticket order time time_msc type entry magic position_id reason volume price commission swap profit fee symbol comment external_id', defaults=(None,)*18)
OrderSendResult = namedtuple('OrderSendResult', 'retcode deal order volume price bid ask comment request_id retcode_external request', defaults=(None,)*11)
OrderCheckResult = namedtuple('OrderCheckResult', 'retcode balance equity profit margin margin_free margin_level comment request', defaults=(None,)*9)
TICK_DTYPE = [('time', 'i8'), ('bid', 'f8'), ('ask', 'f8'), ('last', 'f8'), ('volume', 'u8'), ('time_msc', 'i8'), ('flags', 'u4'), ('volume_real', 'f8')]


class FauxMT5:
    __version__ = _FAITS['version']

    def __init__(self, dossier_commun='COMMON_FIXTURE', instant_ms=1794268800000):
        self.appels = []
        self.scenarios = defaultdict(deque)
        self.erreur = (RES_S_OK, 'succès synthétique')
        self.compte = AccountInfo(ACCOUNT_TRADE_MODE_DEMO, 100, ACCOUNT_MARGIN_MODE_RETAIL_HEDGING, 'USD', 100., 100., 0., 100., 0., ACCOUNT_STOPOUT_MODE_PERCENT, 100., 50., True, True, 200, 'COURTIER_FIXTURE', 'SERVEUR_FIXTURE', 123456789)
        self.terminal = TerminalInfo(True, True, False, str(dossier_commun), 6231)
        self.symboles = {'EURUSD.micro': SymbolInfo('EURUSD.micro', .00001, .00001, 5, 1000., .01, .1, 50., .01, 0., 0, 0, 3, 127, SYMBOL_TRADE_MODE_FULL, SYMBOL_TRADE_EXECUTION_MARKET, SYMBOL_CALC_MODE_FOREX, 'EUR', 'USD', 'EUR', SYMBOL_CHART_MODE_BID, 0., 0., True, -.5, .1)}
        self.ticks = defaultdict(list)
        self.positions = []
        self.ordres = []
        self.historique_ordres = []
        self.transactions = []
        self.instant_ms = instant_ms
        self._ticket = 100
        self.attache = False

    def _appel(self, nom, args, kw, defaut):
        self.appels.append((nom, args, dict(kw)))
        if self.scenarios[nom]:
            v = self.scenarios[nom].popleft()
            if isinstance(v, BaseException): raise v
            return v(*args, **kw) if callable(v) else v
        return defaut() if callable(defaut) else defaut

    def initialize(self, *args, **kwargs):
        if any(k in kwargs for k in ('login', 'password', 'server')):
            raise AssertionError('identifiants interdits')
        r = self._appel('initialize', args, kwargs, True); self.attache = bool(r); return r

    def login(self, *args, **kwargs):
        raise AssertionError('login interdit par D02')

    def copy_rates_from(self, *args, **kwargs): raise AssertionError('bougies natives interdites pour décider')
    def copy_rates_from_pos(self, *args, **kwargs): raise AssertionError('bougies natives interdites pour décider')
    def copy_rates_range(self, *args, **kwargs): raise AssertionError('bougies natives interdites pour décider')
    def market_book_add(self, symbol): return self._appel('market_book_add', (symbol,), {}, False)
    def market_book_get(self, symbol): return self._appel('market_book_get', (symbol,), {}, None)
    def market_book_release(self, symbol): return self._appel('market_book_release', (symbol,), {}, True)
    def positions_total(self): return self._appel('positions_total', (), {}, len(self.positions))
    def orders_total(self): return self._appel('orders_total', (), {}, len(self.ordres))
    def history_orders_total(self, date_from, date_to): return self._appel('history_orders_total', (date_from, date_to), {}, len(self.historique_ordres))
    def history_deals_total(self, date_from, date_to): return self._appel('history_deals_total', (date_from, date_to), {}, len(self.transactions))

    def shutdown(self):
        self.attache = False
        return self._appel('shutdown', (), {}, None)

    def version(self): return self._appel('version', (), {}, (500, 6231, '10 Nov 2026'))
    def last_error(self): return self._appel('last_error', (), {}, self.erreur)
    def account_info(self): return self._appel('account_info', (), {}, self.compte)
    def terminal_info(self): return self._appel('terminal_info', (), {}, self.terminal)
    def symbols_total(self): return self._appel('symbols_total', (), {}, len(self.symboles))
    def symbols_get(self, group=None): return self._appel('symbols_get', (), {} if group is None else {'group': group}, tuple(self.symboles.values()))
    def symbol_select(self, symbol, enable): return self._appel('symbol_select', (symbol, enable), {}, symbol in self.symboles)
    def symbol_info(self, symbol): return self._appel('symbol_info', (symbol,), {}, self.symboles.get(symbol))

    def symbol_info_tick(self, symbol):
        def defaut():
            if not self.ticks[symbol]: return None
            t = self.ticks[symbol][-1]
            return TickInfo(t[0]//1000, t[1], t[2], 0., 0, t[0], t[3], 0.)
        return self._appel('symbol_info_tick', (symbol,), {}, defaut)

    def ajouter_tick(self, symbol, ms, bid, ask, flags=None):
        self.ticks[symbol].append((ms, bid, ask, TICK_FLAG_BID|TICK_FLAG_ASK if flags is None else flags))

    def _tableau(self, symbol, debut, fin=None, count=None):
        if debut.tzinfo is None or fin is not None and fin.tzinfo is None:
            raise AssertionError('requête datetime UTC aware requise')
        a = int(debut.timestamp()*1000); b = None if fin is None else int(fin.timestamp()*1000)
        lignes = [(ms//1000, bid, ask, 0., 0, ms, flags, 0.) for ms, bid, ask, flags in self.ticks[symbol] if ms >= a and (b is None or ms <= b)]
        return np.array(lignes if count is None else lignes[:count], dtype=TICK_DTYPE)

    def copy_ticks_from(self, symbol, date_from, count, flags):
        if flags != COPY_TICKS_ALL: raise AssertionError('COPY_TICKS_ALL requis')
        return self._appel('copy_ticks_from', (symbol, date_from, count, flags), {}, lambda: self._tableau(symbol, date_from, count=count))

    def copy_ticks_range(self, symbol, date_from, date_to, flags):
        if flags != COPY_TICKS_ALL: raise AssertionError('COPY_TICKS_ALL requis')
        return self._appel('copy_ticks_range', (symbol, date_from, date_to, flags), {}, lambda: self._tableau(symbol, date_from, date_to))

    def order_calc_profit(self, action, symbol, volume, price_open, price_close):
        return self._appel('order_calc_profit', (action, symbol, volume, price_open, price_close), {},
            lambda: (price_close-price_open)*self.symboles[symbol].trade_contract_size*volume*(1 if action == ORDER_TYPE_BUY else -1))

    def order_calc_margin(self, action, symbol, volume, price):
        return self._appel('order_calc_margin', (action, symbol, volume, price), {}, lambda: self.symboles[symbol].trade_contract_size*volume*price/self.compte.leverage)

    def order_check(self, request):
        return self._appel('order_check', (request,), {}, lambda: OrderCheckResult(0, self.compte.balance, self.compte.equity, 0., self.compte.margin+1., self.compte.margin_free-1., 10000., 'fixture', request))

    def order_send(self, request):
        def defaut():
            self._ticket += 1; ticket = self._ticket
            if request['action'] == TRADE_ACTION_SLTP:
                self.positions = [p._replace(sl=request['sl'], tp=request['tp']) if p.ticket == request['position'] else p for p in self.positions]
            elif request['action'] == TRADE_ACTION_REMOVE:
                self.ordres = [o for o in self.ordres if o.ticket != request['order']]
            else:
                position = request.get('position', ticket)
                entree = DEAL_ENTRY_OUT if 'position' in request else DEAL_ENTRY_IN
                self.transactions.append(TradeDeal(ticket=ticket, order=ticket, time=self.instant_ms//1000, time_msc=self.instant_ms,
                    type=request['type'], entry=entree, magic=request.get('magic', 0), position_id=position, reason=DEAL_REASON_EXPERT,
                    volume=request['volume'], price=request['price'], commission=0., swap=0., profit=0., fee=0., symbol=request['symbol'], comment=request.get('comment', ''), external_id=''))
                if entree == DEAL_ENTRY_IN:
                    self.positions.append(TradePosition(ticket=position, identifier=position, type=request['type'], magic=request['magic'],
                        volume=request['volume'], price_open=request['price'], sl=request['sl'], tp=request['tp'], time_msc=self.instant_ms,
                        symbol=request['symbol'], comment=request['comment'], reason=POSITION_REASON_EXPERT))
                else:
                    self.positions = [p._replace(volume=max(0., p.volume-request['volume'])) if p.ticket == position else p for p in self.positions]
                    self.positions = [p for p in self.positions if p.volume > 0]
            return OrderSendResult(retcode=TRADE_RETCODE_DONE, deal=ticket, order=ticket, volume=request.get('volume', 0.), price=request.get('price', 0.), request=request)
        return self._appel('order_send', (request,), {}, defaut)

    def positions_get(self, *, symbol=None, group=None, ticket=None):
        kw = {k: v for k, v in dict(symbol=symbol, group=group, ticket=ticket).items() if v is not None}
        return self._appel('positions_get', (), kw, tuple(p for p in self.positions if (symbol is None or p.symbol == symbol) and (ticket is None or p.ticket == ticket)))

    def orders_get(self, *, symbol=None, group=None, ticket=None):
        kw = {k: v for k, v in dict(symbol=symbol, group=group, ticket=ticket).items() if v is not None}
        return self._appel('orders_get', (), kw, tuple(o for o in self.ordres if (symbol is None or o.symbol == symbol) and (ticket is None or o.ticket == ticket)))

    def history_orders_get(self, date_from=None, date_to=None, *, group=None, ticket=None, position=None):
        kw = {k: v for k, v in dict(group=group, ticket=ticket, position=position).items() if v is not None}
        return self._appel('history_orders_get', (date_from, date_to), kw, tuple(o for o in self.historique_ordres if (ticket is None or o.ticket == ticket) and (position is None or o.position_id == position)))

    def history_deals_get(self, date_from=None, date_to=None, *, group=None, ticket=None, position=None):
        kw = {k: v for k, v in dict(group=group, ticket=ticket, position=position).items() if v is not None}
        return self._appel('history_deals_get', (date_from, date_to), kw, tuple(t for t in self.transactions if (ticket is None or t.ticket == ticket) and (position is None or t.position_id == position)))


for _nom, _valeur in _FAITS['constantes'].items():
    setattr(FauxMT5, _nom, _valeur)
