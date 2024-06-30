##!/usr/bin/env python
# DISABLE SELECT PYLINT TESTS
# pylint: disable=bad-continuation
r"""
 ╔════════════════════════════════════════════════════╗
 ║ ╔═╗╦═╗╔═╗╔═╗╦ ╦╔═╗╔╗╔╔═╗  ╔╦╗╔═╗╔╦╗╔═╗╔╗╔╔═╗╔╦╗╔═╗ ║
 ║ ║ ╦╠╦╝╠═╣╠═╝╠═╣║╣ ║║║║╣   ║║║║╣  ║ ╠═╣║║║║ ║ ║║║╣  ║
 ║ ╚═╝╩╚═╩ ╩╩  ╩ ╩╚═╝╝╚╝╚═╝  ╩ ╩╚═╝ ╩ ╩ ╩╝╚╝╚═╝═╩╝╚═╝ ║
 ╚════════════════════════════════════════════════════╝
~
GRAPHENE BASE METANODE CLIENT
~
A TRUSTLESS CLIENT PROVIDING STATISICAL MODE DATA
FROM A GRAPHENE BLOCKCHAIN'S PUBLIC API NODES
FOR A SINGLE ACCOUNT AND - MULTIPLE - TRADING PAIRS
~
Because a personal node requires expertise and resources
a long term connection to any node operator is improbable
trusting a 3rd party blochchain api node can be risky
some public api connenctions are faster than others
and querying a graphene chain is just not user friendly
~
The aim of metanode is to present stable API
utilizing a minimalist sqlite database
providing data for one account and multiple trading pairs
formatted as you'd expect from centralized exchange
with statitistically validated blockchain data
for decentralized exchange order book and user stream
with collection procedures offering 99.9999% uptime
"""
# STANDARD MODULES
from json import loads

# GRAPHENE MODULES
from .graphene_constants import GrapheneConstants
from .graphene_sql import Sql
from .graphene_utils import it, ld2dd, two_tone
from .unit_test_dbux import convert


class GrapheneTrustlessClient:
    """
    metanode = GrapheneTrustlessClient()
    metanode.whitelist
    metanode.account
    metanode.timing
    metanode.assets
    metanode.chain
    metanode.nodes
    metanode.pairs
    ~
    every metanode.xyz method is a SQL database query and should be cached
    at time of use to dict(metanode_xyz) to avoid excess database lookups
    the format of each response is described in the docstrings below
    all of the data returned is as as a list or dict python object
    loaded from json and containing str/float/int values
    these responses are statistically clean "mode" or "median" as appropritate
    from all responding nodes the user has provided upon configuration
    """

    def __init__(self, constants: GrapheneConstants):
        self.constants = constants
        self.sql = Sql(self.constants)

    def _get_table(self, table):
        if table in self.constants.metanode.VALID_TABLES:
            # ==========================================================================
            # SECURITY - SQL INJECTION RISK at {table} fstring
            # ==========================================================================
            dml = {
                "query": f"""
                SELECT * FROM {table}
                """,
                "values": tuple(),
            }
            # ==========================================================================
            return self.sql.execute([dml])  # DISCRETE SQL QUERY
            # ==========================================================================
        raise ValueError("invalid table")

    @property
    def chain(self) -> dict:
        """
        returns dict with keys
        ~
        ["id", "name"]
        """
        return self._get_table("chain")[0]

    @property
    def account(self) -> dict:
        """
        returns dict with keys
        ~
        ["id", "name", "fees_account", "ltm", "cancels"]
        """
        return {
            k: v if k != "cancels" else loads(v) for k, v in self._get_table("account")[0].items()
        }

    @property
    def assets(self) -> dict:
        """
        returns a dict of dicts keyed by asset name; with subdict keys:
        ~
        ["id", "fees_asset", "balance", "precision", "supply"]
        """
        return ld2dd(self._get_table("assets"), key="name")

    @property
    def objects(self) -> dict:
        """
        returns a dict of dicts keyed by asset id; with subdict keys:
        ~
        ["name", "precision"]
        """
        return ld2dd(self._get_table("objects"), key="id")

    @property
    def pairs(self) -> dict:
        """
        returns a dict of dict of pairs keyed by trading pair name; with subdict keys:
        ~
        ["id", "last", "book", "history", "ops", "fills", "opens"]
        """
        return ld2dd(self._get_table("pairs"), key="name")

    @property
    def nodes(self) -> dict:
        """
        returns a dict of dicts of nodes keyed by websocket url; with subdict keys:
        ~
        ["ping", "code", "status", "handshake"]
        """
        return ld2dd(self._get_table("nodes"), key="url")

    @property
    def timing(self) -> dict:
        """
        returns a list of dicts of timing items, with keys:
        ~
        ["ping", "read", "begin", "blocktime", "blocknum", "handshake"]
        """
        return self._get_table("timing")[0]

    @property
    def whitelist(self) -> list:
        """
        returns a dynamic list of node urls; tested and sorted by latency
        ["wss://", "wss://", ...]
        """
        nodes = self._get_table("nodes")
        if len(nodes) > 1:
            nodes = [i for i in nodes if i["code"] == 200]
            nodes = sorted(nodes, key=lambda d: d["ping"])
        nodes = [i["url"] for i in nodes]
        return nodes


def unit_test():
    """
    Test client side of metanode
    """
    constants = GrapheneConstants()
    dispatch = {str(idx): chain for idx, chain in enumerate(constants.core.CHAINS)}
    for key, value in dispatch.items():
        if "testnet" not in value:
            print(key + ": " + it("blue", value))
        else:
            print(key + ": " + it("purple", value))
    chain = dispatch[input("Enter choice: ")]
    constants = GrapheneConstants(chain)
    metanode = GrapheneTrustlessClient(constants)
    methods = {
        "account": metanode.account,
        "assets": metanode.assets,
        "chain": metanode.chain,
        "nodes": metanode.nodes,
        "objects": metanode.objects,
        "pairs": metanode.pairs,
        "timing": metanode.timing,
        "whitelist": metanode.whitelist,
    }
    for name, method in methods.items():
        print(convert(name, "green"))
        print(two_tone(method, "blue", "purple"))
        print("\n\n\n")


if __name__ == "__main__":
    unit_test()
