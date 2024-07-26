#!/usr/bin/env python
# DISABLE SELECT PYLINT TESTS
# pylint: disable=broad-except
# pylint: disable=bad-continuation, too-many-branches
# import pdb; pdb.set_trace()
r"""
 ╔════════════════════════════════════════════════════╗
 ║ ╔═╗╦═╗╔═╗╔═╗╦ ╦╔═╗╔╗╔╔═╗  ╔╦╗╔═╗╔╦╗╔═╗╔╗╔╔═╗╔╦╗╔═╗ ║
 ║ ║ ╦╠╦╝╠═╣╠═╝╠═╣║╣ ║║║║╣   ║║║║╣  ║ ╠═╣║║║║ ║ ║║║╣  ║
 ║ ╚═╝╩╚═╩ ╩╩  ╩ ╩╚═╝╝╚╝╚═╝  ╩ ╩╚═╝ ╩ ╩ ╩╝╚╝╚═╝═╩╝╚═╝ ║
 ╚════════════════════════════════════════════════════╝
~
CREATE THE METANODE SQL DATABASE AND PROVIDE A SAFE READ / WRITE WRAPPER
~
mavens are streaming windowed lists of json data
colleced directly from public api nodes user whitelist as "mostly trustworthy"
regenerative multiprcocessing prevents failed sockets from hanging main process
the statiscial mode of these lists is moved to the respective base table
note in some cases a REAL or INTEGER may be a TEXT as maven, eg.
maven.account.fees.cancel = "[0.2, 0.2, 0.2, 0.1]" ->
account.fees.cancel = 0.2
"""
# STANDARD MODULES
import json
import os
import time
from sqlite3 import OperationalError, Row, connect

# GRAPHENE MODULES
from .graphene_constants import GrapheneConstants
from .graphene_utils import it, jprint

# GLOBAL CONSTANTS
DEV = False
# self.constants.core.PATH = os.path.dirname(os.path.abspath(__file__)) + "/database"
CREATES = [
    """
    CREATE TABLE chain (
    name TEXT PRIMARY KEY,
    id TEXT UNIQUE
    )
    """,
    """
    CREATE TABLE account (
    name TEXT PRIMARY KEY,
    id TEXT UNIQUE,
    fees_account TEXT,
    ltm INT,
    cancels TEXT
    )
    """,
    """
    CREATE TABLE nodes (
    url TEXT PRIMARY KEY,
    ping REAL,
    handshake REAL,
    blocktime INT,
    code INT,
    status TEXT
    )
    """,
    """
    CREATE TABLE objects (
    id TEXT PRIMARY KEY,
    name TEXT,
    precision TEXT
    )
    """,
    """
    CREATE TABLE timing (
    name TEXT,
    blocknum INT,
    blocktime INT,
    server REAL,
    ping REAL,
    handshake REAL,
    read REAL,
    begin REAL
    )
    """,
    """
    CREATE TABLE assets (
    name TEXT PRIMARY KEY,
    id TEXT UNIQUE,
    precision INT,
    supply REAL,
    fees_asset TEXT,
    balance TEXT
    )
    """,
    """
    CREATE TABLE pairs (
    name TEXT PRIMARY KEY,
    id TEXT UNIQUE,
    invert_pair TEXT UNIQUE,
    invert_id TEXT UNIQUE,
    ops TEXT,
    last REAL,
    book TEXT,
    history TEXT,
    opens TEXT,
    fills TEXT
    )
    """,
    """
    CREATE TABLE maven_account (
    name TEXT PRIMARY KEY,
    fees_account TEXT,
    ltm TEXT,
    cancels TEXT
    )
    """,
    """
    CREATE TABLE maven_assets (
    name TEXT PRIMARY KEY,
    supply TEXT,
    fees_asset TEXT,
    balance TEXT
    )
    """,
    """
    CREATE TABLE maven_pairs (
    name TEXT PRIMARY KEY,
    ops TEXT,
    last TEXT,
    book TEXT,
    history TEXT,
    opens TEXT,
    fills TEXT
    )
    """,
    """
    CREATE TABLE maven_timing (
    name TEXT,
    blocknum TEXT,
    blocktime TEXT,
    read TEXT
    )
    """,
]
SELECTS = [
    """
    SELECT * FROM chain
    """,
    """
    SELECT * FROM nodes
    """,
    """
    SELECT * FROM objects
    """,
    """
    SELECT * FROM account
    """,
    """
    SELECT * FROM maven_account
    """,
    """
    SELECT * FROM timing
    """,
    """
    SELECT * FROM maven_timing
    """,
    """
    SELECT * FROM assets
    """,
    """
    SELECT * FROM maven_assets
    """,
    """
    SELECT * FROM pairs
    """,
    """
    SELECT * FROM maven_pairs
    """,
]
UPDATES = [
    (
        """
        UPDATE nodes SET ping=?, code=?, status=?
        """,
        ("999.9", "1000", "INITIALIZING"),
    ),
    (
        """
        UPDATE account SET fees_account=?, ltm=?, cancels=?
        """,
        ("{}", "0", "[]"),
    ),
    (
        """
        UPDATE assets SET precision=?, supply=?, fees_asset=?, balance=?
        """,
        ("0", "0.0", "{}", "{}"),
    ),
    (
        """
        UPDATE pairs SET last=?, book=?, history=?, opens=?, fills=?, ops=?
        """,
        ("0", "{}", "[]", "[]", "[]", "[]"),
    ),
    (
        """
        UPDATE maven_account SET fees_account=?, ltm=?, cancels=?
        """,
        ("[]", "[]", "[]"),
    ),
    (
        """
        UPDATE maven_assets SET supply=?, fees_asset=?, balance=?
        """,
        ("[]", "[]", "[]"),
    ),
    (
        """
        UPDATE maven_pairs SET last=?, book=?, history=?, opens=?, fills=?, ops=?
        """,
        ("[]", "[]", "[]", "[]", "[]", "[]"),
    ),
    (
        """
        UPDATE maven_timing SET blocknum=?, blocktime=?, read=?
        """,
        ("[]", "[]", "[]"),
    ),
]


class Sql:
    """
    creation of hummingbot graphene database and execution of queries
    """

    def __init__(self, constants):
        self.constants = constants

    def restart(self):
        """
        delete any existing db and initialize new SQL db
        """
        # create database folder
        os.makedirs(self.constants.core.PATH + "/database", exist_ok=True)
        # user input w/ warning
        # print("\033c")
        # print(it("red", "WARNING THIS SCRIPT WILL RESTART DATABASE AND ERASE ALL DATA\n"))
        # erase the database
        try:
            os.remove(self.constants.chain.DATABASE)
        except FileNotFoundError:
            pass
        # print("creating sqlite3:", it("green", self.constants.chain.DATABASE), "\n")
        print("creating sqlite3...")
        # initialize insert operations with chain specific configuration
        inserts = [
            (
                """
                INSERT INTO chain (name, id) VALUES (?,?)
                """,
                (
                    self.constants.chain.NAME,
                    self.constants.chain.ID,
                ),
            ),
            (
                """
                INSERT INTO timing
                (name, ping, handshake, blocktime, blocknum, read, begin)
                VALUES (?,?,?,?,?,?,?)
                """,
                (
                    self.constants.chain.ACCOUNT,
                    9999,
                    9999,
                    0,
                    0,
                    9999,
                    self.constants.metanode.BEGIN,
                ),
            ),
            (
                """
                INSERT INTO maven_timing (name, blocktime, blocknum, read)
                VALUES (?,?,?,?)
                """,
                (
                    self.constants.chain.ACCOUNT,
                    "[]",
                    "[]",
                    "[]",
                ),
            ),
            (
                """
                INSERT INTO account (name) VALUES (?)
                """,
                (self.constants.chain.ACCOUNT,),
            ),
            (
                """
                INSERT INTO objects (id, name) VALUES (?,?)
                """,
                (
                    "1.3.0",
                    self.constants.chain.CORE,
                ),
            ),
            (
                """
                INSERT INTO maven_account (name) VALUES (?)
                """,
                (self.constants.chain.ACCOUNT,),
            ),
        ]
        for asset in self.constants.chain.ASSETS:
            inserts.append(
                (
                    """
                    INSERT INTO assets (name) VALUES (?)
                    """,
                    (asset,),
                )
            )
            inserts.append(
                (
                    """
                    INSERT INTO maven_assets (name) VALUES (?)
                    """,
                    (asset,),
                )
            )
        for pair in self.constants.chain.ALL_PAIRS:
            inserts.append(
                (
                    """
                    INSERT INTO pairs (name) VALUES (?)
                    """,
                    (pair,),
                )
            )
            inserts.append(
                (
                    """
                    INSERT INTO maven_pairs (name) VALUES (?)
                    """,
                    (pair,),
                )
            )
        for node in self.constants.chain.NODES:
            inserts.append(
                (
                    """
                    INSERT INTO nodes (url) VALUES (?)
                    """,
                    (node,),
                )
            )
        # new table creation
        queries = []
        for query in CREATES:
            dml = {"query": query, "values": tuple()}
            queries.append(dml)
        self.execute(queries)
        # row creation in each table
        queries = []
        for insert in inserts:
            dml = {"query": insert[0], "values": insert[1]}
            queries.append(dml)
        self.execute(queries)
        # default column data in each row
        queries = []
        for update in UPDATES:
            dml = {"query": update[0], "values": update[1]}
            queries.append(dml)
        self.execute(queries)
        # print
        if DEV:
            for query in SELECTS:
                jprint(self.execute(query))
        # ~ raise ValueError("created database")

    def execute(self, query, values=()):
        """
        execute discrete sql queries, handle race condition gracefully
        if query is a string, assume values is a
        else, query can be a list of dicts with keys ["query","values"]
        While True:
            Try:
                con = connect(DB)
                cur = con.cursor()
                cur.execute(query, values)
                ret = cur.fetchall()
                con.commit()
                con.close()
                break
            Except:
                continue
        :return ret:
        """
        queries = []
        # handle both single query and multiple queries
        if isinstance(query, str):
            queries.append({"query": query, "values": values})
        else:
            queries = query
        # strip double spaces and new lines in each query
        for idx, dml in enumerate(queries):
            queries[idx]["query"] = " ".join(dml["query"].replace("\n", " ").split())
        # print sql except when...
        for dml in queries:
            if DEV:
                print(it("yellow", f"'query': {dml['query']}"))
                print(it("green", f"'values': {dml['values']}\n"))
        # attempt to update database until satisfied
        pause = -1
        curfetchall = None
        while True:
            try:
                pause += 1
                # only allow batched write queries
                if len(queries) > 1:
                    for dml in queries:
                        if "SELECT" in dml["query"]:
                            raise ValueError("batch queries must be write only")
                # ======================================================================
                # SQL CONNECT
                # ======================================================================
                con = connect(self.constants.chain.DATABASE)
                for dml in queries:
                    con.row_factory = Row
                    cur = con.cursor()
                    cur.execute(dml["query"], dml["values"])
                    curfetchall = cur.fetchall()
                con.commit()
                con.close()
                # ======================================================================
                # SQL CLOSE
                # ======================================================================
                data = [dict(i) for i in curfetchall]
                for idx, row in enumerate(data):
                    for key, val in row.items():
                        # these are sql REAL, but TEXT when maven_
                        if (
                            key
                            in [
                                "ltm",
                                "supply",
                                "last",
                            ]
                            and "maven_" in dml["query"]
                        ):
                            data[idx][key] = json.loads(val)
                        # these are valid json sql REAL
                        elif key in [
                            "fees_account",
                            "fees_asset",
                            "balance",
                            "book",
                            "history",
                            "ops",
                            "opens",
                            "fills",
                        ]:
                            data[idx][key] = json.loads(val)
                return data
            except OperationalError:
                if DEV:
                    print("Race condition at", int(time.time()))
                # ascending pause here prevents excess cpu on corruption of database
                # and allows for decreased load during race condition
                time.sleep(min(5, 1.01**pause - 1))
                continue


def unit_test():
    """
    initialize the database
    """
    print("\033c")
    constants = GrapheneConstants()
    dispatch = {str(idx): chain for idx, chain in enumerate(constants.core.CHAINS)}
    for key, value in dispatch.items():
        if "testnet" not in value:
            print(key + ": " + it("blue", value))
        else:
            print(key + ": " + it("purple", value))
    chain = dispatch[input("Enter choice: ")]
    constants = GrapheneConstants(chain)
    sql = Sql(constants)
    sql.restart()


if __name__ == "__main__":
    unit_test()
