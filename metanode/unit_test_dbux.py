# pylint: disable=bad-continuation, too-many-branches, too-many-statements
# pylint: disable=too-many-locals
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
from json import loads
from random import choice, randint
from sqlite3 import OperationalError

# GRAPHENE MODULES
from .graphene_constants import GrapheneConstants
from .graphene_sql import Sql
from .graphene_utils import at, it, ld2dd, precision, two_tone

LOGO = """
╔═╗
║ ╦
╚═╝
╦═╗
╠╦╝
╩╚═
╔═╗
╠═╣
╩ ╩
╔═╗
╠═╝
╩
╦ ╦
╠═╣
╩ ╩
╔═╗
║╣
╚═╝
╔╗╔
║║║
╝╚╝
╔═╗
║╣
╚═╝\n\n\n\n
╔╦╗
║║║
╩ ╩
╔═╗
║╣
╚═╝
╔╦╗
 ║
 ╩
╔═╗
╠═╣
╩ ╩
╔╗╔
║║║
╝╚╝
╔═╗
║ ║
╚═╝
╔╦╗
 ║║
═╩╝
╔═╗
║╣
╚═╝
""".replace("    ", "")

LETTERS = {
    "a": """
╔═╗
╠═╣
╩ ╩ """,
    "b": """
╔╗
╠╩╗
╚═╝ """,
    "c": """
╔═╗
║
╚═╝ """,
    "d": """
╔╦╗
 ║║
═╩╝ """,
    "e": """
╔═╗
║╣
╚═╝ """,
    "f": """
╔═╗
╠╣
╚   """,
    "g": """
╔═╗
║ ╦
╚═╝ """,
    "h": """
╦ ╦
╠═╣
╩ ╩ """,
    "i": """
 ╦
 ║
 ╩  """,
    "j": """
 ╦
 ║
╚╝  """,
    "k": """
╦╔═
╠╩╗
╩ ╩ """,
    "l": """
╦
║
╩═╝ """,
    "m": """
╔╦╗
║║║
╩ ╩ """,
    "n": """
╔╗╔
║║║
╝╚╝ """,
    "o": """
╔═╗
║ ║
╚═╝ """,
    "p": """
╔═╗
╠═╝
╩   """,
    "q": """
╔═╗
║═╬╗
╚═╝╚""",
    "r": """
╦═╗
╠╦╝
╩╚═ """,
    "s": """
╔═╗
╚═╗
╚═╝ """,
    "t": """
╔╦╗
 ║
 ╩  """,
    "u": """
╦ ╦
║ ║
╚═╝ """,
    "v": """
╦  ╦
╚╗╔╝
 ╚╝  """,
    "w": """
╦ ╦
║║║
╚╩╝ """,
    "x": """
═╗╔
╔╬╝
╝╚═ """,
    "y": """
╦ ╦
╚╦╝
 ╩  """,
    "z": """
══╦
╔═╝
╩══ """,
    " ": """    ,
    ,
     """,
    "-": """
   ,
 ═
    """,
    ".": """
   ,
   ,
 ¤  """,
}


def convert(text, foreground, printing=False):
    """
    Converts regular text text to banner3D text
    """

    letters = {k: v.replace(",", "").strip("\n").split("\n") for k, v in LETTERS.items()}

    end_string = ""

    # only lowercase text is accepted
    text = text.lower()

    # loop through letter rows
    for row in range(3):
        # loop through the characters on the text
        for letter in text:
            try:
                # get the correct ASCII row and letter
                if row != 2:
                    string = letters[letter][row].ljust(3)
                else:
                    string = letters[letter][row].ljust(3)[:-1]
            except KeyError:
                raise Exception(
                    f"\n\n\nSorry, the character '{letter}' is not currently available."
                )
            except IndexError:
                string = "   "
            # initialize `new_string`
            new_string = ""
            # append colored characters to final string
            for char in string:
                if char != " ":
                    new_string += it(foreground, char)
                else:
                    new_string += char
            # print each letters correct row
            end_string += new_string
        # newline at end of ASCII row
        end_string += "\n"

    if printing:
        print(end_string)

    return end_string


TIME_DURATION_UNITS = (
    ("week", 60 * 60 * 24 * 7),
    ("day", 60 * 60 * 24),
    ("hour", 60 * 60),
    ("min", 60),
    ("sec", 1),
)


def human_time_duration(seconds):
    """
    Convert seconds to hrs, mins, etc
    """
    if seconds == 0:
        return "inf"
    parts = []
    for unit, div in TIME_DURATION_UNITS:
        amount, seconds = divmod(int(seconds), div)
        if amount > 0:
            parts.append("{} {}{}".format(amount, unit, "" if amount == 1 else "s"))
    return ", ".join(parts)


def animate(sql):
    """
    7-second animated bifurcation plot
    """
    width = 260
    height = 65

    def plot(x_list, y_list):
        query = f"""
            SELECT * FROM timing
        """
        timing = sql.execute(query)[0]

        for idx, x_pos in enumerate(x_list):
            print(
                it(
                    choice(["green", "blue", "purple"]),
                    at(
                        (
                            (int(x_pos * (width / 4) - (width / 2)) * 2),
                            -(int(y_list[idx] * height)) + height,
                            0,
                            0,
                        ),
                        choice(["¤", "¤", "¤", " "]),
                    ),
                )
            )
            time.sleep(0.01)
            # ==========================================================================
            # HIGH SPEED TIMING
            # ==========================================================================
            if not idx % 20:
                print(
                    at(
                        (80, 5, 0, 0),
                        it("white", "BLOCKTIME:   ") + it("yellow", str(timing["blocktime"])),
                    )
                )
                print(
                    at(
                        (80, 2, 60, 1),
                        it("white", "LATENCY:     ")
                        + two_tone(
                            str(precision(time.time() - timing["blocktime"], 2)),
                            "purple",
                            "blue",
                        ),
                    )
                )
                if time.time() - timing["blocktime"] > 30:
                    print(at((60, 11, 70, 4), convert("WARNING FEED IS STALE", "red")))
                print(
                    at(
                        (80, 4, 0, 0),
                        it("white", "BLOCKNUM:    ") + it("yellow", str(timing["blocknum"])),
                    )
                )
                print(
                    at(
                        (80, 3, 47, 1),
                        it("white", "RUNTIME:     ")
                        + two_tone(
                            str(human_time_duration(int(time.time() - timing["begin"]))),
                            "yellow",
                            "green",
                        ),
                    )
                )

    populations = []
    rates = []
    for rate in range(2000, 4000):
        ppopulation = float(0.4)
        for _ in range(100 + randint(-10, 10)):
            population = float(rate / 1000) * float(ppopulation) * float(1 - ppopulation)
            ppopulation = population
        populations.append(ppopulation)
        rates.append(rate / 1000)
    start = time.time()
    while time.time() - start < 7:
        cho = randint(0, len(rates) - 1)
        plot([rates[cho]], [populations[cho]])


def static():
    """
    static bifurcation plot
    """
    width = 260
    height = 65

    def plot(x_list, y_list):
        text = ""
        for idx, x_pos in enumerate(x_list):
            text += it(
                choice(["green", "blue", "purple"]),
                at(
                    (
                        (int(x_pos * (width / 4) - (width / 2)) * 2),
                        -(int(y_list[idx] * height)) + height,
                        0,
                        0,
                    ),
                    choice(["¤", "¤", "¤", " "]),
                ),
            )
        return text

    populations = []
    rates = []
    for rate in range(2000, 4000):
        ppopulation = float(0.4)
        for _ in range(100 + randint(-10, 10)):
            population = float(rate / 1000) * float(ppopulation) * float(1 - ppopulation)
            ppopulation = population
        populations.append(ppopulation)
        rates.append(rate / 1000)
    data = plot(rates, populations)
    print("\033c")
    print(data)


def main():
    """
    display database in human readable manner
    """
    print("\033c")
    constants = GrapheneConstants()
    dispatch = {str(idx): chain for idx, chain in enumerate(constants.core.CHAINS)}
    for key, value in dispatch.items():
        if "testnet" not in value:
            print(key + ": " + it("blue", value))
        else:
            print(key + ": " + it("purple", value))
    chain_name = dispatch[input("Enter choice: ")]
    constants = GrapheneConstants(chain_name)
    sql = Sql(constants)
    pairs_i = list(constants.chain.PAIRS)
    i = 0
    print("\033[?25l")
    try:
        while True:
            query = f"""
                SELECT * FROM chain
            """
            chain = sql.execute(query)
            query = f"""
                SELECT * FROM objects
            """
            objects = ld2dd(sql.execute(query), key="id")
            query = f"""
                SELECT * FROM account
            """
            account = sql.execute(query)[0]
            query = f"""
                SELECT * FROM pairs
            """
            pairs = ld2dd(sql.execute(query), key="name")
            query = f"""
                SELECT * FROM assets
            """
            assets = sql.execute(query)
            query = f"""
                SELECT * FROM nodes
            """
            nodes = sql.execute(query)
            query = f"""
                SELECT * FROM timing
            """
            timing = sql.execute(query)[0]
            # ==========================================================================
            i += 1
            i %= len(nodes)
            for _ in range(i):
                nodes.append(nodes.pop(0))
            pairs_i.append(pairs_i.pop(0))
            pair = pairs_i[0]
            # ==========================================================================
            static()
            print(it("purple", at((3, 6, 0, 0), LOGO)))
            # ==========================================================================
            # CALVIN S
            # ==========================================================================
            print(at((65, 28, 0, 0), convert(pair, "green")))
            print(at((140, 4, 0, 0), convert(chain[0]["name"].upper(), "blue")))
            print(at((65, 33, 0, 0), convert("ORDER BOOK", "purple")))
            print(at((65, 43, 0, 0), convert("USER STREAM", "purple")))
            # ==========================================================================
            # PAIRS
            # ==========================================================================
            print(at((42, 20, 0, 0), it("purple", constants.chain.PAIRS)))
            # ==========================================================================
            # CHAIN
            # ==========================================================================
            print(
                at(
                    (140, 2, 0, 0),
                    it("white", "ID:    ") + two_tone(chain[0]["id"], "blue", "purple"),
                )
            )
            print(
                at(
                    (140, 3, 0, 0),
                    it("white", "1.3.0: ") + two_tone(str(objects["1.3.0"]), "blue", "purple"),
                )
            )
            # ==========================================================================
            # BIDS; ASKS; HISTORY
            # ==========================================================================
            print(at((15, 37, 0, 0), it("yellow", "0 ") + it("white", "BIDS")))
            print(at((15, 38, 0, 0), it("grey", "[price, amount]".upper())))
            print(at((52, 37, 0, 0), it("yellow", "0 ") + it("white", "ASKS")))
            print(at((52, 38, 0, 0), it("grey", "[price, amount]".upper())))
            if pairs[pair]["book"]:
                print(
                    at(
                        (15, 37, 4, 1),
                        it("yellow", str(len(pairs[pair]["book"]["bids"]))) + it("white", " BIDS"),
                    )
                )
                for idx, item in enumerate(pairs[pair]["book"]["bids"][:3]):
                    print(at((15, 39 + idx, 0, 0), two_tone(str(item), "blue", "purple")))
                # ======================================================================
                print(
                    at(
                        (52, 37, 4, 1),
                        it("yellow", str(len(pairs[pair]["book"]["asks"]))) + it("white", " ASKS"),
                    )
                )
                for idx, item in enumerate(pairs[pair]["book"]["asks"][:3]):
                    print(at((52, 39 + idx, 0, 0), two_tone(str(item), "purple", "blue")))
            # ==========================================================================
            print(at((88, 37, 0, 0), it("white", "HISTORY")))
            print(at((88, 38, 0, 0), it("grey", "[unix, price, amount]".upper())))
            print(
                at(
                    (88, 37, 20, 1),
                    it("yellow", str(len(pairs[pair]["history"]))) + it("white", " HISTORY"),
                )
            )
            for idx, item in enumerate(pairs[pair]["history"][:3]):
                print(at((88, 39 + idx, 0, 0), two_tone(str(item), "green", "yellow")))
            print(at((122, 37, 0, 0), it("white", "LAST")))
            print(at((122, 38, 0, 0), two_tone(pairs[pair]["last"], "yellow", "green")))
            # ==========================================================================
            # CANCELS
            # ==========================================================================
            print(at((140, 48, 0, 0), two_tone("0 CANCEL OPERATIONS", "yellow", "white")))
            if len(loads(account["cancels"])) > 0:
                print(
                    at(
                        (140, 48, 23, 1),
                        it("yellow", str(len(loads(account["cancels"]))))
                        + it("white", " CANCEL OPERATIONS"),
                    )
                )
                print(
                    at(
                        (140, 49, 0, 0),
                        it(
                            "grey",
                            str(list(loads(account["cancels"])[0].keys())).replace("'", "").upper(),
                        ),
                    )
                )
                for idx, item in enumerate(loads(account["cancels"])[:3]):
                    print(
                        at(
                            (140, 50 + idx, 0, 0),
                            two_tone(str(list(item.values())), "purple", "blue"),
                        )
                    )
            # ==========================================================================
            # CREATES
            # ==========================================================================
            print(at((140, 55, 0, 0), two_tone("0 CREATE OPERATIONS", "yellow", "white")))
            if pairs[pair]["ops"] and pairs[pair]["ops"]["creates"]:
                print(
                    at(
                        (140, 55, 20, 1),
                        it("yellow", str(len(pairs[pair]["ops"]["creates"])))
                        + it("white", " CREATE OPERATIONS"),
                    )
                )
                print(
                    at(
                        (140, 56, 0, 0),
                        it(
                            "grey",
                            str(list(pairs[pair]["ops"]["creates"][0].keys()))
                            .replace("'", "")
                            .upper(),
                        ),
                    )
                )
                for idx, item in enumerate(pairs[pair]["ops"]["creates"][:3]):
                    if item["type"] == "BUY":
                        print(
                            at(
                                (140, 57 + idx, 0, 0),
                                two_tone(str(list(item.values())), "blue", "purple"),
                            )
                        )
                    else:
                        print(
                            at(
                                (140, 57 + idx, 0, 0),
                                two_tone(str(list(item.values())), "purple", "blue"),
                            )
                        )
            # ==========================================================================
            # OPEN ORDERS
            # ==========================================================================
            print(at((15, 48, 0, 0), it("yellow", "0") + it("white", " OPEN ORDERS")))
            if len(pairs[pair]["opens"]) > 0:
                print(
                    at(
                        (15, 48, 11, 1),
                        it("yellow", str(len(pairs[pair]["opens"]))) + it("white", " OPEN ORDERS"),
                    )
                )
                print(
                    at(
                        (15, 49, 0, 0),
                        it(
                            "grey",
                            str(list(pairs[pair]["opens"][0].keys())).replace("'", "").upper(),
                        ),
                    )
                )
                for idx, item in enumerate(pairs[pair]["opens"][:3]):
                    if item["type"] == "BUY":
                        print(
                            at(
                                (15, 50 + idx, 0, 0),
                                two_tone(str(list(item.values())), "blue", "purple"),
                            )
                        )
                    else:
                        print(
                            at(
                                (15, 50 + idx, 0, 0),
                                two_tone(str(list(item.values())), "purple", "blue"),
                            )
                        )
            # ==========================================================================
            # FILL ORDERS
            # ==========================================================================
            print(at((15, 55, 0, 0), it("yellow", "0") + it("white", " FILL ORDERS")))
            if len(pairs[pair]["fills"]) > 0:
                print(
                    at(
                        (15, 55, 11, 1),
                        it("yellow", str(len(pairs[pair]["fills"]))) + it("white", " FILL ORDERS"),
                    )
                )
                print(
                    at(
                        (15, 56, 0, 0),
                        it(
                            "grey",
                            str(list(pairs[pair]["fills"][0].keys())).replace("'", "").upper(),
                        ),
                    )
                )
                for idx, item in enumerate(pairs[pair]["fills"][:3]):
                    if item["type"] == "BUY":
                        print(
                            at(
                                (15, 57 + idx, 0, 0),
                                two_tone(str(list(item.values())), "blue", "purple"),
                            )
                        )
                    else:
                        print(
                            at(
                                (15, 57 + idx, 0, 0),
                                two_tone(str(list(item.values())), "purple", "blue"),
                            )
                        )
            # ==========================================================================
            # NODES
            # ==========================================================================
            print(
                at(
                    (142, 17, 0, 0),
                    it(
                        "grey",
                        str(["ping", "handshake", "url", "status"]).replace("'", "").upper(),
                    ),
                )
            )
            nodesp = [[i["ping"], i["handshake"], i["url"], i["status"]] for i in nodes[:10:]]
            connected = 0
            for iteration in nodes:
                if iteration["status"] == "CONNECTED":
                    connected += 1
            ratio = str(connected) + "/" + str(len(nodes))
            print(at((185, 17, 0, 0), two_tone(ratio, "yellow", "green")))
            for idx, node in enumerate(nodesp):
                if node[-1] == "CONNECTED":
                    print(
                        at(
                            (142, idx + 18, 0, 0),
                            two_tone(str(node), "green", "yellow"),
                        )
                    )
                elif node[-1] == "CONNECTION TIMEOUT":
                    print(at((142, idx + 18, 0, 0), two_tone(str(node), "purple", "blue")))
                else:
                    print(at((142, idx + 18, 0, 0), two_tone(str(node), "blue", "purple")))
            # ==========================================================================
            # BALANCES
            # ==========================================================================
            idx = 0
            print(at((10, 12, 0, 0), "BALANCES"))
            print(at((20, 12, 0, 0), it("grey", "['free', 'tied', 'total']".upper())))
            if assets[0]:
                justs = max(
                    len(str(i["name"])) + 2
                    for i in assets[:16:]
                    if ((i["name"] in pair.split("-")) or (str(i["id"]) in "1.3.0"))
                )

                for asset in assets[:16:]:
                    if asset["name"] in pair.split("-") or str(asset["id"]) in "1.3.0":
                        print(
                            at(
                                (10, 13 + idx, 0, 0),
                                it("white", (asset["name"] + ": ").ljust(justs))
                                + two_tone(
                                    str(list(asset["balance"].values())),
                                    "blue",
                                    "purple",
                                ),
                            )
                        )
                        idx += 1

            # ==========================================================================
            # TIMING
            # ==========================================================================
            print(
                at(
                    (80, 6, 0, 0),
                    it("white", "PING:        ") + two_tone(str(timing["ping"]), "yellow", "green"),
                )
            )
            print(
                at(
                    (80, 7, 0, 0),
                    it("white", "HANDSHAKE:   ")
                    + two_tone(str(timing["handshake"]), "yellow", "green"),
                )
            )
            print(
                at(
                    (80, 8, 0, 0),
                    it("white", "READ:        ") + two_tone(str(timing["read"]), "yellow", "green"),
                )
            )
            # ==========================================================================
            # ACCOUNT
            # ==========================================================================
            print(at((10, 2, 0, 0), it("white", "[NAME, ID]: ")))
            print(
                at(
                    (22, 2, 0, 0),
                    two_tone(str([account["name"], account["id"]]), "blue", "purple"),
                )
            )
            if account["fees_account"]:
                print(
                    at(
                        (10, 4, 0, 0),
                        it("white", "TX FEES:    ")
                        + two_tone(
                            str(
                                {
                                    "create": account["fees_account"]["create"],
                                    "cancel": account["fees_account"]["cancel"],
                                }
                            ),
                            "blue",
                            "purple",
                        ),
                    )
                )
            justs = max(len(str(i["name"])) + 2 for i in assets[:16:])
            idx = 0
            for _, asset in enumerate(assets[:16:]):
                if asset["name"] in pair.split("-") + [objects["1.3.0"]]:
                    idx += 1
                    print(
                        at(
                            (10, 5 + idx, 0, 0),
                            it("white", (asset["name"] + ": ").ljust(justs))
                            + two_tone(
                                str(list(asset["fees_asset"].values())),
                                "blue",
                                "purple",
                            ),
                        )
                    )

            animate(sql)
    except (KeyboardInterrupt, OperationalError):
        print(at((0, 69, 0, 0), ""))
    finally:
        print("\033[?25h")


if __name__ == "__main__":
    main()
