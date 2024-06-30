##!/usr/bin/env python
# DISABLE SELECT PYLINT TESTS
# pylint: disable=bad-continuation, too-many-locals, broad-except, too-many-statements
# pylint: disable=too-many-arguments, too-many-branches, too-many-nested-blocks
# pylint: disable=too-many-lines
r"""
 ╔════════════════════════════════════════════════════╗
 ║ ╔═╗╦═╗╔═╗╔═╗╦ ╦╔═╗╔╗╔╔═╗  ╔╦╗╔═╗╔╦╗╔═╗╔╗╔╔═╗╔╦╗╔═╗ ║
 ║ ║ ╦╠╦╝╠═╣╠═╝╠═╣║╣ ║║║║╣   ║║║║╣  ║ ╠═╣║║║║ ║ ║║║╣  ║
 ║ ╚═╝╩╚═╩ ╩╩  ╩ ╩╚═╝╝╚╝╚═╝  ╩ ╩╚═╝ ╩ ╩ ╩╝╚╝╚═╝═╩╝╚═╝ ║
 ╚════════════════════════════════════════════════════╝
~
GRAPHENE BASE METANODE SERVER v2.0 SQL MULTI-PAIR
~
A TRUSTLESS SERVER PROVIDING STATISICAL MODE DATA
FROM A GRAPHENE BLOCKCHAIN'S PUBLIC API NODES
~
Because a personal node requires expertise and resources
a long term connection to any node operator is improbable
trusting a 3rd party blockchain API node can be risky
some public api connenctions are inherently faster than others
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
import json
import time
from multiprocessing import Process, Value
from random import choice, randint, shuffle
from sqlite3 import OperationalError, connect
from statistics import StatisticsError, median, mode, multimode
from threading import Thread

# GRAPHENE MODULES
from .graphene_constants import GrapheneConstants
from .graphene_metanode_client import GrapheneTrustlessClient
from .graphene_rpc import RemoteProcedureCall
from .graphene_sql import SELECTS, Sql
from .graphene_utils import blip, invert_pairs, it, jprint, precision, trace

DEV = False
DEV_PAUSE = False


def log_info(data):
    """log all dprints"""
    with open("log.txt", "a") as handle:
        handle.write(" ".join([str(i) for i in data]).replace("\\n", "\n") + "\n")
        handle.close()


def dprint(*data):
    """print for development"""
    if DEV:
        log_info(data)
        print(*data)


def dinput(data):
    """input for development"""
    out = None
    if DEV_PAUSE:
        out = input(data)
    return out


class GrapheneMetanode:
    """
    instantiated by GrapheneExchange for spawning the metanode data curation process
    """

    def __init__(self, constants: GrapheneConstants):
        self.initialized = False
        self.constants = constants
        self.metanode = GrapheneTrustlessClient(self.constants)
        self.constants.metanode.BEGIN = time.time()
        self.sql = Sql(constants)

    def jprint_db(self):
        """
        Pretty (fairly) print sql database
        """
        if DEV:
            for query in SELECTS:
                dprint(it("yellow", query))
                jprint(self.sql.execute(query))

    def deploy(self):
        """
        launch a metanode instance on a given blockchain
        which watches one account, several trading pairs, and all relevent balances
        use sls(); sorted(list(set())) idiom on user config
        during development pause at each stage
        """
        print("BOOTING METANODE")
        killswitch = Value("i", 0)
        signal_latency = Value("i", 0)
        signal_oracle = Value("i", 0)
        signal_maven = Value("i", 0)
        maven_free = [Value("i", 1) for _ in range(self.constants.metanode.MAVENS)]
        dinput("Press Enter to deploy database task")
        self.sql.restart()
        print(it("purple", "METANODE DATABASE INITIALIZED"))
        self.jprint_db()
        dinput("Press Enter to deploy latency task")
        self.jprint_db()
        latency_thread = Thread(target=self.latency_task, args=(signal_latency, killswitch))
        latency_thread.start()
        self.jprint_db()
        dinput("Press Enter to deploy cache task")
        self.cache_task()
        print(it("purple", "METANODE CACHE INITIALIZED"))
        while not bool(signal_latency.value):
            time.sleep(1)
            continue
        print(it("purple", "METANODE LATENCY INITIALIZED"))
        self.jprint_db()
        dinput("Press Enter to deploy maven_id task")
        maven_processes = {}
        for maven_id in range(self.constants.metanode.MAVENS):
            maven_processes[maven_id] = Process(
                target=self.maven_task,
                args=(signal_maven, maven_free[maven_id], maven_id),
                daemon=True,
            )
            maven_processes[maven_id].start()
        self.jprint_db()
        print(it("purple", "METANODE MAVEN INITIALIZED"))
        dinput("Press Enter to deploy oracle task")
        while not bool(signal_maven.value):
            blip(1)
            continue
        oracle_thread = Thread(target=self.oracle_task, args=(signal_oracle, killswitch))
        oracle_thread.start()
        while not bool(signal_oracle.value):
            blip(1)
            continue
        print(it("purple", "METANODE ORACLE INITIALIZED"))
        stars = it("cyan", "*" * 28)
        msg = it("green", "METANODE INITIALIZED")
        print(stars + "\n    " + msg + "\n" + stars)
        self.initialized = True
        # maven regeneration
        iteration = 0
        while self.running_flag():
            iteration += 1
            if iteration >= self.constants.metanode.REGENERATION_TUPLE:
                iteration = 0
                maven_id = randint(0, self.constants.metanode.MAVENS - 1)
                # ##########################################################################
                # SECURITY no maven_id task SQL access when dying
                maven_free[maven_id].value = 0
                time.sleep(1)
                maven_processes[maven_id].terminate()
                # ##########################################################################
                maven_processes[maven_id] = Process(
                    target=self.maven_task,
                    args=(signal_maven, maven_free[maven_id], maven_id),
                    daemon=True
                )
                maven_processes[maven_id].start()
                maven_free[maven_id].value = 1
            time.sleep(1)
        killswitch.value = 1
        for maven in maven_processes.values():
            maven.terminate()

    def running_flag(self):
        try:
            with open(self.constants.DATABASE_FOLDER + "metanode_flags.json", "r") as handle:
                flag = json.loads(handle.read()).get(self.constants.chain.NAME, True)
                handle.close()
        except:
            flag = True
        return flag

    def latency_task(self, signal_latency, killswitch):
        """
        classify the response status of each node in the user configuration
        the aim here to determine if this is a legit public api endpoint
        ~
        launch timed subprocesses to test each node in validated list
        update the metanode with the latest connectivity data from the network
        ~
        # threshers are Process to strictly enforce TIMEOUT
        # Value is a multiprocessing communication channel
        # we'll keep track of our values on this side in a status codes dict()
        # the threshing processes will run concurrently on all nodes
        # repeat this process once per minute
        """

        def thresh(node, code, ping, handshake, blocktime):
            """
            ping the blockchain and return a response code to classify the interaction
            """
            try:
                print(it("green", "latency"), it("blue", node))
                # connect to websocket and capture handshake latency
                start = time.time()
                # ======================================================================
                # WSS START
                # ======================================================================
                rpc = RemoteProcedureCall(self.constants, [node])
                handshake.value = time.time() - start
                # get chain id and capture ping latency
                start = time.time()
                chain = rpc.chain_id()
                ping.value = time.time() - start
                # get blocktime and participation rate (check if stale / forked)
                blocktime.value, participation = rpc.blocktime_participation()
                if len(self.constants.chain.NODES) == 1 or (
                    "testnet" in self.constants.chain.NAME
                ):  # skip participation tests on testnets or a single node in config
                    participation = 100
                # calculate block latency
                block_latency = time.time() - blocktime.value
                try:
                    # check if this node supports history
                    rpc.market_history(self.constants.chain.PAIRS, depth=2)[0]  # sample_pair?
                except Exception:
                    code.value = 1001  # "NO HISTORY"
                try:
                    # we're done testing this node for now... disconnect
                    rpc.close()
                    # ==================================================================
                    # WSS STOP
                    # ==================================================================
                except Exception:
                    pass
                if chain != self.constants.chain.ID:
                    code.value = 1002  # "WRONG CHAIN ID"
                elif participation < 90:  # @xeroc: anything above 67% is "fine"
                    code.value = 1003  # "FORKED FROM MAINNET"
                elif block_latency > (ping.value + 10):
                    code.value = 1004  # "STALE BLOCKTIME",
                elif handshake.value > 10:
                    code.value = 1005  # "SLOW HANDSHAKE"
                elif ping.value > self.constants.metanode.MAX_PING:
                    code.value = 1006  # "SLOW PING"
                else:
                    code.value = 200  # "CONNECTED"
            except Exception as error:
                code.value = 1007  # "CONNECTION FAILED"
                dprint(str(node) + " " + str(type(error).__name__) + " " + str(error.args))
                dprint(trace(error))

        nodes_to_test = list(self.constants.chain.NODES)
        # begin the latency task loop:
        while not killswitch.value:
            # initially test all nodes at once...
            # then test each node with a pause in between thereafter
            if signal_latency.value:
                nodes_to_test = [
                    choice(self.constants.chain.NODES),
                ]
            # print(it("green", nodes_to_test))
            nodes = {}
            codes = {}
            handshakes = {}
            pings = {}
            blocktimes = {}
            thresher = {}
            try:
                for node in nodes_to_test:
                    blip(0.5)
                    codes[node] = Value("i", 1008)  # "CONNECTION TIMEOUT"
                    pings[node] = Value("d", 0)
                    handshakes[node] = Value("d", 0)  # "CONNECTION TIMEOUT"
                    blocktimes[node] = Value("i", 0)  # unix blocktime
                    # contacting the "unknown status" endpoint is Process wrapped
                    thresher[node] = Process(
                        target=thresh,
                        args=(
                            node,
                            codes[node],
                            pings[node],
                            handshakes[node],
                            blocktimes[node],
                        ),
                        daemon=True,
                    )
                    # begin all the threshers at once
                    thresher[node].start()
                time.sleep(self.constants.metanode.LATENCY_THRESHER_TIMEOUT)
                for node in nodes_to_test:
                    try:
                        thresher[node].terminate()
                    except Exception as error:
                        dprint(trace(error))
                    status = self.constants.metanode.STATUS_CODES[codes[node].value]
                    if status != "CONNECTED":
                        pings[node].value = 9999
                        handshakes[node].value = 9999
                    nodes[node] = {
                        "ping": float(precision(pings[node].value, 4)),
                        "handshake": float(precision(handshakes[node].value, 4)),
                        "code": int(codes[node].value),
                        "status": status,
                        "blocktime": int(blocktimes[node].value),
                    }
                for node, values in nodes.items():
                    dprint(node, values)
                node_updates = []
                for node, state in nodes.items():
                    node_updates.append(
                        {
                            "query": """UPDATE nodes
                            SET ping=?, handshake=?, code=?, status=?, blocktime=?
                            WHERE url=?
                            """,
                            "values": (
                                state["ping"],
                                state["handshake"],
                                state["code"],
                                state["status"],
                                state["blocktime"],
                                node,
                            ),
                        }
                    )
                # ======================================================================
                self.sql.execute(node_updates)  # DISCRETE SQL QUERY
                # ======================================================================
            except Exception as error:
                dprint(trace(error))
            # return an iteration signal to the parent process
            signal_latency.value += 1
            if signal_latency.value > 1:
                # do not pause if there are no status 200 nodes
                # ======================================================================
                if self.metanode.whitelist:  # DISCRETE SQL QUERY
                    # ==================================================================
                    # latency pause is per node
                    # pause but quit if the killswitch is thrown
                    start = time.time()
                    while time.time()-start < self.constants.metanode.LATENCY_TASK_PAUSE / len(self.constants.chain.NODES) and not killswitch.value:
                        time.sleep(1)

    def cache_task(self):
        """
        Acquire and store account id; asset ids, and asset precisions
        This is called once at startup, prior to spawning additional processes
        """

        def harvest(samples, node):
            """
            make external calls and add responses to the "samples" dict by key "node"
            """
            rpc = RemoteProcedureCall(self.constants, [node])
            cache = {}
            acct_by_name = rpc.account_by_name()
            if isinstance(acct_by_name, dict) and "id" in acct_by_name:
                cache["account_id"] = acct_by_name["id"]
            else:
                dprint(node, "is a bad node, returned", acct_by_name)
                rpc.close()
                return
            cache["assets"] = rpc.lookup_asset_symbols()
            rpc.close()
            samples[node] = json.dumps(cache)
            print(it("yellow", f"cache {len(samples)}"))

        def thresh(cache_signal):
            """
            continue querying until we have agreement
            then update db cache objects *once* at launch
            """
            all_pairs = self.constants.chain.ALL_PAIRS
            nodes = self.constants.chain.NODES
            assets = self.constants.chain.ASSETS
            samples = {}
            threads = {}
            # spawn the harvest threads
            for idx, node in enumerate(nodes):
                threads[node] = Thread(target=harvest, args=(samples, node))
                threads[node].start()
                dprint(f"Thread #{idx}/{len(nodes)} started at {node}")
            # split the timeout between thread joins
            timeout = self.constants.metanode.MAVEN_CACHE_HARVEST_JOIN
            start = time.time()
            for idx, node in enumerate(nodes):
                threads[node].join(timeout)
                elapsed = time.time()-start
                start = time.time()
                timeout -= elapsed
                if timeout <= 0:
                    break

            whitelisted = len(self.metanode.whitelist)

            data = {}

            # return the wheat when there is a mode
            for idx, node in enumerate(nodes):
                try:
                    if len(nodes) == 1:
                        data = json.loads(samples[node])
                        break
                    if idx >= min(
                        len(self.constants.chain.NODES) - 1,
                        self.constants.metanode.MAVENS,
                        whitelisted-1,
                        5,
                    ):
                        data = json.loads(
                            multimode(list(samples.values()))[0]
                        )  # FIXME maybe this works with one?
                        break
                except Exception as error:
                    dprint(trace(error))
            queries = []
            # add the 1.2.X account id
            queries.append(
                {
                    "query": "UPDATE account SET id=?",
                    "values": (data["account_id"],),
                }
            )
            for asset in assets:
                # add each 1.3.X asset id
                asset_id = data["assets"][asset]["id"]
                queries.append(
                    {
                        "query": """
                        UPDATE assets SET id=?, precision=?, fees_asset=? WHERE name=?
                        """,
                        "values": (
                            asset_id,
                            data["assets"][asset]["precision"],
                            json.dumps(data["assets"][asset]["fees"]),
                            asset,
                        ),
                    }
                )
                # core was inserted at db initialization
                if asset_id != "1.3.0":
                    queries.append(
                        # create rows in the objects table
                        {
                            "query": "INSERT INTO objects (id, name) VALUES (?,?)",
                            "values": (asset_id, asset),
                        }
                    )
                # Add precesions to objects table for easy lookup
                queries.append(
                    {
                        "query": """
                        UPDATE objects SET precision=? WHERE id=?
                        """,
                        "values": (
                            data["assets"][asset]["precision"],
                            asset_id,
                        ),
                    }
                )
            for pair in all_pairs:
                # add 1.3.X-1.3.X pair id
                base_id = data["assets"][pair.split("-")[0]]["id"]
                quote_id = data["assets"][pair.split("-")[1]]["id"]
                pair_id = f"{base_id}-{quote_id}"
                invert_pair_id = f"{quote_id}-{base_id}"
                invert_pair = invert_pairs([pair])[0]
                queries.append(
                    {
                        "query": """
                        UPDATE pairs SET
                        id=?, invert_id=?, invert_pair=? WHERE name=?
                        """,
                        "values": (pair_id, invert_pair_id, invert_pair, pair),
                    }
                )
                # create rows in the objects table for pair and invert pair object
                queries.append(
                    {
                        "query": "INSERT INTO objects (id, name) VALUES (?,?)",
                        "values": (pair_id, pair),
                    }
                )
            # ==========================================================================
            self.sql.execute(queries)  # DISCRETE SQL QUERY
            # ==========================================================================
            cache_signal.value += 1  # success of thresh()

        # each attempt is process wrapped and disposable
        # success or failure it has a lifespan and a successor
        # multiprocessing value turns to 1 upon success of thresh()
        cache_signal = Value("i", 0)
        while True:
            process = Process(target=thresh, args=(cache_signal,), daemon=True)
            process.start()
            process.join(self.constants.metanode.CACHE_RESTART_JOIN)
            process.terminate()
            if bool(cache_signal.value):
                break
            else:
                dprint("CACHE TASK RESTARTING")

    def maven_task(self, signal_maven, maven_free, maven_id):
        """
        gather streaming data and place it in a list to be statistically analyized
        """

        def maven_update(
            self,
            sooth,  # some value gathered from some tracker for some row
            tracker,  # eg last, balances, book, fills, ops
            row,  # database table primary key
            maven_id,
            maven_free,
        ):
            """
            execute atomic sql read/edit/write to update the maven feed
            """
            # ~ print(
            # ~ it("purple", "maven"),
            # ~ tracker,
            # ~ row,
            # ~ )
            if tracker == "fills" and not sooth:
                return
            # FIXME maven_id never gets used... its available for future dev
            # ==========================================================================
            # SECURITY - SQL INJECTION RISK at {tracker} and {table}
            # hardcoded dict prevents injection at fstring
            # ==========================================================================
            table = self.constants.metanode.TRACKER_TABLE[tracker]
            # ==========================================================================
            # eg. SELECT last FROM maven_pairs WHERE name=BTC-USD
            read_query = f"""SELECT {tracker} FROM maven_{table} WHERE name=?"""
            read_values = (row,)
            # eg. UPDATE pairs SET last=sooth WHERE name=BTC-USD
            write_query = f"""UPDATE maven_{table} SET {tracker}=? WHERE name=?"""
            # write_values are atomic
            # maven_free.value is locked by parent process prior to Process termination
            # this prevents a maven Process from hard kill while db is accessed
            if maven_free.value:
                # ======================================================================
                # SQL CONNECT ** minimize access time **
                # ======================================================================
                if tracker in ["blocknum", "blocktime"]:
                    con = connect(self.constants.chain.DATABASE)
                    cur = con.cursor()
                    cur.execute(read_query, read_values)
                    while True:
                        try:
                            cur.execute(
                                write_query,
                                (
                                    (
                                        json.dumps(
                                            (json.loads(cur.fetchall()[0][0]) + [sooth])[-mavens:]
                                        )
                                    ),
                                    row,
                                ),
                            )
                            break
                        except OperationalError:
                            dprint("Race condition at", int(time.time()))
                        except Exception as error:  # JSONDecodeError ?
                            dprint(
                                "maven error...",
                                error.args,
                                trace(error),
                                table,
                                tracker,
                                row,
                                sooth,
                                maven_id,
                                maven_free.value,
                            )
                else:
                    while True:
                        try:
                            con = connect(self.constants.chain.DATABASE)
                            cur = con.cursor()
                            cur.execute(read_query, read_values)
                            break
                        except OperationalError:
                            dprint("Race condition at", int(time.time()))
                    while True:
                        try:
                            cur.execute(
                                write_query,
                                (
                                    (
                                        json.dumps(
                                            (json.loads(cur.fetchall()[0][0]) + [sooth])[-mavens:]
                                        )
                                    ),
                                    row,
                                ),
                            )
                            break
                        except OperationalError:
                            dprint("Race condition at", int(time.time()))
                        except Exception as error:  # JSONDecodeError ?
                            dprint(
                                "maven error...",
                                error.args,
                                trace(error),
                                table,
                                tracker,
                                row,
                                sooth,
                                maven_id,
                                maven_free.value,
                            )
                while True:
                    try:
                        con.commit()
                        break
                    except Exception:
                        pass
                con.close()
                # ======================================================================
                # SQL CLOSE
                # ======================================================================

        nodes = list(self.metanode.whitelist)
        shuffle(nodes)
        rpc = RemoteProcedureCall(self.constants, nodes)
        trackers = {
            "ltm": rpc.is_ltm,
            "fees_account": rpc.fees_account,
            "fees_asset": rpc.lookup_asset_symbols,
            "supply": rpc.current_supply,
            "balance": rpc.account_balances,
            "history": rpc.market_history,
            "book": rpc.book,
            "last": rpc.last,
            "ops": rpc.operations,
            "opens": rpc.open_orders,
            "fills": rpc.fill_order_history,
            "blocknum": rpc.block_number,
            "blocktime": rpc.blocktime,
        }
        # localize constants
        pairs = self.constants.chain.PAIRS
        assets = self.constants.chain.ASSETS
        account = self.constants.chain.ACCOUNT
        pause = self.constants.metanode.MAVEN_PAUSE
        core_pairs = self.constants.chain.CORE_PAIRS
        mavens = self.constants.metanode.MAVEN_WINDOW
        rpc_ratio = self.constants.metanode.MAVEN_RPC_RATIO
        high_low_ratio = self.constants.metanode.MAVEN_HIGH_LOW_RATIO
        while True:
            start = time.time()
            _ = self.metanode.pairs
            read_elapsed = time.time() - start
            blip(pause)
            maven_update(
                self,
                read_elapsed,
                "read",
                account,
                maven_id,
                maven_free,
            )
            # create a fresh websocket every so many iterations
            if int(signal_maven.value) % rpc_ratio == 0:
                rpc = rpc.reconnect()  # WSS HANDSHAKE
            #  low frequency
            if int(signal_maven.value) % high_low_ratio == 0:
                # account calls
                for tracker in ["fees_account", "ltm"]:
                    blip(pause)
                    sooth = trackers[tracker]()  # WSS RPC
                    maven_update(
                        self,
                        sooth,
                        tracker,
                        account,
                        maven_id,
                        maven_free,
                    )
                #  asset calls
                for asset in assets:
                    for tracker in ["supply", "fees_asset"]:
                        blip(pause)
                        sooth = trackers[tracker]()  # WSS RPC
                        maven_update(self, sooth[asset], tracker, asset, maven_id, maven_free)
            # high frequency
            else:
                # pair calls for account buy/sell/cancel operations and open orders
                # NOTE the creation of sooth IS NOT pair specific; is keyed by pair
                for tracker in ["ops", "opens"]:
                    blip(pause)
                    sooth = trackers[tracker]()
                    # NOTE cancel operations carry no pair data; move to account table
                    if tracker == "ops":
                        maven_update(
                            self,
                            sooth["cancels"],
                            "cancels",
                            account,
                            maven_id,
                            maven_free,
                        )
                    for pair in pairs:
                        maven_update(self, sooth[pair], tracker, pair, maven_id, maven_free)
                #  pair calls for last, order book, fill orders, and market history
                #  NOTE the creation if each sooth from RPC is pair specific
                for tracker in ["last", "book", "fills", "history"]:
                    for pair in pairs:
                        try:
                            blip(pause)
                            sooth = trackers[tracker](pair)  # WSS RPC
                            maven_update(self, sooth, tracker, pair, maven_id, maven_free)
                        except Exception as error:
                            dprint(trace(error))
                        # add the invert last price for every trading pair
                        if tracker == "last":
                            try:
                                blip(pause)
                                sooth = trackers[tracker](pair)  # WSS RPC
                                maven_update(
                                    self,
                                    1 / sooth,
                                    "last",
                                    invert_pairs([pair])[0],
                                    maven_id,
                                    maven_free,
                                )
                            except Exception as error:
                                dprint(trace(error))
                # add exchange rates back to core token for every asset
                for pair in core_pairs:
                    try:
                        blip(pause)
                        sooth = trackers["last"](pair)  # WSS RPC
                        maven_update(self, sooth, "last", pair, maven_id, maven_free)
                    except Exception as error:
                        dprint(trace(error))
                    # add the invert last price for every core trading pair
                    try:
                        blip(pause)
                        sooth = trackers["last"](pair)  # WSS RPC
                        maven_update(
                            self,
                            1 / sooth,
                            "last",
                            invert_pairs([pair])[0],
                            maven_id,
                            maven_free,
                        )
                    except Exception as error:
                        dprint(trace(error))
                #  balances calls, NOTE one RPC and get a sooth keyed by asset
                blip(pause)
                sooth = trackers["balance"]()  # WSS RPC
                for asset in self.constants.chain.ASSETS:
                    maven_update(self, sooth[asset], "balance", asset, maven_id, maven_free)
                # blocktime and blocknum calls in maven timing table
                for tracker in ["blocktime", "blocknum"]:
                    blip(pause)
                    sooth = trackers[tracker]()  # WSS RPC
                    # ~ print("maven " + tracker + ": " + it("red", str(sooth).upper()))
                    maven_update(
                        self,
                        sooth,
                        tracker,
                        account,
                        maven_id,
                        maven_free,
                    )
            # return an iteration signal to the parent process
            signal_maven.value += 1
            blip(pause)

    def oracle_task(self, signal_oracle, killswitch):
        """
        read maven tracker data from the database
        write statistical mode of the maven as the oracle back to database, eg.
        ~
        pair["tracker"] = mode(maven_pairs["tracker"])
        """

        def oracle_update(
            self,
            tracker,
            row,
        ):
            """
            execute atomic sql read/edit/write to update the oracle feed
            read table / row of maven_xyz, write statistical mode to xyz table / row
            """
            # ~ print(it("red", "oracle"), tracker, row)
            # ==========================================================================
            # SECURITY SQL hardcoded dict prevents injection at fstring
            # ==========================================================================
            table = self.constants.metanode.TRACKER_TABLE[tracker]
            # ==========================================================================
            # SQL CONNECT  ** minimize access time **
            # ==========================================================================
            con = connect(self.constants.chain.DATABASE)
            cur = con.cursor()
            # some timing tables require special consideration
            if table == "timing" and tracker not in ["blocktime", "blocknum"]:
                # update server time to current time.time()
                if tracker == "server":
                    while True:
                        try:
                            update_query = f"UPDATE timing SET server=?"
                            update_values = (time.time(),)
                            cur.execute(update_query, update_values)
                            break
                        except OperationalError:
                            dprint("Race condition at", int(time.time()))
                        except Exception as error:
                            dprint(trace(error))
                # timing trackers which require median statistic
                elif tracker == "read":
                    while True:
                        try:
                            select_query = f"""SELECT read FROM maven_timing"""
                            select_values = tuple()
                            update_query = f"""UPDATE timing SET read=?"""
                            # update_values are atomic
                            cur.execute(select_query, select_values)
                            curfetchall = json.loads([i[0] for i in cur.fetchall()][0])
                            cur.execute(
                                update_query,
                                ((float(precision(median(curfetchall), 6))),),
                            )
                            break
                        except OperationalError:
                            dprint("Race condition at", int(time.time()))
                        except Exception as error:
                            dprint(trace(error))
                # timing trackers which require median statistic
                elif tracker in ["handshake", "ping"]:
                    while True:
                        try:
                            select_query = f"""SELECT {tracker} FROM nodes WHERE code=200"""
                            select_values = tuple()
                            update_query = f"""UPDATE timing SET {tracker}=?"""
                            # update_values are atomic
                            cur.execute(select_query, select_values)
                            curfetchall = [i[0] for i in cur.fetchall()]
                            cur.execute(
                                update_query,
                                ((float(precision(median(curfetchall), 4))),),
                            )
                            break
                        except OperationalError:
                            dprint("Race condition at", int(time.time()))
                        except Exception as error:
                            dprint(trace(error))
            elif tracker == "cancels":
                while True:
                    try:
                        # the normal way of handling most tracker updates at oracle level
                        select_query = f"""SELECT {tracker} FROM maven_{table} WHERE name=?"""
                        select_values = (row,)
                        update_query = f"""UPDATE {table} SET {tracker}=? WHERE name=?"""
                        cur.execute(select_query, select_values)
                        # ~ if tracker == "fills":
                        # ~ print(cur.fetchall())
                        break
                    except OperationalError:
                        dprint("Race condition at", int(time.time()))
                # update_values are atomic
                while True:
                    try:
                        cur.execute(
                            update_query,
                            (
                                json.dumps(
                                    json.loads(
                                        mode(
                                            [
                                                json.dumps(i)
                                                for i in json.loads(cur.fetchall()[0][0])
                                            ]
                                        )
                                    )
                                ),
                                row,
                            ),
                        )
                        break
                    except OperationalError:
                        dprint("Race Error", int(time.time()), tracker, table, row)
                    except StatisticsError:
                        dprint("Statistics Error", tracker, table, row)
                        break
                    except IndexError:
                        dprint("Index Error", tracker, table, row)
                        break
                    except Exception as error:
                        dprint(trace(error), tracker, table, row)
                        break
            else:
                while True:
                    try:
                        # the normal way of handling most tracker updates at oracle level
                        select_query = f"""SELECT {tracker} FROM maven_{table} WHERE name=?"""
                        select_values = (row,)
                        update_query = f"""UPDATE {table} SET {tracker}=? WHERE name=?"""
                        cur.execute(select_query, select_values)
                        # ~ if tracker == "fills":
                        # ~ print(cur.fetchall())
                        break
                    except OperationalError:
                        dprint("Race condition at", int(time.time()))
                # update_values are atomic
                while True:
                    try:
                        cur.execute(
                            update_query,
                            (
                                json.dumps(
                                    json.loads(
                                        mode(
                                            [
                                                json.dumps(i)
                                                for i in json.loads(cur.fetchall()[0][0])
                                            ]
                                        )
                                    )
                                ),
                                row,
                            ),
                        )
                        break
                    except OperationalError:
                        dprint("Race Error", int(time.time()), tracker, table, row)
                    except StatisticsError:
                        dprint("Statistics Error", tracker, table, row)
                        break
                    except IndexError:
                        dprint("Index Error", tracker, table, row)
                        break
                    except Exception as error:
                        dprint(trace(error), tracker, table, row)
                        break
            while True:
                try:
                    con.commit()
                    break
                except Exception:
                    pass
            con.close()
            # ==========================================================================
            # SQL CLOSE
            # ==========================================================================

        # localize constants
        all_pairs = self.constants.chain.ALL_PAIRS
        pause = self.constants.metanode.ORACLE_PAUSE
        account = self.constants.chain.ACCOUNT
        assets = self.constants.chain.ASSETS
        pairs = self.constants.chain.PAIRS
        while not killswitch.value:
            # low frequency
            if int(signal_oracle.value) % 20 == 0:
                # account writes
                trackers = ["fees_account", "ltm"]
                for tracker in trackers:
                    blip(pause)
                    oracle_update(self, tracker, account)
                # asset writes
                for asset in assets:
                    trackers = ["supply", "fees_asset"]
                    for tracker in trackers:
                        blip(pause)
                        oracle_update(self, tracker, asset)
                # timing writes
                for tracker in ["ping", "handshake"]:
                    blip(pause)
                    oracle_update(self, tracker, account)
            # high frequency
            else:
                # updates to timing; these have no row key
                trackers = ["server", "blocknum", "blocktime", "read"]
                for tracker in trackers:
                    blip(pause)
                    oracle_update(self, tracker, account)
                # update account cancel operations; these are not split by pair
                blip(pause)
                oracle_update(self, "cancels", account)
                # updates to each row in pair table
                trackers = ["last", "book", "history", "fills", "opens", "ops"]
                for pair in pairs:
                    for tracker in trackers:
                        blip(pause)
                        oracle_update(self, tracker, pair)
                # provide a last price for every asset back to core token
                for pair in all_pairs:
                    blip(pause)
                    oracle_update(self, "last", pair)
                # updates to each row in asset table
                trackers = ["balance"]
                for asset in assets:
                    for tracker in trackers:
                        blip(pause)
                        oracle_update(self, tracker, asset)
            # return an iteration signal to the parent process
            signal_oracle.value += 1


def unit_test():
    """
    Primary event backbone
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
    metanode_instance = GrapheneMetanode(constants)
    metanode_instance.deploy()


if __name__ == "__main__":
    unit_test()
