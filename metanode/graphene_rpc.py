#!/usr/bin/env python
# DISABLE SELECT PYLINT TESTS
# pylint: disable=import-error, broad-except, bad-continuation, line-too-long
# pylint: disable=too-many-locals, too-many-public-methods, too-many-function-args
# pylint: disable=too-many-lines, method-hidden
r"""
 ╔════════════════════════════════════════════════════╗
 ║ ╔═╗╦═╗╔═╗╔═╗╦ ╦╔═╗╔╗╔╔═╗  ╔╦╗╔═╗╔╦╗╔═╗╔╗╔╔═╗╔╦╗╔═╗ ║
 ║ ║ ╦╠╦╝╠═╣╠═╝╠═╣║╣ ║║║║╣   ║║║║╣  ║ ╠═╣║║║║ ║ ║║║╣  ║
 ║ ╚═╝╩╚═╩ ╩╩  ╩ ╩╚═╝╝╚╝╚═╝  ╩ ╩╚═╝ ╩ ╩ ╩╝╚╝╚═╝═╩╝╚═╝ ║
 ╚════════════════════════════════════════════════════╝
~
GRAPHENE BASE RPC
~
REMOTE PROCEDURE CALLS VIA PUBLIC NODE WEBSOCKET API
"""
# STANDARD MODULES
import json
import threading
import time
import traceback
from random import shuffle

# THIRD PARTY MODULES
import websocket

# GRAPHENE MODULES
from .graphene_constants import GrapheneConstants
from .graphene_metanode_client import GrapheneTrustlessClient
from .graphene_utils import (
    blip,
    from_iso_date,
    invert_pairs,
    it,
    jprint,
    precision,
    to_iso_date,
)
from websocket import create_connection as wss_connect

LOGO = """
╔═╗╦═╗╔═╗╔═╗╦ ╦╔═╗╔╗╔╔═╗  ╔╦╗╔═╗╔╦╗╔═╗╔╗╔╔═╗╔╦╗╔═╗
║ ╦╠╦╝╠═╣╠═╝╠═╣║╣ ║║║║╣   ║║║║╣  ║ ╠═╣║║║║ ║ ║║║╣
╚═╝╩╚═╩ ╩╩  ╩ ╩╚═╝╝╚╝╚═╝  ╩ ╩╚═╝ ╩ ╩ ╩╝╚╝╚═╝═╩╝╚═╝
DECENTRALIZED EXCHANGE USER STREAM AND ORDER BOOKS
"""
DEV = False


class RemoteProcedureSession:
    """
    Create a websocket app for callbacks
    """

    def __init__(self, nodes, retries):
        self.nodes = nodes
        self.num_retries = retries
        self.wsa = None
        self.msg = None
        self.keepalive = None
        self.run_event = None

    def on_message(self, _, reply):
        """
        This method is called by the websocket connection on every message that is
        received.
        If we receive a ``notice``, we hand over post-processing and signalling of
        events to ``process_notice``.
        """
        self.msg = str(reply)
        data = {}
        try:
            data = json.loads(reply, strict=False)
        except ValueError:
            raise ValueError("API node returned invalid format. Expected JSON!")
        if DEV:
            print(data)
        if data.get("result") is not None or data.get("method") == "notice":
            try:
                if data["result"][0]["id"] != "2.8.0":
                    self.close()
            except Exception:
                self.close()

    def on_error(self, _, error):
        """Called on websocket errors."""
        print("Websocket error:", error)
        print("last message:", self.msg)

    def on_close(self, *_):
        """Called when websocket connection is closed."""
        print(f"Closing WebSocket connection")
        print("last message:", self.msg)

    def on_open(self, query):
        """
        start the keepalive and send the query
        """
        self.keepalive = threading.Thread(target=self._ping)
        self.keepalive.start()
        if DEV:
            print("Sending query")
        self.wsa.send(query.encode("utf8"))
        if DEV:
            print("Sent query")

    def close(self):
        """Closes the websocket connection and waits for the ping thread to close."""
        self.wsa.close()
        self.run_event.set()

    def _ping(self):
        while not self.run_event.wait(10):
            self.wsa.send(
                json.dumps(
                    {
                        "method": "call",
                        "params": ["database", "get_objects", [["2.8.0"]]],
                        "jsonrpc": "2.0",
                        "id": 1,
                    }
                )
            )

    def wss_query(self, params: list = None, client_order_id: int = 1):
        """
        This method is used to run the websocket app continuously.
        It will execute callbacks as defined and try to stay connected with the provided
        APIs
        """
        self.run_event = threading.Event()
        query = json.dumps(
            {
                "method": "call",
                # params format is ["location", "object", []]
                "params": params,
                "jsonrpc": "2.0",
                # client order id is for listening for callback
                "id": client_order_id,
            }
        )
        if DEV:
            print(query)
        cnt = 0
        self.wsa = None
        while not self.run_event.is_set():
            cnt += 1
            try:
                # If there is no connection, we have to create one and wait for it to connect
                self.wsa = websocket.WebSocketApp(
                    self.nodes[0],
                    on_message=self.on_message,
                    on_error=self.on_error,
                    on_close=self.on_close,
                    on_open=lambda _: self.on_open(query),
                )
                self.wsa.run_forever()
            except websocket.WebSocketException as error:
                if self.num_retries >= 0 and cnt > self.num_retries:
                    raise Exception("NumRetriesReached")
                sleeptime = cnt**2
                if sleeptime:
                    print(
                        f"Lost connection to node during wsconnect(): {self.nodes[0]}"
                        + f"\nRetrying in {sleeptime} seconds:"
                        + str(error)
                    )
                    time.sleep(sleeptime)
            except Exception as error:
                print(f"{str(error)}\n\n{traceback.format_exc()}")
        # print(type(self.msg))
        data = json.loads(self.msg)
        if params[1] != "broadcast_transaction_with_callback":
            data = data["result"]
        if DEV:
            print(data)
        return data


class RemoteProcedureCall:
    """
    query method docstrings are derived from Bitshare doxygen docs
    https://doxygen.bitshares.org/namespacemetanode.graphene_1_1app.html
    all RemoteProcedureCall queries return json.loads()
    and post processed python objects
    """

    def __init__(self, constants, nodes=None, session=False):
        self.constants = constants
        self.metanode = GrapheneTrustlessClient(self.constants)
        self.nodes = nodes
        self.printing = True
        self.connection = None
        if nodes is None:
            # ==========================================================================
            self.nodes = list(self.metanode.whitelist)  # DISCRETE SQL QUERY
            # ==========================================================================
        self.session = session
        if session:
            rps = RemoteProcedureSession(self.nodes, self.constants.signing.HANDSHAKE_TIMEOUT)
            self.wss_query = rps.wss_query
        else:
            self.connection = self.wss_handshake()

    # WEBSOCKET SEND AND RECEIVE
    # ==================================================================================
    def wss_handshake(self):
        """
        create a wss handshake in less than X seconds, else try again
        """
        # in the case of metanode we want to keep track of latency
        handshake = handshake_max = self.constants.signing.HANDSHAKE_TIMEOUT
        iteration = 0
        while handshake >= handshake_max and iteration < max(len(self.nodes)*2, 10):
            iteration += 1
            # attempt to close open stale connection
            try:
                if self.connection is not None:
                    self.connection.close()
            except Exception:
                pass
            try:
                start = time.time()
                self.connection = wss_connect(self.nodes[0], timeout=handshake_max)
                handshake = time.time() - start
            except Exception:
                # ascending pause here prevents excess cpu on loss of internet
                time.sleep(min(5, 1.01**iteration - 1))
                try:
                    self.connection.close()
                except Exception:
                    pass
            # rotate the nodes list
            self.nodes.append(self.nodes.pop(0))
        return self.connection

    def wss_query(self, params: list = None, client_order_id: int = 1) -> object:
        """
        this definition will place all remote procedure calls (RPC)
        the logo refresh is also here
        """
        if self.printing:
            if not DEV:
                print("\033c")
            print(
                it("yellow", LOGO),
                it(
                    "red",
                    [
                        self.constants.chain.NAME,
                        self.constants.chain.ACCOUNT,
                        self.constants.chain.PAIRS,
                    ],
                ),
                "\n",
                it("green", self.nodes),
                "\n",
                it("orange", "rpc"),
                self.nodes[0],
                client_order_id,
                params,
            )
        if self.connection is None:
            self.connection = self.wss_handshake()
        for _ in range(10):
            try:
                # this is the 4 part format of EVERY self.connection request
                query = json.dumps(
                    {
                        "method": "call",
                        # params format is ["location", "object", []]
                        "params": params,
                        "jsonrpc": "2.0",
                        # client order id is for listening for callback,
                        # not currently used, but implemented at this level for future
                        "id": client_order_id,
                    }
                )
                # self.connection is the websocket connection created by wss_handshake()
                # we will use this connection to send query and receive json
                self.connection.send(query)
                ret = json.loads(self.connection.recv())
                try:
                    return ret["result"]  # if there is result key take it
                except Exception:
                    print("NODE FAILED", jprint(params), client_order_id, ret)
                    return ret
            except Exception:
                try:  # attempt to terminate the connection
                    self.connection.close()
                except Exception:
                    pass
                self.connection = self.wss_handshake()
        print(f"NODE FAILED AFTER 10 ATTEMPTS", jprint(params), client_order_id)

    def close(self):
        """
        attempt to close the websocket connection associated with this instance
        """
        try:
            self.connection.close()
        except Exception:
            pass

    def reconnect(self):
        """
        close and reopen the connection
        """
        self.close()
        nodes = list(self.metanode.whitelist)
        shuffle(nodes)
        return RemoteProcedureCall(self.constants, nodes)

    def get_pair_data(self, pair):
        """
        get the id and precision for a given pair from the metanode
        """
        # ==============================================================================
        assets = self.metanode.assets  # DISCRETE SQL QUERY
        # ==============================================================================
        asset_name, currency_name = pair.split("-")
        return {
            "asset": {
                "name": asset_name,
                "id": assets[asset_name]["id"],
                "precision": int(assets[asset_name]["precision"]),
            },
            "currency": {
                "name": currency_name,
                "id": assets[currency_name]["id"],
                "precision": int(assets[currency_name]["precision"]),
            },
            "account_name": self.constants.chain.ACCOUNT,
        }

    # DATABASE API
    # ==================================================================================
    def account_by_name(self):
        """
        given an account name return an account id
        ~
        :RPC param str(name): Name of the account to retrieve
        :RPC returns str(): The account id holding the provided name
        """
        return self.wss_query(
            ["database", "get_account_by_name", [self.constants.chain.ACCOUNT, 1]],
        )

    def account_balances(self):
        """
        RPC an account's balances in various assets
        ~
        :RPC param str(account_name_or_id): name or ID of the account to get balances
        :RPC param list(assets): IDs of the assets to get balances of;
            if empty, get all assets account has a balance in
        :RPC returns: Balances of the account
        """
        # ==============================================================================
        dict_assets = dict(self.metanode.assets)  # DISCRETE SQL QUERY
        metanode_objects = dict(self.metanode.objects)  # DISCRETE SQL QUERY
        # ==============================================================================
        list_assets = list(dict_assets.keys())
        balances = {asset: {"free": 0, "tied": 0, "total": 0} for asset in list_assets}
        asset_ids = [j["id"] for i, j in dict_assets.items()]
        # query only relevant balances
        ret = self.wss_query(
            [
                "database",
                "get_named_account_balances",
                [self.constants.chain.ACCOUNT, asset_ids],
            ],
        )
        # print(ret)
        # [{'amount': 1166517892, 'asset_id': '1.3.0'}, ... ]
        for total in ret:
            asset_name = metanode_objects[total["asset_id"]]["name"]
            balances[asset_name]["total"] = float(
                precision(
                    float(total["amount"]) / 10 ** int(dict_assets[asset_name]["precision"]),
                    dict_assets[asset_name]["precision"],
                )
            )
        amounts_tied = self.open_order_balances_tied()
        for asset_name, amount_tied in amounts_tied.items():
            balances[asset_name]["tied"] = float(
                precision(amount_tied, dict_assets[asset_name]["precision"])
            )
            balances[asset_name]["free"] = max(
                0,
                (
                    float(
                        precision(
                            balances[asset_name]["total"] - amount_tied,
                            int(dict_assets[asset_name]["precision"]),
                        )
                        # less one quantum to mitigate float errors
                    )
                    - 1.0 / 10 ** int(dict_assets[asset_name]["precision"])
                ),
            )
        # ~ balances = {
        # ~ "XXX": {
        # ~ "free": float(),
        # ~ "tied": float(),
        # ~ "total": float(),
        # ~ "YYY": {}, ..
        # ~ }
        return balances

    def block_number(self):
        """
        block number and block prefix
        ~
        Retrieve the current graphene::chain::dynamic_global_property_object
        """
        return self.block_number_raw()["head_block_number"]

    def block_number_raw(self):
        """
        block number and block prefix
        ~
        Retrieve the current graphene::chain::dynamic_global_property_object
        """
        return self.wss_query(["database", "get_dynamic_global_properties", []])

    def blocktime(self):
        """
        wraps blocktime_participation, only returning the blocktime
        """
        blocktime, _ = self.blocktime_participation()
        return int(blocktime)

    def blocktime_participation(self):
        """
        Determine if node is returning stale data
        ~
        RPC the objects corresponding to the provided IDs
        ~
        :RPC param str(ids): IDs of the objects to retrieve
        :RPC returns: The objects retrieved, in the order they are mentioned in ids
        """
        ret = self.wss_query(["database", "get_objects", [["2.1.0"]]])[0]
        unix = from_iso_date(ret["time"])
        participation = bin(int(ret["recent_slots_filled"])).count("1") / 1.28
        return int(unix), int(participation)

    def book(self, pair, depth=3):
        """
        Remote procedure call orderbook bids and asks
        ~
        :RPC param str(base): symbol name or ID of the base asset
        :RPC param str(quote): symbol name or ID of the quote asset
        :RPC param int(limit): depth of the order book to retrieve (max limit 50)
        :RPC returns: Order book of the market
        """
        cache = self.get_pair_data(pair)
        order_book = self.wss_query(
            [
                "database",
                "get_order_book",
                [cache["currency"]["name"], cache["asset"]["name"], depth],
            ],
        )
        asks = []
        bids = []
        for i, _ in enumerate(order_book["asks"]):
            price = float(precision(order_book["asks"][i]["price"], 16))
            if float(price) == 0 and not self.constants.metanode.DEV:
                raise ValueError("zero price in asks")
            volume = float(
                precision(order_book["asks"][i]["quote"], int(cache["asset"]["precision"]))
            )
            asks.append((price, volume))
        for i, _ in enumerate(order_book["bids"]):
            price = float(precision(order_book["bids"][i]["price"], 16))
            if float(price) == 0 and not self.constants.metanode.DEV:
                raise ValueError("zero price in bids")
            volume = float(
                precision(order_book["bids"][i]["quote"], int(cache["asset"]["precision"]))
            )
            bids.append((price, volume))
        return {"asks": asks, "bids": bids}

    def chain_id(self):
        """
        RPC the chain ID to confirm it matches mainnet ID
        ~
        Retrieve the graphene::chain::chain_property_object associated with the chain
        """
        ret = self.wss_query(["database", "get_chain_properties", []])
        return ret["chain_id"]

    def current_supply(self):
        """
        NOTE: returns supply in graphene terms; no precision
        :param dict(assets): metanode assets dict
        :return dict(assets): metanode assets dict with updated supply
        ~
        RPC the objects corresponding to the provided IDs
        ~
        :RPC param str(ids): IDs of the objects to retrieve
        :RPC returns: The objects retrieved, in the order they are mentioned in ids
        """
        # ==============================================================================
        metanode_assets = dict(self.metanode.assets)  # DISCRETE SQL QUERY
        # ==============================================================================
        asset_id_to_name = {v["id"]: k for k, v in metanode_assets.items()}
        asset_ids = [v["id"] for v in metanode_assets.values()]
        dynamic_assets = ["2.3." + asset.split(".")[-1] for asset in asset_ids]
        ret = self.wss_query(["database", "get_objects", [dynamic_assets]])
        return {
            asset_id_to_name[asset["id"].replace("2.3", "1.3")]: int(asset["current_supply"])
            for asset in ret
        }

    def get_transaction_hex(self, trx):
        """
        use this to verify the manually serialized trx buffer
        ~
        RPC a hexdump of the serialized binary form of a transaction
        ~
        :RPC param trx: a transaction to get hexdump from
        :RPC returns: the hexdump of the transaction WITH the signatures
        """
        ret = self.wss_query(["database", "get_transaction_hex", [trx]])
        return bytes(ret, "utf-8")

    def is_ltm(self) -> bool:
        """
        returns True if user is lifetime member and eligible for 80% tx fee discountx
        """
        return self.account_by_name()["membership_expiration_date"] == self.constants.core.LTM

    def key_reference(self, public_key: str):
        """
        given public key return account id
        ~
        RPC all accounts that refer to the specified public keys in their owner
        authority, active authorities or memo key
        ~
        :RPC param keys: list of public keys to query
        :RPC returns: ID of all accounts that refer to the specified keys
        """
        return self.wss_query(["database", "get_key_references", [[public_key]]])

    def lookup_asset_symbols(self):
        """
        Given asset names return asset ids and precisions
        ~
        RPC a list of assets by symbol names or IDs
        ~
        :RPC param list(symbols_or_ids): symbol names or IDs of the assets to retrieve
        :RPC returns: The assets corresponding to the provided symbols or IDs
        """
        assets = self.constants.chain.ASSETS
        ret = self.wss_query(["database", "lookup_asset_symbols", [assets]])
        # print(json.dumps(ret, indent=4))
        cache = {}
        for idx, asset in enumerate(assets):
            cache[asset] = {
                "id": ret[idx]["id"],
                "precision": int(ret[idx]["precision"]),
                "fees": {},
            }
            market_fee = float(ret[idx]["options"]["market_fee_percent"]) / 100
            taker_fee = float(0)
            if (
                isinstance(ret[idx]["options"]["extensions"], dict)
                and "taker_fee_percent" in ret[idx]["options"]["extensions"]
            ):
                taker_fee = float(ret[idx]["options"]["extensions"]["taker_fee_percent"]) / 100
            cache[asset]["fees"]["maker"] = market_fee
            cache[asset]["fees"]["taker"] = market_fee if taker_fee == 0 else taker_fee
        return cache

    def last(self, pair):
        """
        RPC the latest ticker price
        ~
        :RPC param base: symbol name or ID of the base asset
        :RPC param quote: symbol name or ID of the quote asset
        :RPC returns: The market ticker for the past 24 hours
        """
        asset, currency = pair.split("-")
        ticker = self.wss_query(["database", "get_ticker", [currency, asset, False]])
        last = float(precision(ticker["latest"], 16))
        if float(last) == 0:
            last = -1
        # if not self.constants.metanode.DEV:
        #     raise ValueError("zero price last")
        return last

    def market_history(self, pair, depth=100):
        """
        RPC recent recent transaction in this market
        ~
        :RPC param str(base):  symbol or ID of the base asset
        :RPC param str(quote):  symbol or ID of the quote asset
        :RPC param int(start):  Start time UNIX timestamp; latest transactions to get
        :RPC param int(stop):  Stop time UNIX timestamp; earliest transactions to get
        :RPC param int(limit):  Maximum quantity of transactions to retrieve, max 100
        """
        cache = self.get_pair_data(pair)
        now = time.time()
        trade_history = self.wss_query(
            [
                "database",
                "get_trade_history",
                [
                    cache["currency"]["id"],
                    cache["asset"]["id"],
                    to_iso_date(now),
                    to_iso_date(now - 86400),
                    depth,
                ],
            ],
        )
        history = []
        # ~ print(trade_history)
        # ~ [{'sequence': 183490,
        # ~ 'date': '2022-01-21T20:41:36',
        # ~ 'price': '0.025376407606742865',
        # ~ 'amount': '414.76319',
        # ~ 'value': '10.5252',
        # ~ 'type': 'sell',
        # ~ 'side1_account_id':'1.2.1624289',
        # ~ 'side2_account_id': '1.2.883283'},...]
        for value in trade_history:
            unix = int(from_iso_date(value["date"]))
            price = float(precision(value["price"], 16))
            if float(price) == 0 and not self.constants.metanode.DEV:
                raise ValueError("zero price in history")
            amount = float(value["amount"])
            history.append([unix, price, amount, value["type"], value["sequence"]])
        # if not history and not CONSTANTS.metanode.DEV:
        #    raise ValueError("no history")
        return history

    def open_order_balances_tied(self):
        """
        determine how much of each asset is tied on open orders
        """
        account_name = self.constants.chain.ACCOUNT
        assets = self.constants.chain.ASSETS
        # ==============================================================================
        metanode_objects = dict(self.metanode.objects)  # DISCRETE SQL QUERY
        metanode_assets = dict(self.metanode.assets)  # DISCRETE SQL QUERY
        # ==============================================================================
        ret = self.wss_query(["database", "get_full_accounts", [[account_name], "false"]])
        try:
            limit_orders = ret[0][1]["limit_orders"]
        except Exception:
            limit_orders = []
        tied = {asset: 0 for asset in assets}
        for order in limit_orders:
            base_id = order["sell_price"]["base"]["asset_id"]
            if base_id in metanode_objects:
                base_name = metanode_objects[base_id]["name"]
            else:
                continue
            tied[base_name] += float(order["for_sale"]) / float(
                10 ** int(metanode_assets[base_name]["precision"])
            )
        return tied

    def open_orders(self):
        """
        remote procedure call for open orders returns price as fraction,
        with unreferenced Decimal point locations on both amounts,
        also reference by A.B.C instead of ticker symbol
        gather data and post process to human readable from graphene
        ~
        :RPC param list(names_or_ids): Names or IDs of an accounts to retrieve
        :RPC returns: Map of string from names_or_ids to the corresponding account
        """
        all_open_orders = {}
        pairs = self.constants.chain.PAIRS
        ret = self.wss_query(
            ["database", "get_full_accounts", [[self.constants.chain.ACCOUNT], False]],
        )
        try:
            limit_orders = ret[0][1]["limit_orders"]
        except BaseException:
            limit_orders = []
        for pair in pairs:
            cache = self.get_pair_data(pair)
            orders = []
            for order in limit_orders:
                base_id = order["sell_price"]["base"]["asset_id"]
                quote_id = order["sell_price"]["quote"]["asset_id"]
                if (base_id in [cache["currency"]["id"], cache["asset"]["id"]]) and (
                    quote_id in [cache["currency"]["id"], cache["asset"]["id"]]
                ):
                    amount = float(order["for_sale"])
                    base_amount = float(order["sell_price"]["base"]["amount"])
                    quote_amount = float(order["sell_price"]["quote"]["amount"])
                    if base_id == cache["currency"]["id"]:
                        base_precision = int(cache["currency"]["precision"])
                        quote_precision = int(cache["asset"]["precision"])
                    else:
                        base_precision = int(cache["asset"]["precision"])
                        quote_precision = int(cache["currency"]["precision"])
                    base_amount /= 10**base_precision
                    quote_amount /= 10**quote_precision
                    if base_id == cache["asset"]["id"]:
                        order_type = "SELL"
                        price = quote_amount / base_amount
                        amount /= 10**base_precision
                    else:
                        order_type = "BUY"
                        price = base_amount / quote_amount
                        amount = (amount / 10**base_precision) / price
                    orders.append(
                        {
                            "order_number": order["id"],
                            "market": pair,
                            "amount": float(precision(amount, int(cache["asset"]["precision"]))),
                            "base_amount": float(
                                precision(base_amount, int(cache["asset"]["precision"]))
                            ),
                            "price": precision(price, 16),
                            "type": order_type,
                        }
                    )
            all_open_orders[pair] = sorted(orders, key=lambda k: k["price"])
        return all_open_orders

    def open_order_ids(self, pair=None):
        """
        return a list of open orders, for one account, in one market
        used to cancel all
        ~
        Fetch all objects relevant to the specified accounts
        ~
        :RPC param list(names_or_ids): names or IDs of an accounts to retrieve
        :RPC returns: Map of string from names_or_ids to the corresponding account
        """
        ret = self.wss_query(
            [
                "database",
                "get_full_accounts",
                [[self.constants.chain.ACCOUNT], "false"],
            ],
        )
        try:
            limit_orders = ret[0][1]["limit_orders"]
        except Exception:
            limit_orders = []
        if pair is not None:
            market = [pair["currency_id"], pair["asset_id"]]
        else:
            market = False
        orders = []
        for order in limit_orders:
            base_id = order["sell_price"]["base"]["asset_id"]
            quote_id = order["sell_price"]["quote"]["asset_id"]
            if not market or (base_id in market) and (quote_id in market):
                orders.append(order["id"])
        return orders

    def fees_account(self):
        """
        returns fee for limit order create and cancel in graphene int terms
        ~
        For each operation calculate the required fee in the specified asset type
        ~
        :RPC param list(ops): a list of operations to be query for required fees
        :RPC param str(asset_symbol_or_id): symbol name or ID of an asset used to pay
        :RPC returns list(): of objects which indicates required fees of each operation
        """
        account_id = dict(self.metanode.account)["id"]
        objects = dict(self.metanode.objects)
        core_precision = int(objects["1.3.0"]["precision"])
        ret = self.wss_query(
            [
                "database",
                "get_required_fees",
                [
                    [
                        ["1", {"from": str(account_id)}],
                        ["2", {"from": str(account_id)}],
                    ],
                    "1.3.0",
                ],
            ]
        )
        create_graphene = int(ret[0]["amount"])
        cancel_graphene = int(ret[1]["amount"])
        return {
            "create": float(create_graphene) / 10**core_precision,
            "cancel": float(cancel_graphene) / 10**core_precision,
            "create_graphene": create_graphene,
            "cancel_graphene": cancel_graphene,
        }

    def list_assets(self, search):
        return self.wss_query([
            "database",
            "list_assets",
            [
                search, 100
            ]
        ])

    # HISTORY API
    # ==================================================================================
    def fill_order_history(self, pair):
        """
        we get a list of "fill order history" dicts for one trading_pair from core:
        {
            "id": "0.0.69",
            "key": {
                "base": "1.3.0",
                "quote": "1.3.8",
                "sequence": -5
            },
            "time.time": "2021-12-22T23:09:42",
            "op": {
                "fee": {
                    "amount": 0,
                    "asset_id": "1.3.8"
                },
                "order_id": "1.7.181",
                "account_id": "1.2.207",
                "pays": {
                    "amount": 100000,
                    "asset_id": "1.3.0"
                },
                "receives": {
                    "amount": 60000000,
                    "asset_id": "1.3.8"
                }
            }
        }
        we need to refine this into OrderBookMessageType.TRADE dicts
        for our account for each trading_pair in this format:
        {
            "exchange_order_id": str(),
            "trade_type": str(),
            "price": Decimal(),
            "amount": Decimal(),
        }
        ~
        RPC details of most recent order executions for a trading pair
        ~
        :RPC param asset_a: Asset symbol or ID in a trading pair
        :RPC param asset_b: The other asset symbol or ID in the trading pair
        :RPC param limit: Maximum records to return
        :RPC returns: a list of order_history objects, in "most recent first" order
        """
        # ==============================================================================
        pair_data = self.get_pair_data(pair)  # DISCRETE SQL QUERY
        objects = dict(self.metanode.objects)  # DISCRETE SQL QUERY
        account_id = str(self.metanode.account["id"])  # DISCRETE SQL QUERY
        pairs = dict(self.metanode.pairs)  # DISCRETE SQL QUERY
        # ==============================================================================
        metanode_fills = pairs[pair]["fills"]
        iteration = 0
        rpc_fills = []
        while rpc_fills == []:
            iteration += 1
            if iteration > 10:
                break
            ret = self.wss_query(
                [
                    "history",
                    "get_fill_order_history",
                    [pair_data["asset"]["id"], pair_data["currency"]["id"], 100],
                ],
            )
            # sort by user
            fills = [i for i in ret if i["op"]["account_id"] == account_id]
            for fill in fills:
                if DEV:
                    print(fill)
                # base
                base_id = fill["op"]["pays"]["asset_id"]
                base_name = objects[base_id]["name"]
                base_precision = int(objects[base_id]["precision"])
                pays = float(fill["op"]["pays"]["amount"]) / 10**base_precision
                # quote
                quote_id = fill["op"]["receives"]["asset_id"]
                quote_name = objects[quote_id]["name"]
                quote_precision = int(objects[quote_id]["precision"])
                receives = float(fill["op"]["receives"]["amount"]) / 10**quote_precision
                # fee
                fee = {"asset": quote_name, "amount": 0}
                try:
                    fee_id = fill["op"]["fee"]["asset_id"]
                    fee_name = objects[fee_id]["name"]
                    if fee_name not in [base_name, quote_name]:
                        raise ValueError("fee outside of trading pair")
                    fee_precision = int(objects[fee_id]["precision"])
                    fee_amount = float(fill["op"]["fee"]["amount"]) / 10**fee_precision
                    fee = {"asset": fee_name, "amount": fee_amount}
                except Exception:
                    pass
                # pair and order id
                fill_trading_pair = base_name + "-" + quote_name
                exchange_order_id = fill["op"]["order_id"]
                # eg pays BTC receives USD in BTC-USD market; price = $50,000
                if fill_trading_pair == pair:
                    rpc_fills.append(
                        {
                            "exchange_order_id": str(exchange_order_id),
                            "price": float(receives / pays),
                            "amount": float(pays),
                            "type": "SELL",
                            "unix": from_iso_date(fill["time"]),
                            "sequence": abs(fill["key"]["sequence"]),
                            "fee": fee,
                        }
                    )
                # eg pays USD receives BTC in BTC-USD market; price = $50,000
                elif fill_trading_pair == invert_pairs([pair])[0]:
                    rpc_fills.append(
                        {
                            "exchange_order_id": str(exchange_order_id),
                            "price": float(pays / receives),
                            "amount": float(receives),
                            "type": "BUY",
                            "unix": from_iso_date(fill["time"]),
                            "sequence": abs(fill["key"]["sequence"]),
                            "fee": fee,
                        }
                    )
            blip(0.5)
        # fills should never get shorter
        return [json.loads(i) for i in list({json.dumps(i) for i in rpc_fills + metanode_fills})]

    def operations(self):
        """
        sample public API response:
        [
            # CREATE
            {
                "id": "1.11.313551",
                "op": [1, {
                        "fee": {"amount": 500000, "asset_id": "1.3.0"},
                        "seller": "1.2.207",
                        "amount_to_sell": {"amount": 49360, "asset_id": "1.3.0"},
                        "min_to_receive": {"amount": 123399999, "asset_id": "1.3.8"},
                        "expiration": "2096-10-02T07:06:40",
                        "fill_or_kill": false,
                        "extensions": []
                }],
                "result": [
                    1,
                    "1.7.348"
                ],
                "block_num": 1674347,
                "trx_in_block": 0,
                "op_in_trx": 0,
                "virtual_op": 0
            },
            # CANCEL
            {
                "id": "1.11.262418",
                "op": [2, {
                        "fee": {"amount": 0, "asset_id": "1.3.0"},
                        "fee_paying_account": "1.2.207",
                        "order": "1.7.290",
                        "extensions": []
                    }
                ],
                "result": [2, { "amount": 49360, "asset_id": "1.3.0"}],
                "block_num": 1413738,
                "trx_in_block": 0,
                "op_in_trx": 14,
                "virtual_op": 0
            }
        ]
        RPC operations relevant to the specified account referenced
        by an event numbering specific to the account
        The current number of operations for the account
        can be found in the account statistics (or use 0 for start)
        ~
        :RPC param str(account_name_or_id):	The account name or ID history to query
        :RPC param int(stop):	Sequence number of earliest operation
            0 is default and will query 'limit' number of operations
        :RPC param int(limit):	Maximum number of operations to retrieve (max 100)
        :RPC param int(start):	Sequence number of the most recent operation to retrieve
            0 is default, which will start querying from the most recent operation
        :RPC returns:  A list of operations performed by account; recent to oldest
        """
        # gather cache required to post process relative history from the metanode
        # ==============================================================================
        objects = dict(self.metanode.objects)  # DISCRETE SQL QUERY
        # ==============================================================================
        account_name = self.constants.chain.ACCOUNT
        trading_pairs = self.constants.chain.PAIRS
        # make the external call
        ret = self.wss_query(
            [
                "history",
                "get_relative_account_history",
                [
                    account_name,
                    0,  # total_ops - 100,
                    100,
                    0,  # total_ops,
                ],
            ],
        )
        # ==============================================================================
        # OP 1 - LIMIT ORDER CREATE
        # ==============================================================================
        # NOTE list comprehension must FIRST sort by op=1; then account and assets
        creates = [
            i
            for i in ret
            if i["op"][0] == 1
            and i["op"][1]["amount_to_sell"]["asset_id"] in objects
            and i["op"][1]["min_to_receive"]["asset_id"] in objects
        ]
        # reformat sales to human Decimal terms from graphene integer fraction math
        create_ops = []
        for create in creates:
            # "amount_to_sell" we call base asset
            # "min_to_receive" we call quote currency
            # NOTE: graphene everything is a sell, the trading pair swaps, eg
            # sell BTC-USD is expressed as sell BTC-USD, but
            # buy BTC-USD is expressed as sell USD-BTC
            # ~
            # extract the asset id for the fee, base, and quote
            fee_id = create["op"][1]["fee"]["asset_id"]
            base_id = create["op"][1]["amount_to_sell"]["asset_id"]
            quote_id = create["op"][1]["min_to_receive"]["asset_id"]
            # from the id's we can derive names utilizing the metanode objects
            base_name = objects[base_id]["name"]
            quote_name = objects[quote_id]["name"]
            pair = base_name + "-" + quote_name
            # extract the amount for the fee, base, and quote in human terms
            fee_amount = int(create["op"][1]["fee"]["amount"]) / 10 ** int(objects[fee_id]["precision"])
            base_amount = int(create["op"][1]["amount_to_sell"]["amount"]) / 10 ** int(
                objects[base_id]["precision"]
            )
            quote_amount = int(create["op"][1]["min_to_receive"]["amount"]) / 10 ** int(
                objects[quote_id]["precision"]
            )
            # from quote and base amount we can derive a price
            price = base_amount / quote_amount
            if pair in trading_pairs:
                create_ops.append(
                    {
                        "order_id": create["result"][1],
                        "op_id": create["id"],
                        "block_num": create["block_num"],
                        "price": 1 / price,
                        "amount": base_amount,
                        "tx_fee": fee_amount,
                        "pair": pair,
                        "type": "SELL",
                    }
                )
            elif pair in invert_pairs(trading_pairs):
                create_ops.append(
                    {
                        "order_id": create["result"][1],
                        "op_id": create["id"],
                        "block_num": create["block_num"],
                        "price": price,
                        "amount": quote_amount,
                        "tx_fee": fee_amount,
                        "pair": invert_pairs([pair])[0],
                        "type": "BUY",
                    }
                )
        # ==============================================================================
        # OP 2 - LIMIT ORDER CANCEL
        # ==============================================================================
        # NOTE list comprehension must FIRST sort by op=2; then account
        cancels = [i for i in ret if i["op"][0] == 2]
        # reformat cancellations to human terms from graphene integer math
        my_cancel_ops = []
        for cancel in cancels:
            fee_id = cancel["op"][1]["fee"]["asset_id"]
            fee_amount = cancel["op"][1]["fee"]["amount"] / 10 ** int(objects[fee_id]["precision"])
            my_cancel_ops.append(
                {
                    "order_id": cancel["op"][1]["order"],
                    "op_id": cancel["id"],
                    "block_num": cancel["block_num"],
                    "tx_fee": fee_amount,
                }
            )
        sooth = {
            pair: {
                "creates": [s for s in create_ops if s["pair"] == pair],
            }
            for pair in self.constants.chain.PAIRS
        }
        sooth["cancels"] = my_cancel_ops
        return sooth

    # BROADAST API
    # ==================================================================================
    def broadcast_transaction(self, trx, client_order_id=1):
        """
        upload the signed transaction to the blockchain
        ~
        RPC Broadcast a transaction to the network
        trx will be checked for validity in node database prior to broadcasting
        If it fails to apply locally,
        an error will be thrown and the transaction will not be broadcast
        ~
        :RPC param trx: The transaction to broadcast
        ~
        if _with_callback:
            :RPC returns: info about the block including the transaction
        """
        broadcast = "broadcast_transaction"
        if self.session:
            broadcast += "_with_callback"
            trx = [client_order_id, trx]
        else:
            trx = [trx]
        ret = self.wss_query(["network_broadcast", broadcast, trx], client_order_id)
        return ret


def unit_test():
    """
    test functionality of select definitions
    """
    input(
        "you must have a metanode server running to \n"
        + "test the RemoteProcedureCall class. Please run\n\n"
        + "`python3 metanode.graphene_metanode_server.py`\n\n"
        + "in a seperate terminal, then press enter."
    )
    constants = GrapheneConstants()
    dispatch = {str(idx): chain for idx, chain in enumerate(constants.core.CHAINS)}
    for key, val in dispatch.items():
        print(key + ": " + val)
    chain = dispatch[input("Enter choice: ")]
    constants = GrapheneConstants(chain)
    print("\033c")
    dispatch = {str(idx): pair for idx, pair in enumerate(constants.chain.PAIRS)}
    for key, val in dispatch.items():
        print(key + ": " + val)
    pair = dispatch[input("Enter choice: ")]
    rpc = RemoteProcedureCall(constants, constants.chain.NODES)
    dispatch = [
        ("pair data", lambda: rpc.get_pair_data(pair)),
        ("current supply", rpc.current_supply),
        ("asset symbols", rpc.lookup_asset_symbols),
        ("open order balences tied", rpc.open_order_balances_tied),
        ("open orders", rpc.open_orders),
        ("account by name", rpc.account_by_name),
        ("fill order history", lambda: rpc.fill_order_history(pair)),
        ("relative account history", rpc.operations),
        ("account balances", rpc.account_balances),
        ("market history", lambda: rpc.market_history(pair)),
        ("book", lambda: rpc.book(pair)),
        ("last", lambda: rpc.last(pair)),
        ("block number", rpc.block_number),
        ("tx fees", rpc.fees_account),
        ("is lifetime member", rpc.is_ltm),
        ("chain id", rpc.chain_id),
    ]
    for func in dispatch:
        print(func[0])
        print(func[1]())
        print("\n\n")
        time.sleep(0.5)


if __name__ == "__main__":
    unit_test()
