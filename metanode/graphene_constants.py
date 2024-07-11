#!/usr/bin/env python
# DISABLE SELECT PYLINT TESTS
# pylint: disable=import-error, line-too-long, too-few-public-methods
# pylint: disable=bad-continuation
r"""
 ╔════════════════════════════════════════════════════╗
 ║ ╔═╗╦═╗╔═╗╔═╗╦ ╦╔═╗╔╗╔╔═╗  ╔╦╗╔═╗╔╦╗╔═╗╔╗╔╔═╗╔╦╗╔═╗ ║
 ║ ║ ╦╠╦╝╠═╣╠═╝╠═╣║╣ ║║║║╣   ║║║║╣  ║ ╠═╣║║║║ ║ ║║║╣  ║
 ║ ╚═╝╩╚═╩ ╩╩  ╩ ╩╚═╝╝╚╝╚═╝  ╩ ╩╚═╝ ╩ ╩ ╩╝╚╝╚═╝═╩╝╚═╝ ║
 ╚════════════════════════════════════════════════════╝
~
GLOBAL CONSTANTS AND USER CONFIGURATION FOR DEX CONNECTIVITY
"""

# STANDARD MODULES
import os
from decimal import Decimal
from random import randint

# GRAPHENE MODULES
from .graphene_utils import assets_from_pairs, invert_pairs, it, sls


class GrapheneConstants:
    """
    the base class contains constants relevant to all graphene chains
    and chain specific constants for <your chain>
    the aim here is to have a single object
    which can be instatied either as:
        # chain agnostic constants, eg.
            # constants = GrapheneConstants()
            # constants.core.BASE58
            # constants.metanode.TIMEOUT
            # constants.signing.TIMEOUT
        # chain specific constants, eg.
            # constants = GrapheneConstants(chain_name)
            # constants.chain.NODES
            # constants.chain.PAIRS
            # constants.chain.ACCOUNT
    and then passed through instantiated class objects as CONSTANTS
    """

    def __init__(self, chain_name=None):
        """
        this requires no user configuration,
        advanced might configure a testnet or additional graphene based blockchain here
        """
        self.chains = {
            "peerplays": {
                "core": "PPY",
                "config": PeerplaysConfig,
                "id": "6b6b5f0ce7a36d323768e534f3edb41c6d6332a541a95725b98e28d140850134",
            },
            "peerplays testnet": {
                "core": "TEST",
                "config": PeerplaysTestnetConfig,
                # "7c1c72eb738b3ff1870350f85daca27e2d0f5dd25af27df7475fbd92815e421e"
                "id":"195d4e865e3a27d2b204de759341e4738f778dd5c4e21860c7e8bf1bd9c79203"
            },
            "bitshares": {
                "core": "BTS",
                "config": BitsharesConfig,
                "id": "4018d7844c78f6a6c41c6a552b898022310fc5dec06da467ee7905a8dad512c8",
            },
            "bitshares testnet": {
                "core": "TEST",
                "config": BitsharesTestnetConfig,
                "id": "39f5e2ede1f8bc1a3a54a7914414e3779e33193f1f5693510e73cb7a87617447",
            },
            # ~ "rudex": {
            # ~ "core": "GPH",
            # ~ "config": RudexConfig,
            # ~ "id": (
            # ~ "7fcf452d6bb058949cdc875b13c8908c8f54b0f264c39faf8152b682af0740ee"
            # ~ ),
            # ~ },
            # ~ "hive": {
            # ~ "core": "HIVE",
            # ~ "config": HiveConfig,
            # ~ "id": (
            # ~ "18dcf0a285365fc58b71f18b3d3fec954aa0c141c44e4e5cb4cf777b9eab274e"
            # ~ ),
            # ~ },
        }
        # instantiate hummingbot and graphene core constants
        self.core = CoreConstants
        self.core.CHAINS = list(self.chains.keys())
        # instantiate user configuration for public and private api connectivity
        self.metanode = MetanodeConfig
        self.signing = SigningConfig
        # instantiate user configuration specific to one blockchain
        # normalize user inputs derive some constants that will prove useful later
        # constants derived at instantiation still formatted upper `constants.chain.XXX`
        if chain_name is not None:
            self.chain = self.chains[chain_name.lower()]["config"]
            self.chain.NAME = chain_name.lower()
            self.chain.CORE = self.chains[self.chain.NAME]["core"].upper()
            self.chain.ID = self.chains[self.chain.NAME]["id"]
            self.chain.NODES = [node.lower() for node in sls(self.chain.NODES)]
            self.chain.PAIRS = [pair.upper() for pair in sls(self.chain.PAIRS)]
            # filter out duplicate inverted pairs
            self.chain.PAIRS = [
                i for i in self.chain.PAIRS if i not in invert_pairs(self.chain.PAIRS)
            ]
            self.chain.INVERTED_PAIRS = invert_pairs(self.chain.PAIRS)
            self.chain.ASSETS = list(set(assets_from_pairs(self.chain.PAIRS) + [self.chain.CORE]))
            self.chain.CORE_PAIRS = [
                i
                for i in [
                    self.chain.CORE + "-" + asset
                    for asset in self.chain.ASSETS
                    if asset != self.chain.CORE
                ]
                if i not in self.chain.PAIRS and i not in self.chain.INVERTED_PAIRS
            ]
            self.chain.INVERTED_CORE_PAIRS = invert_pairs(self.chain.CORE_PAIRS)
            self.chain.ALL_PAIRS = (
                self.chain.PAIRS
                + self.chain.CORE_PAIRS
                + self.chain.INVERTED_PAIRS
                + self.chain.INVERTED_CORE_PAIRS
            )
            self.chain.DATABASE = (
                self.core.PATH
                + "/database/"
                + self.chain.NAME.replace(" ", "_")
                + ".db"
            )
            self.DATABASE_FOLDER = self.core.PATH + "/database"
            self.chain.TITLE = self.chain.NAME.title()
            if not hasattr(self.chain, "PREFIX"):
                self.chain.PREFIX = self.chain.CORE


class CoreConstants:
    """
    ╔═╗╔═╗╦═╗╔═╗
    ║  ║ ║╠╦╝║╣
    ╚═╝╚═╝╩╚═╚═╝
    these constants require no user configuration
    """

    # about 75 years in future; used for expiration date of limit orders
    END_OF_TIME = 4 * 10**9
    # membership_expiration_date is set to this date if lifetime member
    LTM = "2106-02-07T06:28:15"
    # ISO8601 time format; 'graphene time'
    ISO8601 = "%Y-%m-%dT%H:%M:%S%Z"
    # bitsharesbase/operationids.py
    OP_IDS = {
        "LimitOrderCreate": 1,
        "LimitOrderCancel": 2,
    }
    # swap keys/values to index names by number
    OP_NAMES = {v: k for k, v in OP_IDS.items()}
    # bitsharesbase/objecttypes.py used by ObjectId() to confirm a.b.c
    TYPES = {
        "account": 2,
        "asset": 3,
        "limit_order": 7,
    }  # 1.2.x  # 1.3.x  # 1.7.x
    # base58 encoding and decoding; this is alphabet defined as bytes
    # ~ BASE58 = "".join(
    # ~ [i for i in string.digits + string.ascii_letters if i not in "Il0O"]
    # ~ ).encode()
    # ~ print(b"123456789abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ")
    # ~ print(BASE58)
    # ~ # hex encoding and decoding
    # ~ HEXDIGITS = string.hexdigits
    # ~ print(f"0123456789abcdefABCDEF\n{HEXDIGITS}")
    # base58 encoding and decoding; this is alphabet defined:
    BASE58 = b"123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    # hex encoding and decoding
    HEXDIGITS = "0123456789abcdefABCDEF"
    # numerical constants
    GRAPHENE_MAX = int(10**15)
    DECIMAL_NIL = Decimal(1) / GRAPHENE_MAX
    DECIMAL_NAN = Decimal("nan")
    DECIMAL_0 = Decimal(0)
    DECIMAL_SATOSHI = Decimal(0.00000001)
    DECIMAL_SIXSIG = Decimal(0.999999)
    PATH = os.path.dirname(os.path.abspath(__file__))


class MetanodeConfig:
    """
    ╔╦╗╔═╗╔╦╗╔═╗╔╗╔╔═╗╔╦╗╔═╗
    ║║║║╣  ║ ╠═╣║║║║ ║ ║║║╣
    ╩ ╩╚═╝ ╩ ╩ ╩╝╚╝╚═╝═╩╝╚═╝
    these constants relate to the timing of the metanode server and trustless client
    metanode can run with a single node, a few nodes, or a large selection of nodes
    depending on the size of the public api network you've whitelisted,
    some configuration may be required
    its suggested that you familiarize yourself with the codebase
    prior to adjusting anything here
    """

    # ==================================================================================
    # SECURITY hard coded list prevents SQL injection in _get_table()
    # ==================================================================================
    VALID_TABLES = [
        "chain",
        "account",
        "objects",
        "pairs",
        "assets",
        "nodes",
        "timing",
    ]
    # ==================================================================================
    # SECURITY this hard coded list prevents SQL injection in maven and oracle updates
    # ==================================================================================
    TRACKER_TABLE = {
        # account table
        "fees_account": "account",
        "ltm": "account",
        "cancels": "account",
        # assets table
        "supply": "assets",
        "fees_asset": "assets",
        "balance": "assets",
        # pairs table
        "ops": "pairs",
        "last": "pairs",
        "book": "pairs",
        "history": "pairs",
        "opens": "pairs",
        "fills": "pairs",
        # timing table
        "ping": "timing",
        "handshake": "timing",
        "blocktime": "timing",
        "server": "timing",
        "blocknum": "timing",
        "read": "timing",
    }
    STATUS_CODES = {  # used by latency testing
        200: "CONNECTED",
        1001: "NO HISTORY",
        1002: "WRONG CHAIN ID",
        1003: "FORKED FROM MAINNET",
        1004: "STALE BLOCKTIME",
        1005: "SLOW HANDSHAKE",
        1006: "SLOW PING",
        1007: "CONNECTION FAILED",
        1008: "CONNECTION TIMEOUT",
    }
    DEV = True  # additional printing in terminal
    REGENERATION_TUPLE = randint(120, 240)
    MAVENS = 7  # number of processes collecting data
    MAVEN_WINDOW = 7  # window depth for mode(sooths)
    LATENCY_THRESHER_TIMEOUT = 10  # if status 1008 on all nodes, increase
    LATENCY_TASK_PAUSE = 60  # time between testing same node twice
    MAVEN_CACHE_HARVEST_JOIN = 8
    CACHE_RESTART_JOIN = 10
    MAVEN_RPC_RATIO = 3
    MAVEN_HIGH_LOW_RATIO = 20
    MAVEN_PAUSE = 0.1
    ORACLE_PAUSE = 0.5
    MAX_PING = 1
    SQL_EXECUTE_PAUSE = (0.2, True)


class SigningConfig:
    """
    ╔═╗╦╔═╗╔╗╔╦╔╗╔╔═╗
    ╚═╗║║ ╦║║║║║║║║ ╦
    ╚═╝╩╚═╝╝╚╝╩╝╚╝╚═╝
    these constants relate to the client side graphene scripting of
        transcription, serialization, signing, and broadcast
        of authenticate, buy, sell, and cancel operations
    """

    # timeout during websocket handshake; default 4 seconds
    HANDSHAKE_TIMEOUT = 4
    # multiprocessing handler lifespan, default 20 seconds
    PROCESS_TIMEOUT = 20
    # default False for persistent limit orders
    KILL_OR_FILL = False
    # default True scales elements of oversize gross order to means
    AUTOSCALE = True
    # default True to never spend last 2 core tokens (for fees)
    CORE_FEES = True
    # multiprocessing incarnations, default 3 attempts
    ATTEMPTS = 3
    # prevent extreme number of AI generated edicts; default 20
    # NOTE batch transactions are currently disable
    # so this parameter is moot at the hummingbot level
    LIMIT = 20
    # ignore orders value less than ~DUST core in value; 0 to disable
    DUST = 0
    # True = heavy print output
    DEV = True


class PeerplaysConfig:
    """
    ╔═════════════════════════════╗
    ║     HUMMINGBOT GRAPHENE     ║
    ║ ╔═╗╔═╗╔═╗╦═╗╔═╗╦  ╔═╗╦ ╦╔═╗ ║
    ║ ╠═╝║╣ ║╣ ╠╦╝╠═╝║  ╠═╣╚╦╝╚═╗ ║
    ║ ╩  ╚═╝╚═╝╩╚═╩  ╩═╝╩ ╩ ╩ ╚═╝ ║
    ║ DEX MARKET MAKING CONNECTOR ║
    ╚═════════════════════════════╝
    configuration details specific to peerplays mainnet
    """

    ACCOUNT = "test1" # for example purposes
    NODES = [
        "wss://ca.peerplays.info/",
        "wss://de.peerplays.xyz/",
        "wss://pl.peerplays.org/",
        "ws://96.46.48.98:18090",
        "wss://peerplaysblockchain.net/mainnet/api",
        "ws://witness.serverpit.com:8090",
        "ws://api.i9networks.net.br:8090",
        "wss://node.mainnet.peerblock.trade"
    ]
    PAIRS = ["BTC-PPY", "HIVE-PPY", "HBD-PPY"]


class PeerplaysTestnetConfig:
    """
    configuration details specific to peerplays testnet
    """

    ACCOUNT = "litepresence1"
    NODES = ["wss://testnet.peerplays.download/api"]
    PAIRS = ["TEST-ABC", "TEST-DEFG"]


class BitsharesConfig:
    """
    ╔═════════════════════════════╗
    ║     HUMMINGBOT GRAPHENE     ║
    ║  ╔╗ ╦╔╦╗╔═╗╦ ╦╔═╗╦═╗╔═╗╔═╗  ║
    ║  ╠╩╗║ ║ ╚═╗╠═╣╠═╣╠╦╝║╣ ╚═╗  ║
    ║  ╚═╝╩ ╩ ╚═╝╩ ╩╩ ╩╩╚═╚═╝╚═╝  ║
    ║ DEX MARKET MAKING CONNECTOR ║
    ╚═════════════════════════════╝
    configuration details specific to bitshares mainnet
    """

    ACCOUNT = "litepresence1"
    NODES = [
        "wss://api.bts.mobi/wss",
        "wss://eu.nodes.bitshares.ws/ws",
        "wss://cloud.xbts.io/wss",
        "wss://dex.iobanker.com/wss",
        "wss://bts.mypi.win/wss",
        "wss://node.xbts.io/wss",
        "wss://public.xbts.io/ws",
        "wss://btsws.roelandp.nl/wss",
        "wss://singapore.bitshares.im/wss",
    ]
    # [
    #     "wss://api.bts.mobi/wss",
    #     "wss://api-us.61bts.com/wss",
    #     "wss://cloud.xbts.io/ws",
    #     "wss://api.dex.trading/wss",
    #     "wss://eu.nodes.bitshares.ws/ws",
    #     "wss://api.pindd.club/ws",
    #     "wss://dex.iobanker.com/ws",
    #     "wss://public.xbts.io/ws",
    #     "wss://node.xbts.io/ws",
    #     "wss://node.market.rudex.org/ws",
    #     "wss://nexus01.co.uk/ws",
    #     "wss://api-bts.liondani.com/ws",
    #     "wss://api.bitshares.bhuz.info/wss",
    #     "wss://btsws.roelandp.nl/ws",
    #     "wss://hongkong.bitshares.im/ws",
    #     "wss://node1.deex.exchange/wss",
    #     "wss://api.cnvote.vip:888/wss",
    #     "wss://bts.open.icowallet.net/ws",
    #     "wss://api.weaccount.cn/ws",
    #     "wss://api.61bts.com",
    #     "wss://api.btsgo.net/ws",
    #     "wss://bitshares.bts123.cc:15138/wss",
    #     "wss://singapore.bitshares.im/wss",
    # ]
    PAIRS = ["HONEST.USD-HONEST.BTC"]


class BitsharesTestnetConfig:
    """
    configuration details specific to bitshares testnet
    """

    ACCOUNT = ""
    NODES = [
        "wss://testnet.bitshares.im/ws",
        "wss://testnet.dex.trading/",
        "wss://testnet.xbts.io/ws",
        "wss://api-testnet.61bts.com/ws",
    ]
    PAIRS = ["TEST-USD", "TEST-CNY"]


# NOTE these are not yet tested...  may require some dev; pull requests welcome
# ~ class RudexConfig:
# ~ """
# ~ ╔═════════════════════════════╗
# ~ ║     HUMMINGBOT GRAPHENE     ║
# ~ ║       ╦═╗╦ ╦╔╦╗╔═╗╔╗╔═      ║
# ~ ║       ╠╦╝║ ║ ║║║╣  ╠╣       ║
# ~ ║       ╩╚═╚═╝═╩╝╚═╝═╝╚╝      ║
# ~ ║ DEX MARKET MAKING CONNECTOR ║
# ~ ╚═════════════════════════════╝
# ~ configuration details specific to rudex mainnet
# ~ """
# ~ FIXME needs to be debugged / unit tested, may be some rpc differences
# ~ /testnet?
# ~ ACCOUNT = "litepresence1"
# ~ NODES = ["wss://node.gph.ai"]
# ~ PAIRS = ["GPH-BTS", "PPY-BTS"]
# ~ class HiveConfig:
# ~ """
# ~ ╔═════════════════════════════╗
# ~ ║     HUMMINGBOT GRAPHENE     ║
# ~ ║         ╦ ╦╦╦  ╦╔═╗         ║
# ~ ║         ╠═╣║╚╗╔╝║╣          ║
# ~ ║         ╩ ╩╩ ╚╝ ╚═╝         ║
# ~ ║ DEX MARKET MAKING CONNECTOR ║
# ~ ╚═════════════════════════════╝
# ~ configuration details specific to hive mainnet
# ~ """
# ~ raise NotImplementedError
# ~ FIXME needs to be debugged / unit tested, may be some rpc differences
# ~ /testnet?
# ~ https://developers.hive.io/quickstart/hive_full_nodes.html
# ~ https://steemit.com/full-nodes/@fullnodeupdate/full-api-node-update---762018
# ~ # https://github.com/openhive-network/hive
# ~ # https://api.hive.blog
# ~ # https://testnet.openhive.network
# ~ ACCOUNT = "rolandp"
# ~ NODES = ["ws://testnet.openhive.network:8090"]
# ~ NODES = [
# ~ "wss://rpc.steemviz.com/wss",
# ~ "wss://steemd.minnowsupportproject.org/wss",
# ~ "wss://steemd.pevo.science/wss",
# ~ "wss://steemd.privex.io/wss",
# ~ "wss://rpc.buildteam.io/wss",
# ~ "wss://gtg.steem.house:8090/wss",
# ~ ]
# ~ PAIRS = ["HBD-HIVE"]
def unit_test():
    """
    test class inheritance
    """
    constants = GrapheneConstants()
    dispatch = {str(idx): chain for idx, chain in enumerate(constants.core.CHAINS)}
    for key, value in dispatch.items():
        if "testnet" not in value:
            print(key + ": " + it("blue", value))
        else:
            print(key + ": " + it("purple", value))
    chain = dispatch[input("Enter choice: ")]
    CONSTANTS = GrapheneConstants()  # pylint: disable=invalid-name
    print(CONSTANTS.core.BASE58)
    print(CONSTANTS.metanode.STATUS_CODES)
    print(CONSTANTS.signing.ATTEMPTS)
    # chain specific constants, eg.
    constants = GrapheneConstants(chain)
    print(constants.chain.NODES)
    print(constants.chain.PAIRS)
    print(constants.chain.INVERTED_PAIRS)
    print(constants.chain.ASSETS)
    print(constants.chain.CORE)
    print(constants.chain.PREFIX)
    # note core / metanode / etc. constants still work this way
    print(constants.metanode.STATUS_CODES)


if __name__ == "__main__":
    unit_test()
