r"""
 ╔════════════════════════════════════════════════════╗
 ║ ╔═╗╦═╗╔═╗╔═╗╦ ╦╔═╗╔╗╔╔═╗  ╔╦╗╔═╗╔╦╗╔═╗╔╗╔╔═╗╔╦╗╔═╗ ║
 ║ ║ ╦╠╦╝╠═╣╠═╝╠═╣║╣ ║║║║╣   ║║║║╣  ║ ╠═╣║║║║ ║ ║║║╣  ║
 ║ ╚═╝╩╚═╩ ╩╩  ╩ ╩╚═╝╝╚╝╚═╝  ╩ ╩╚═╝ ╩ ╩ ╩╝╚╝╚═╝═╩╝╚═╝ ║
 ╚════════════════════════════════════════════════════╝
~
UNIT TEST AUTHENTICATED OPS
"""

# STANDARD MODULES
import json
from getpass import getpass

# GRAPHENE MODULES
from .graphene_auth import GrapheneAuth
from .graphene_constants import GrapheneConstants
from .graphene_metanode_server import GrapheneTrustlessClient
from .graphene_utils import it


def sample_orders(auth, constants, pair, active):
    """
    sample orders of in-script demo
    """
    order = json.loads(auth.prototype_order(pair))
    order["header"]["wif"] = active
    order1, order2, order3, order4 = dict(order), dict(order), dict(order), dict(order)
    # login
    order1["edicts"] = [{"op": "login"}]
    # cancel all
    order2["edicts"] = [{"op": "cancel", "ids": ["1.7.X"]}]
    # place two limit orders
    order3["edicts"] = [
        {
            "op": "buy",
            "amount": 1,
            "price": 0.9,
            "expiration": 0,
        },
        {
            "op": "sell",
            "amount": 1,
            "price": 1.1,
            "expiration": 0,
        },
    ]
    # query open orders from the metanode and cancel 2 of them
    metanode = GrapheneTrustlessClient(constants)
    metanode_pairs = metanode.pairs
    orders = [order["order_number"] for order in metanode_pairs[pair]["opens"]][:2:]
    order4["edicts"] = [{"op": "cancel", "ids": orders}]
    return order1, order2, order3, order4


def unit_test():
    """
    'broker' an order
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
    print("\033c")
    dispatch = {str(idx): pair for idx, pair in enumerate(constants.chain.PAIRS)}
    for key, value in dispatch.items():
        print(key + ": " + value)
    pair = dispatch[input("Enter choice: ")]
    print("\033c")
    print("WARNING: this script will buy/sell whatever amount is hard coded inline")
    input("press Enter to continue, Ctrl+c to cancel")
    active = getpass("Enter WIF:  ")
    print("\033c")
    auth = GrapheneAuth(constants, active)
    order1, order2, order3, order4 = sample_orders(auth, constants, pair, active)

    dispatch = {
        "1": order1,
        "2": order2,
        "3": order3,
        "4": order4,
    }
    choices = {
        "1": "authenticate",
        "2": "cancel all",
        "3": "buy and sell",
        "4": "cancel some",
    }
    print(it("yellow", "   UNIT TEST\n"))
    for key, val in choices.items():
        print(it("green", key), ":", it("cyan", val))
    choice = input("\n\n")
    print(auth.broker(dispatch[choice]))


if __name__ == "__main__":
    print("\033c")
    unit_test()
