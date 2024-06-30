##!/usr/bin/env python
# DISABLE SELECT PYLINT TESTS
# pylint:
r"""
 ╔════════════════════════════════════════════════════╗
 ║ ╔═╗╦═╗╔═╗╔═╗╦ ╦╔═╗╔╗╔╔═╗  ╔╦╗╔═╗╔╦╗╔═╗╔╗╔╔═╗╔╦╗╔═╗ ║
 ║ ║ ╦╠╦╝╠═╣╠═╝╠═╣║╣ ║║║║╣   ║║║║╣  ║ ╠═╣║║║║ ║ ║║║╣  ║
 ║ ╚═╝╩╚═╩ ╩╩  ╩ ╩╚═╝╝╚╝╚═╝  ╩ ╩╚═╝ ╩ ╩ ╩╝╚╝╚═╝═╩╝╚═╝ ║
 ╚════════════════════════════════════════════════════╝
DATABASE VISUALIZATION CLI GUI
"""

# STANDARD MODULES
import time
from random import choice

from .graphene_constants import GrapheneConstants

# GRAPHENE MODULES
from .graphene_metanode_client import GrapheneTrustlessClient
from .graphene_utils import at, it, two_tone
from .unit_test_dbux import convert


def unit_test():
    """
    instantiate a metanode client and test data methods
    """
    constants = GrapheneConstants("bitshares")

    metanode = GrapheneTrustlessClient(constants)

    methods = {
        "chain": metanode.chain,
        "pairs": metanode.pairs,
        "assets": metanode.assets,
        "account": metanode.account,
        "timing": metanode.timing,
        "nodes": metanode.nodes,
        "whitelist": metanode.whitelist,
        "objects": metanode.objects,
    }

    while True:
        pair = ""
        asset = ""
        method = choice(list(methods.keys()))
        data = methods[method]

        if method == "pairs":
            pair = choice(constants.chain.PAIRS)
            data = data[pair]

        elif method == "assets":
            asset = choice(constants.chain.ASSETS)
            data = data[asset]

        print("\033c")
        print(convert("metanode", "green"))
        print(it("yellow", "GrapheneTrustlessClient()"))
        print(two_tone(data, "blue", "purple"))
        print(it("green", f"metanode.{method} {pair}{asset}"))
        print(at((0, 0, 0, 0), ""))
        time.sleep(7)


if __name__ == "__main__":
    unit_test()
