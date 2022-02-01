#!/usr/bin/env python
# DISABLE SELECT PYLINT TESTS
# pylint: disable=bad-continuation, broad-except, too-many-locals, too-many-statements
# pylint: disable=import-error, too-many-branches, line-too-long
r"""
 ╔════════════════════════════════════════════════════╗
 ║ ╔═╗╦═╗╔═╗╔═╗╦ ╦╔═╗╔╗╔╔═╗  ╔╦╗╔═╗╔╦╗╔═╗╔╗╔╔═╗╔╦╗╔═╗ ║
 ║ ║ ╦╠╦╝╠═╣╠═╝╠═╣║╣ ║║║║╣   ║║║║╣  ║ ╠═╣║║║║ ║ ║║║╣  ║
 ║ ╚═╝╩╚═╩ ╩╩  ╩ ╩╚═╝╝╚╝╚═╝  ╩ ╩╚═╝ ╩ ╩ ╩╝╚╝╚═╝═╩╝╚═╝ ║
 ╚════════════════════════════════════════════════════╝
~
AUTHENTICATE, CREATE ORDER HEADERS, BUILD TRANSACTIONS IN GRAPHENE TERMS
THEN FROM HIGH LEVEL, SERIALIZE, SIGN, VERIFY, AND BROADCAST
"""

# STANDARD MODULES
import json
import time
from binascii import unhexlify  # hexidecimal to binary text
from collections import OrderedDict
from decimal import Decimal as decimal
from multiprocessing import Process, Value
from struct import unpack_from  # convert back to PY variable

# GRAPHENE MODULES
# ~ *soon* from hummingbot.connector.exchange.graphene.
from graphene_metanode_server import GrapheneTrustlessClient
from graphene_rpc import RemoteProcedureCall
from graphene_signing import (ObjectId, PrivateKey, serialize_transaction,
                              sign_transaction, verify_transaction)
from graphene_utils import it, jprint, to_iso_date, trace

DEV = False


class GrapheneAuth:
    """
    Auth class required by Graphene DEXs
    """

    def __init__(self, constants: str, wif: str):
        self.constants = constants
        self.wif = wif
        self.rpc = None
        self.metanode = GrapheneTrustlessClient(self.constants)

    def prototype_order(self, trading_pair=None, client_order_id=1):
        """
        creates an auto formatted empty prototype order in json format
        you will add your ['edicts'] and ['wif']
        metaNODE handles everything else
        usage
        from manualSIGNING import prototype_order
        order = json_loads(prototype_order())
        order['header']['wif'] = wif
        order['edicts'] = edicts
        broker(order)
        """
        proto = {}
        # ==============================================================================
        whitelist = self.metanode.whitelist  # DISCRETE SQL QUERY
        account = self.metanode.account  # DISCRETE SQL QUERY
        objects = self.metanode.objects  # DISCRETE SQL QUERY
        assets = self.metanode.assets  # DISCRETE SQL QUERY
        # ==============================================================================
        core_precision = int(objects["1.3.0"]["precision"])
        create = int(account["fees_account"]["create_graphene"])
        cancel = int(account["fees_account"]["cancel_graphene"])
        print(core_precision)
        print(create, cancel)
        proto["op"] = ""
        proto["nodes"] = whitelist
        proto["header"] = {
            "wif": self.wif,
            "account_id": account["id"],
            "account_name": account["name"],
            "client_order_id": client_order_id,
        }
        if trading_pair is not None:
            asset, currency = trading_pair.split("-")
            proto["header"].update(
                {
                    "asset_id": assets[asset]["id"],
                    "currency_id": assets[currency]["id"],
                    "asset_name": asset,
                    "currency_name": currency,
                    "asset_precision": assets[asset]["precision"],
                    "currency_precision": assets[currency]["precision"],
                    "pair": asset + "-" + currency,
                    "fees": {
                        "create": create,
                        "cancel": cancel,
                    },
                }
            )
        return json.dumps(proto)

    def broker(self, order):
        """
        "broker(order) --> _execute(signal, order)"
        # insistent timed multiprocess wrapper for authorized ops
        # covers all incoming buy/sell/cancel authenticated requests
        # if command does not _execute in time: terminate and respawn
        # serves to force disconnect websockets if hung
        "up to self.constants.signing.ATTEMPTS chances;
        each self.constants.signing.PROCESS_TIMEOUT long: else abort"
        # signal is switched to 0 after execution to end the process
        """
        self.rpc = RemoteProcedureCall(self.constants)
        signal = Value("i", 0)
        auth = Value("i", 0)
        iteration = 0
        while (iteration < self.constants.signing.ATTEMPTS) and not signal.value:
            iteration += 1
            print(
                "\nmanualSIGNING authentication attempt:", iteration, time.ctime(), "\n"
            )
            child = Process(target=self._execute, args=(signal, auth, order))
            child.daemon = False
            child.start()
            # if (
            #    self.constants.signing.JOIN
            # ):  # means main script will not continue till child done
            child.join(self.constants.signing.PROCESS_TIMEOUT)
        return bool(auth.value)

    def _execute(
        self,
        signal,
        auth,
        order,
    ):
        """
        build tx, serialize, sign, verify, broadcast
        """

        def transact(order, auth):
            trx = self._build_transaction(order)
            # if there are any orders, perform ecdsa on serialized transaction
            if trx["operations"]:
                trx, message = serialize_transaction(trx, self.constants, self.rpc)
                signed_tx = sign_transaction(
                    trx, message, wif, self.constants.chain.PREFIX
                )
                signed_tx = verify_transaction(signed_tx, wif, self.constants)
                print(
                    self.rpc.broadcast_transaction(
                        signed_tx, order["header"]["client_order_id"]
                    )
                )
                auth.value = 1
                msg = it("green", "EXECUTED ORDER")
            else:
                msg = it("red", "REJECTED ORDER")
            return msg

        wif = order["header"]["wif"]
        start = time.time()
        # if this is just an authentication test,
        # then there is no serialization / signing
        # just check that the private key references to the account id in question
        msg = it("red", "FAILED FOR UNKNOWN REASON")
        # do not allow mixed create/cancel edicts
        if len(order["edicts"]) > 1:
            for edict in order["edicts"]:
                if edict["op"] == "cancel":
                    raise ValueError("batch edicts must not be cancel operations")
        if order["edicts"][0]["op"] == "login":
            msg = it("red", "LOGIN FAILED")
            # instantitate a PrivateKey object
            private_key = PrivateKey(wif, self.constants.chain.PREFIX)
            print("PrivateKey init")
            # which contains an Address object
            address = private_key.address
            # which contains str(PREFIX) and a Base58(pubkey)
            # from these two, build a human terms "public key"
            public_key = address.prefix + str(address.pubkey)
            # get a key reference from that public key to 1.2.x account id
            print(public_key)
            key_reference_id = self.rpc.key_reference(public_key)
            print(key_reference_id)
            key_reference_id = key_reference_id[0][0]
            # extract the account id in the metanode
            account_id = order["header"]["account_id"]
            print("wif account id", key_reference_id)
            print("order account id", account_id)
            # if they match we're authenticated
            if account_id == key_reference_id:
                auth.value = 1
                msg = it("green", "AUTHENTICATED")
        else:
            try:
                ########################################################################
                # "CANCEL ALL ONE MARKET"
                ########################################################################
                if (
                    order["edicts"][0]["op"] == "cancel"
                    and "1.7.X" in order["edicts"][0]["ids"]
                ):
                    msg = it("red", "NO OPEN ORDERS")
                    open_orders = True
                    while (
                        len(
                            self.rpc.open_order_ids(
                                {
                                    "currency_id": order["header"]["currency_id"],
                                    "asset_id": order["header"]["asset_id"],
                                }
                            )
                        )
                        > 0
                    ):
                        # ==============================================================
                        open_orders = self.metanode.pairs[order["header"]["pair"]][
                            "opens"
                        ]  # DISCRETE SQL QUERY
                        # ==============================================================
                        ids = order["edicts"][0]["ids"] = [
                            order["order_number"] for order in open_orders
                        ]
                        if ids:
                            msg = transact(order, auth)
                        time.sleep(10)
                ########################################################################
                # "CANCEL SOME ORDERS"
                ########################################################################
                elif (
                    order["edicts"][0]["op"] == "cancel"
                    and "1.7.X" not in order["edicts"][0]["ids"]
                ):
                    jprint(order)
                    msg = transact(order, auth)
                    time.sleep(5)
                ########################################################################
                # "BUY / SELL"
                ########################################################################
                else:
                    msg = transact(order, auth)
            except Exception as error:
                print(trace(error))
        stars = it("yellow", "*" * (len(msg) - 1))
        msg = "manualSIGNING " + msg
        print(stars + "\n    " + msg + "\n" + stars)
        print("process elapsed: %.3f sec" % (time.time() - start), "\n\n")
        signal.value = 1

    def login(self):
        """
        :return bool(): True = authenticated
        """
        order = self.prototype_order()
        order["edicts"] = [{"op": "login"}]
        return self.broker(order)

    def _build_transaction(self, order):
        """
        # this performs incoming limit order api conversion
        # from human terms to graphene terms
        # humans speak:
        "account name, asset name, order number"
        "decimal amounts, rounded is just fine"
        "buy/sell/cancel"
        "amount of assets"
        "price in currency"
        # graphene speaks:
        "1.2.x, 1.3.x, 1.7.x"
        "only in integers"
        "create/cancel"
        "min_to_receive/10^receiving_precision"
        "amount_to_sell/10^selling_precision"
        # _build_transaction speaks:
        "list of buy/sell/cancel human terms edicts any order in"
        "validated data request"
        "autoscale amounts if out of budget"
        "autoscale amounts if spending last bitshare"
        "bundled cancel/buy/sell transactions out; cancel first"
        "prevent inadvertent huge number of orders"
        "do not place orders for dust amounts"
        """
        # VALIDATE INCOMING DATA
        if not isinstance(order["edicts"], list):
            raise ValueError("order parameter must be list: %s" % order["edicts"])
        if not isinstance(order["nodes"], list):
            raise ValueError("order parameter must be list: %s" % order["nodes"])
        if not isinstance(order["header"], dict):
            raise ValueError("order parameter must be list: %s" % order["header"])
        # the location of the decimal place must be provided by order
        asset_precision = int(order["header"]["asset_precision"])
        asset_id = str(order["header"]["asset_id"])
        asset_name = str(order["header"]["asset_name"])
        currency_name = str(order["header"]["currency_name"])
        account_id = str(order["header"]["account_id"])
        checks = [account_id, asset_id]
        pair = str(order["header"]["pair"])
        fees = dict(order["header"]["fees"])
        # perform checks on currency for limit and call orders
        if order["edicts"][0]["op"] in ["buy", "sell"]:
            currency_precision = int(order["header"]["currency_precision"])
            currency_id = str(order["header"]["currency_id"])
            checks.append(currency_id)
        # validate a.b.c identifiers of account id and asset ids
        for check in checks:
            ObjectId(check)
        # GATHER TRANSACTION HEADER DATA
        # fetch block data via websocket request
        block = self.rpc.block_number_raw()
        ref_block_num = block["head_block_number"] & 0xFFFF
        ref_block_prefix = unpack_from("<I", unhexlify(block["head_block_id"]), 4)[0]
        # establish transaction expiration
        tx_expiration = to_iso_date(int(time.time() + 120))
        # initialize tx_operations list
        tx_operations = []
        # SORT INCOMING EDICTS BY TYPE AND CONVERT TO DECIMAL
        buy_edicts = []
        sell_edicts = []
        cancel_edicts = []
        for edict in order["edicts"]:
            if edict["op"] == "cancel":
                print(it("yellow", str({k: str(v) for k, v in edict.items()})))
                cancel_edicts.append(edict)
            elif edict["op"] == "buy":
                print(it("yellow", str({k: str(v) for k, v in edict.items()})))
                buy_edicts.append(edict)
            elif edict["op"] == "sell":
                print(it("yellow", str({k: str(v) for k, v in edict.items()})))
                sell_edicts.append(edict)
        for idx, _ in enumerate(buy_edicts):
            buy_edicts[idx]["amount"] = decimal(buy_edicts[idx]["amount"])
            buy_edicts[idx]["price"] = decimal(buy_edicts[idx]["price"])
        for idx, _ in enumerate(sell_edicts):
            sell_edicts[idx]["amount"] = decimal(sell_edicts[idx]["amount"])
            sell_edicts[idx]["price"] = decimal(sell_edicts[idx]["price"])
        # TRANSLATE CANCEL ORDERS TO GRAPHENE
        for edict in cancel_edicts:
            if "ids" not in edict.keys():
                edict["ids"] = ["1.7.X"]
            if "1.7.X" in edict["ids"]:  # the "cancel all" signal
                # for cancel all op, we collect all open orders in 1 market
                # FIXME
                metanode_pairs = self.metanode.pairs
                edict["ids"] = [order["id"] for order in metanode_pairs[pair]["opens"]]
                print(it("yellow", str(edict)))
            for order_id in edict["ids"]:
                # confirm it is good 1.7.x format:
                # FIXME this check should use ObjectId class instead of duplicate code
                order_id = str(order_id)
                aaa, bbb, ccc = order_id.split(".", 2)
                assert int(aaa) == float(aaa) == 1
                assert int(bbb) == float(bbb) == 7
                assert int(ccc) == float(ccc) > 0
                # create cancel fee ordered dictionary
                fee = OrderedDict([("amount", fees["cancel"]), ("asset_id", "1.3.0")])
                # create ordered operation dicitonary for this edict
                operation = [
                    2,  # two means "Limit_order_cancel"
                    OrderedDict(
                        [
                            ("fee", fee),
                            ("fee_paying_account", account_id),
                            ("order", order_id),
                            ("extensions", []),
                        ]
                    ),
                ]
                # append the ordered dict to the trx operations list
                tx_operations.append(operation)
        # SCALE ORDER SIZE TO FUNDS ON HAND
        if self.constants.signing.AUTOSCALE or self.constants.signing.CORE_FEES:
            # ==========================================================================
            metanode_assets = self.metanode.assets  # DISCRETE SQL QUERY
            metanode_objects = self.metanode.objects  # DISCRETE SQL QUERY
            # ==========================================================================
            metanode_currency = metanode_assets[currency_name]
            metanode_asset = metanode_assets[asset_name]
            metanode_core = metanode_assets[metanode_objects["1.3.0"]["name"]]
            currency_balance = metanode_currency["balance"]["free"]
            asset_balance = metanode_asset["balance"]["free"]
            core_balance = metanode_core["balance"]["free"]
            if self.constants.signing.AUTOSCALE and buy_edicts + sell_edicts:
                # autoscale buy edicts
                if buy_edicts:
                    currency_value = 0
                    # calculate total value of each amount in the order
                    for idx, _ in enumerate(buy_edicts):
                        currency_value += (
                            buy_edicts[idx]["amount"] * buy_edicts[idx]["price"]
                        )
                    # scale the order amounts to means
                    scale = (
                        self.constants.core.DECIMAL_SIXSIG
                        * decimal(currency_balance)
                        / (currency_value + self.constants.core.DECIMAL_SATOSHI)
                    )
                    if scale < 1:
                        print(
                            it(
                                "yellow",
                                "ALERT: scaling buy edicts to means: %.3f" % scale,
                            )
                        )
                        for idx, _ in enumerate(buy_edicts):
                            buy_edicts[idx]["amount"] *= scale
                # autoscale sell edicts
                if sell_edicts:
                    asset_total = 0
                    # calculate total amount in the order
                    for idx, _ in enumerate(sell_edicts):
                        asset_total += sell_edicts[idx]["amount"]
                    scale = (
                        self.constants.core.DECIMAL_SIXSIG
                        * decimal(asset_balance)
                        / (asset_total + self.constants.core.DECIMAL_SATOSHI)
                    )
                    # scale the order amounts to means
                    if scale < 1:
                        print(
                            it(
                                "yellow",
                                "ALERT: scaling sell edicts to means: %.3f" % scale,
                            )
                        )
                        for idx, _ in enumerate(sell_edicts):
                            sell_edicts[idx]["amount"] *= scale
            # ALWAYS SAVE LAST 2 BITSHARES FOR FEES
            if self.constants.signing.CORE_FEES and (
                buy_edicts + sell_edicts and ("1.3.0" in [asset_id, currency_id])
            ):
                # print(bitshares, 'BTS balance')
                # when BTS is the currency don't spend the last 2
                if currency_id == "1.3.0" and buy_edicts:
                    bts_value = 0
                    # calculate total bts value of each amount in the order
                    for idx, _ in enumerate(buy_edicts):
                        bts_value += (
                            buy_edicts[idx]["amount"] * buy_edicts[idx]["price"]
                        )
                    # scale the order amounts to save last two bitshares
                    scale = (
                        self.constants.core.DECIMAL_SIXSIG
                        * max(0, (core_balance - 2))
                        / (bts_value + self.constants.core.DECIMAL_SATOSHI)
                    )
                    if scale < 1:
                        print(
                            it(
                                "yellow",
                                "ALERT: scaling buy edicts for fees: %.4f" % scale,
                            )
                        )
                        for idx, _ in enumerate(buy_edicts):
                            buy_edicts[idx]["amount"] *= scale
                # when BTS is the asset don't sell the last 2
                if asset_id == "1.3.0" and sell_edicts:
                    bts_total = 0
                    # calculate total of each bts amount in the order
                    for idx, _ in enumerate(sell_edicts):
                        bts_total += sell_edicts[idx]["amount"]
                    scale = (
                        self.constants.core.DECIMAL_SIXSIG
                        * decimal(max(0, (core_balance - 2)))
                        / (bts_total + self.constants.core.DECIMAL_SATOSHI)
                    )
                    # scale the order amounts to save last two bitshares
                    if scale < 1:
                        print(
                            it(
                                "yellow",
                                "ALERT: scaling sell edicts for fees: %.4f" % scale,
                            )
                        )
                        for idx, _ in enumerate(sell_edicts):
                            sell_edicts[idx]["amount"] *= scale
        # after scaling recombine buy and sell
        create_edicts = buy_edicts + sell_edicts
        # REMOVE DUST EDICTS
        if self.constants.signing.DUST and create_edicts:
            create_edicts2 = []
            dust = self.constants.signing.DUST * 100000 / 10 ** asset_precision
            for idx, _ in enumerate(create_edicts):
                if create_edicts[idx]["amount"] > dust:
                    create_edicts2.append(create_edicts[idx])
                else:
                    print(
                        it("red", "WARN: removing dust threshold %s order" % dust),
                        create_edicts[idx],
                    )
            create_edicts = create_edicts2[:]  # copy as new list
            del create_edicts2
        # TRANSLATE LIMIT ORDERS TO GRAPHENE
        for idx, _ in enumerate(create_edicts):
            price = create_edicts[idx]["price"]
            amount = create_edicts[idx]["amount"]
            op_exp = int(create_edicts[idx]["expiration"])
            # convert zero expiration flag to "really far in future"
            if op_exp == 0:
                op_exp = self.constants.core.END_OF_TIME
            op_expiration = to_iso_date(op_exp)
            # we'll use ordered dicts and put items in api specific order
            min_to_receive = OrderedDict({})
            amount_to_sell = OrderedDict({})
            # derive min_to_receive & amount_to_sell from price & amount
            # means SELLING currency RECEIVING assets
            if create_edicts[idx]["op"] == "buy":
                min_to_receive["amount"] = int(amount * 10 ** asset_precision)
                min_to_receive["asset_id"] = asset_id
                amount_to_sell["amount"] = int(
                    amount * price * 10 ** currency_precision
                )
                amount_to_sell["asset_id"] = currency_id
            # means SELLING assets RECEIVING currency
            if create_edicts[idx]["op"] == "sell":
                min_to_receive["amount"] = int(
                    amount * price * 10 ** currency_precision
                )
                min_to_receive["asset_id"] = currency_id
                amount_to_sell["amount"] = int(amount * 10 ** asset_precision)
                amount_to_sell["asset_id"] = asset_id
            # Limit_order_create fee ordered dictionary
            fee = OrderedDict([("amount", fees["create"]), ("asset_id", "1.3.0")])
            # create ordered dicitonary from each buy/sell operation
            operation = [
                1,
                OrderedDict(
                    [
                        ("fee", fee),  # OrderedDict
                        ("seller", account_id),  # "a.b.c"
                        ("amount_to_sell", amount_to_sell),  # OrderedDict
                        ("min_to_receive", min_to_receive),  # OrderedDict
                        ("expiration", op_expiration),  # self.constants.core.ISO8601
                        ("fill_or_kill", self.constants.signing.KILL_OR_FILL),  # bool
                        (
                            "extensions",
                            [],
                        ),  # always empty list for our purpose
                    ]
                ),
            ]
            tx_operations.append(operation)
        # prevent inadvertent huge number of orders
        tx_operations = tx_operations[: self.constants.signing.LIMIT]
        # the trx is just a regular dictionary we will convert to json later
        # the operations themselves must still be an OrderedDict
        trx = {
            "ref_block_num": ref_block_num,
            "ref_block_prefix": ref_block_prefix,
            "expiration": tx_expiration,
            "operations": tx_operations,
            "signatures": [],
            "extensions": [],
        }
        return trx
