# Installation


```bash
pip3 install virtualenv
virtualenv <name of env>
. <name of env>/bin/activate
pip3 install websocket-client requests secp256k1 ecdsa
git clone https://github.com/litepresence/Graphene-Metanode.git
cd Graphene-Metanode
python3 graphene_metanode_server.py
```

# Abstract

Graphene Metanode is a locally hosted node for one account and several trading pairs,
which uses minimal RAM resources.  It provides the necessary user stream data
and order book data for trading in a format one would expect from a centralized exchange API.

# Motivation

This project is phase one of a Hummingbot.io "connector"
for Peerplays and other Graphene based Decentralized Exchanges

Metanode presents an locally hosted API layer between the trader and Graphene
optimized to support multiple chains and currency pairs concurrently

 - A personal node requires expertise and resources
 - a long term connection to any node operator is improbable
 - trusting a 3rd party blochchain api node can be risky
 - some public api connenctions are faster than others
 - querying a graphene chain directly is not user friendly

# Rationale

The aim of metanode is to present stable API utilizing a minimalist sqlite database.
It provides data for one account and multiple trading pairs formatted as you'd expect from centralized exchange.
All data provided is statitisticly validated among all user provided nodes in the network
The result is a user friendly api for decentralized exchange order book and user stream
with collection procedures offering 99.9999% uptime.

# Specifications

Metanode was built on an FM3+ AMD 7700K machine w/ 16GB ram, 256GB SSD
but may support 3 markets on a raspberry pi 4

it has been built in anticipation of launch of the SONS and DEX on Peerplays mainnet.

The initital pairs there are:

BTC:PPY
HIVE:PPY
HBG:PPY

It has also been tested extensively on Bitshares mainnet.   The framework should be compatible
with other graphene chains with minor revisions.


### graphene_metanode_server.py

Metanode server is based on sqlite, standard python library.

It is an API layer between Graphene chains and Hummingbot.   Hummingbot is an independent open source python algorithmic trading platform, learn more at www.hummingbot.io

Metanode is the process of collecting data from the public api network and curating in a statistically sound manner to produce reliable data feeds from an otherwise unreliable network.

To make this possible, Mavens are streaming windowed lists of json data.   This data has been collected directly from public api nodes that the user whitelists as "mostly trustworthy".  Over time, each node in the list the user has provided might become disconnected, stale, or otherwise currupted.   Metanode ensure the data feed remains reliable client side.   Concurrently, multiple python processes are regeneratively spawned to deal with the outside world. They collect data, put it into the maven feed, and ensure the length of the feed remains windowed to provide a brief glimpse into the past.

In a seperate process an oracle reads the windowed lists provided by the maven processes and its sorts through this data using traditional statistic methods; predominately "mode".  What we learn is "what most reliable nodes are reporting".   The oralce; the the statiscial mode is moved to the respective base table in the database.  A REAL or INTEGER in the oracle tables may be a json TEXT as maven, eg.

    maven.account.fees.cancel = "[0.2, 0.2, 0.2, 0.1]" ->
    account.fees.cancel = 0.2

The metanode server can be launched:

`python3 graphene_metanode_server.py`

graphene_metanode_server.py is the principle product of this package but other sub modules can be used in a stand alone manner.

### unit tests

dbux (data base user experience) is a visualization tool used to ensure everything is configured correctly with the metanode server.

with graphene_metanode_server.py running, open two additional terminal tabs and run:


`python3 unit_test_dbux.py`

`python3 unit_test_public.py`


### graphene_client.py

To instantiate the metanode, execute

`metanode = GrapheneTrustlessClient(constants: GrapheneConstants)`

From there the following methods are provided:
 - `metanode.pairs`
 -- Returns a dict of dicts of pairs keyed by `BASE-QUOTE` trading pair with subdicts:
    `ops,  last, book, history , opens, fills`
    care has been taken with this data to ensure its in an easy to use format
    as well as some metadata
    `name,  id,  invert_pair, invert_id`

 - `metanode.whitelist`
 -- Returns a dynamic list of node urls; tested and sorted by latency.
 - `metanode.account`
 -- Returns pertinent account data for trading; transaciton fees, whether the user is lifetime member, and order cancels performed by the account (these are not sorted by pair)
    `name, id, fees_account, ltm, cancels`
 - `metanode.timing`
 -- Returns a list of dicts of timing items:
    `ping, read, begin, blocktime, blocknum, and handshake`
 - `metanode.assets`
 -- Returns a dict of dicts keyed by asset name.
    `name, id, precision, supply, fees_asset, balance`
    critically, the asset precisison is cached here which allows for graphene integer based math to occur in the background.  The user's account balances per asset are also here, in total, tied, and free terms.

 - `metanode.chain`
 -- returns dict with keys id and name; the chain id is the grahene identifier for the blockchain
 - `metanode.nodes`
 -- Returns a dict of dicts of nodes keyed by websocket url
    this list is used to provide connectivity information in for each note provided by the user

- `metanode.objects`
 -- Returns a dict of dicts keyed by asset id
    objects provides cached reference between graphenes' a.b.c object id's and their respective object name

every metanode.xyz method is a SQL database query and should be cached
at time of use to dict(metanode_xyz) to avoid excess database lookups
the format of each response is described in the docstrings below
all of the data returned is as as a list or dict python object
loaded from json and containing str/float/int values
these responses are statistically clean "mode" or "median" as appropritate
from all responding nodes the user has provided upon configuration

### graphene_contants.py

GrapheneConstants is a class that can be instantiated with or without a chain specified.
Without, it gives access to all constants that are not chain specific, eg.
```python
from graphene_constants import GrapheneConstants
constants = GrapheneConstants()
print(constants.metanode.MAVENS)
print(constants.core.BASE58)
print(constants.signing.KILL_OR_FILL)
```
The above constants should be adjusted with caution.   Some of the metanode constants involve a balancing act between your system resources and your latency.  Effort has been made to provide sensible, system safe metanode constants.

The user only needs to ajust chain specific constants;

`PAIRS, NODES, ACCOUNT`

These are to be edited in file and saved. Default values are provided for simulation and testing.

When specifying the chain you gain access to the chain specific constants, eg.
```python
constants = GrapheneConstants("peerplays")
print(constants.chain.NODES, constants.chain.PAIRS, constants.chain.ACCOUNT)
```
### graphene_rpc.py

These are public api calls to nodes in the network.
The responses are normalized to human terms from graphene integer math always at this level.
The nested dictionaries are flattened, excess data is stripped.  Prices are in float format with 16 digit precision.   Amounts are in float format with the respective precision of each asset.   The purpose is to refine
what is most pertinent to algorithmic traders and put it in the format they would expect
from a centralized exchange.   A unit test is included for this module, to test the rpc methods:

`python3 graphene_rpc.py`

This module can be imported as:
```python
from graphene_rpc import GrapheneRemoteProcedureCall
from graphene_constants import GrapheneConstants
rpc = GrapheneRemoteProcedureCall(GrapheneConstants("peerplays"))
print(rpc.last)
print(rpc.book)
print(rpc.history)
# etc...
```
### graphene_sql.py

This module sets up a new database for one chain, for one account, and for multiple trading pairs.  It creates space for all pertinent data using multiple sqlite tables with rows columns containing json:

It also provides a safe read/write wrapper used by other modules formating the database rows and columns instead as a python a list of dicts.
```python
dml = {
   "query": f"""
   SELECT * FROM {table}
   """,
   "values": tuple(),
}
# ==========================================================================
print(sql.execute([dml]))

>>> [{"col1":0 "col2":1}, {"col1":3 "col2":4}]
```
 unit test is included for this module, to build a test database:

`python3 graphene_sql.py`

### graphene_signing.py

ECDSA transaction signing is distilled from pybitshares(MIT), but is not dependent.
serializing, signing, and verifying
is all spelled out in script in a minimalist manner for the task.
This consise script takes the place of the otherwise large python signing dependency.

### graphene_auth.py

graphene_auth.py is a wrapper for graphene_signing.py which provides the user with the functions

`prototype_order()`
`broker(order)`

prototype order creates the required headers for an order on the blockchain.   broker method ensures the order is properly built and then sends it on to be signed by graphene_signing.py and broadcast by graphene_rpc.py

### unit_test_private.py

this is a unit test for graphene_auth.py   the user should familiarize themselves with the amounts and prices hard coded to be bought/sold.   tests can be performed on testnet or mainnet of peerplays or bitshares.

### Discussion

This project is phase one of connecting Peerplays and other graphene blockchains to hummingbot.  This package can be used stand alone, as sub modules, or eventually as part of a hummingbot market making connector.

# Summary for Shareholders

PBSA and litepresence.com are cooperating to bring Hummingbot's algorithmic traders to the Graphene blockchain decentralized exchange community.

# Copyright

see LICENSE.txt

# See Also

www.litepresence.com

www.pbsa.info

www.github.com/squidKid-deluxe

www.hummingbot.org

# Tip Cup

(Bitshares) `litepresence1` 1.2.743179
(Bitshares) `squidkid-deluxe256` 1.2.1798534
