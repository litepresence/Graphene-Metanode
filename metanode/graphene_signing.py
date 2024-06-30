#!/usr/bin/env python
# DISABLE SELECT PYLINT TESTS
# pylint: disable=import-error, bad-continuation, line-too-long, too-few-public-methods
# pylint: disable=redefined-outer-name, too-many-function-args, broad-except
# pylint: disable=super-init-not-called
r"""
 ╔════════════════════════════════════════════════════╗
 ║ ╔═╗╦═╗╔═╗╔═╗╦ ╦╔═╗╔╗╔╔═╗  ╔╦╗╔═╗╔╦╗╔═╗╔╗╔╔═╗╔╦╗╔═╗ ║
 ║ ║ ╦╠╦╝╠═╣╠═╝╠═╣║╣ ║║║║╣   ║║║║╣  ║ ╠═╣║║║║ ║ ║║║╣  ║
 ║ ╚═╝╩╚═╩ ╩╩  ╩ ╩╚═╝╝╚╝╚═╝  ╩ ╩╚═╝ ╩ ╩ ╩╝╚╝╚═╝═╩╝╚═╝ ║
 ╚════════════════════════════════════════════════════╝
~
GRAPHENE BASE SIGNING
~
CONCISE GRAPHENE SERIALIZATION AND ECDSA TO AUTHENTICATE / BUY / SELL / CANCEL
~
h/t @xeroc and other contiributors
most of this script is distilled from pybitshares (MIT)
"""
# STANDARD MODULES
import os
from binascii import hexlify  # binary text to hexidecimal
from binascii import unhexlify  # hexidecimal to binary text
from collections import OrderedDict  # required for serialization
from hashlib import new as hashlib_new  # access algorithm library
from hashlib import sha256  # message digest algorithm
from json import dumps as json_dumps  # serialize object to string
from json import loads as json_loads  # deserialize string to object
from struct import pack  # convert to string representation of C struct

# THIRD PARTY MODULES
from ecdsa import SECP256k1 as ecdsa_SECP256k1  # curve
from ecdsa import SigningKey as ecdsa_SigningKey  # class
from ecdsa import VerifyingKey as ecdsa_VerifyingKey  # class
from ecdsa import numbertheory as ecdsa_numbertheory  # by far the largest import
from ecdsa import util as ecdsa_util  # module
from secp256k1 import PrivateKey as secp256k1_PrivateKey  # class
from secp256k1 import PublicKey as secp256k1_PublicKey  # class
from secp256k1 import ffi as secp256k1_ffi  # compiled ffi object
from secp256k1 import lib as secp256k1_lib  # library

# GRAPHENE MODULES
from .graphene_constants import GrapheneConstants
from .graphene_utils import from_iso_date, it, trace


# GLOBAL CONSTANTS
CONSTANTS = GrapheneConstants()


class ObjectId:
    """
    Bitshares(MIT)
    encodes aaa.bbb.ccc object ids - serializes the *instance* only!
    ~
    A.B.C = PROTOCOL ID . IMPLEMENTATION ID . INSTANCE ID
    """

    def __init__(self, object_str, type_verify=None):
        # if after splitting aaa.bbb.ccc there are 3 pieces:
        if len(object_str.split(".")) == 3:
            # assign those three pieces to aaa, bbb, and ccc
            aaa, bbb, ccc = object_str.split(".")
            # assure they are integers
            self.aaa = int(aaa)
            self.bbb = int(bbb)
            self.ccc = int(ccc)
            # serialize the ccc element; the "instance"
            self.instance = Id(self.ccc)
            self.abc = object_str
            # 1.2.x:account, 1.3.x:asset, or 1.7.x:limit
            if type_verify:
                assert CONSTANTS.core.TYPES[type_verify] == int(bbb), (
                    # except raise error showing mismatch
                    "Object id does not match object type! "
                    + "Expected %d, got %d" % (CONSTANTS.core.TYPES[type_verify], int(bbb))
                )
        else:
            raise Exception("Object id is invalid")

    def __bytes__(self):
        """
        b'\x00\x00\x00' of serialized ccc element; the "instance"
        """
        return bytes(self.instance)


class Id:
    """
    Bitshares(MIT)
    serializes the c element of "a.b.c" types
    merged with Varint32()
    """

    def __init__(self, data):
        self.data = int(data)

    def __bytes__(self):
        return bytes(varint(self.data))


class Array:
    """
    Bitshares(MIT)
    serializes lists as byte strings
    merged with Set() and Varint32()
    """

    def __init__(self, data):
        self.data = data
        self.length = int(len(self.data))

    def __bytes__(self):
        return bytes(varint(self.length)) + b"".join([bytes(a) for a in self.data])


class Uint8:
    """
    Bitshares(MIT)
    byte string of 8 bit unsigned integers
    merged with Bool()
    """

    def __init__(self, data):
        self.data = int(data)

    def __bytes__(self):
        return pack("<B", self.data)


class Uint16:
    """
    Bitshares(MIT)
    byte string of 16 bit unsigned integers
    """

    def __init__(self, data):
        self.data = int(data)

    def __bytes__(self):
        return pack("<H", self.data)


class Uint32:
    """
    Bitshares(MIT)
    byte string of 32 bit unsigned integers
    """

    def __init__(self, data):
        self.data = int(data)

    def __bytes__(self):
        return pack("<I", self.data)


class Int64:
    """
    Bitshares(MIT)
    byte string of 64 bit unsigned integers
    """

    def __init__(self, data):
        self.data = int(data)

    def __bytes__(self):
        return pack("<q", self.data)


class Optional:
    """
    Bitshares(MIT)
    """

    def __init__(self, data):
        self.data = data

    def __bytes__(self):
        if not bool(self.data):
            return bytes(Uint8(0))
        return bytes(Uint8(1)) + bytes(self.data) if bytes(self.data) else bytes(Uint8(0))

    def __str__(self):
        return str(self.data)

    def isempty(self):
        """
        is there no data
        """
        if self.data is None:
            return True
        if not bool(str(self.data)):  # pragma: no cover
            return True
        return not bool(bytes(self.data))


class Signature:
    """
    Bitshares(MIT)
    used to disable bytes() method on Signatures in OrderedDicts
    """

    def __init__(self, data):
        self.data = data

    def __bytes__(self):
        return self.data  # note does NOT return bytes(self.data)


class PointInTime:
    """
    Bitshares(MIT)
    used to pack ISO8601 time as 4 byte unix epoch integer as bytes
    """

    def __init__(self, data):
        self.data = data

    def __bytes__(self):
        return pack("<I", from_iso_date(self.data))


class StaticVariant:
    """
    Bitshares(MIT)
    """

    def __init__(self, data, type_id):
        self.data = data
        self.type_id = type_id

    def __bytes__(self):
        return varint(self.type_id) + bytes(self.data)

    def __str__(self):
        return json_dumps([self.type_id, self.data.json()])


def is_args_this_class(self, args):
    """
    Bitshares(MIT) graphenebase/objects.py
    True if there is only one argument
    and its type name is the same as the type name of self
    """
    return len(args) == 1 and type(args[0]).__name__ == type(self).__name__


def varint(num):
    """
    Bitshares(MIT)
    varint encoding normally saves memory on smaller numbers
    yet retains ability to represent numbers of any magnitude
    """
    data = b""
    while num >= 0x80:
        data += bytes([(num & 0x7F) | 0x80])
        num >>= 7
    data += bytes([num])
    return data


# BASE 58 ENCODE, DECODE, AND CHECK "  # Bitshares(MIT) graphenebase/base58.py
def base58_decode(base58_str):
    """
    Bitshares(MIT)
    """
    base58_text = bytes(base58_str, "ascii")
    num = 0
    leading_zeroes_count = 0
    for byte in base58_text:
        num = num * 58 + CONSTANTS.core.BASE58.find(byte)
        if num == 0:
            leading_zeroes_count += 1
    res = bytearray()
    while num >= 256:
        div, mod = divmod(num, 256)
        res.insert(0, mod)
        num = div
    res.insert(0, num)
    return hexlify(bytearray(1) * leading_zeroes_count + res).decode("ascii")


def base58_encode(hexstring):
    """
    Bitshares(MIT)
    """
    byteseq = bytes(unhexlify(bytes(hexstring, "ascii")))
    num = 0
    leading_zeroes_count = 0
    for byte in byteseq:
        num = num * 256 + byte
        if num == 0:
            leading_zeroes_count += 1
    res = bytearray()
    while num >= 58:
        div, mod = divmod(num, 58)
        res.insert(0, CONSTANTS.core.BASE58[mod])
        num = div
    res.insert(0, CONSTANTS.core.BASE58[num])
    return (CONSTANTS.core.BASE58[0:1] * leading_zeroes_count + res).decode("ascii")


def ripemd160(string):
    """
    160-bit cryptographic hash function
    """
    r160 = hashlib_new("ripemd160")  # import the library
    r160.update(unhexlify(string))
    return r160.digest()


def double_sha256(string):
    """
    double sha256 cryptographic hash function
    """
    return sha256(sha256(unhexlify(string)).digest()).digest()


def base58_check_encode(version, payload):
    """
    encode arbitrary binary data into a textual representation that is easier to handle
    """
    string = ("%.2x" % version) + payload
    checksum = double_sha256(string)[:4]
    return base58_encode(string + hexlify(checksum).decode("ascii"))


def gph_base58_check_encode(string):
    """
    gph implements the encoding in ripemd160 instead of double sha
    """
    checksum = ripemd160(string)[:4]
    return base58_encode(string + hexlify(checksum).decode("ascii"))


def base58_check_decode(string):
    """
    encoded data can be decoded back to its original human readable form
    """
    string = unhexlify(base58_decode(string))
    dec = hexlify(string[:-4]).decode("ascii")
    checksum = double_sha256(dec)[:4]
    assert string[-4:] == checksum
    return dec[2:]


def gph_base58_check_decode(string):
    """
    gph version using ripemd160
    """
    string = unhexlify(base58_decode(string))
    dec = hexlify(string[:-4]).decode("ascii")
    checksum = ripemd160(dec)[:4]
    assert string[-4:] == checksum
    return dec


class GrapheneObject:
    """
    Bitshares(MIT) graphenebase/objects.py
    """

    def __init__(self, data=None):
        self.data = data

    def __bytes__(self):
        """
        encodes data into wire format
        """
        if self.data is None:
            return bytes()
        buf = b""
        for value in self.data.values():
            buf += bytes(value, "utf-8") if isinstance(value, str) else bytes(value)
        return buf


class LimitOrderCreate(GrapheneObject):
    """
    Bitshares(MIT) bitsharesbase/operations.py
    """

    def __init__(self, *args, **kwargs):
        if is_args_this_class(self, args):
            self.data = args[0].data
        else:
            if len(args) == 1 and len(kwargs) == 0:
                kwargs = args[0]
            super().__init__(
                OrderedDict(
                    [
                        ("fee", Asset(kwargs["fee"])),
                        (
                            "seller",
                            ObjectId(kwargs["seller"], "account"),
                        ),
                        (
                            "amount_to_sell",
                            Asset(kwargs["amount_to_sell"]),
                        ),
                        (
                            "min_to_receive",
                            Asset(kwargs["min_to_receive"]),
                        ),
                        (
                            "expiration",
                            PointInTime(kwargs["expiration"]),
                        ),
                        ("fill_or_kill", Uint8(kwargs["fill_or_kill"])),
                        ("extensions", Array([])),
                    ]
                )
            )


class LimitOrderCancel(GrapheneObject):
    """
    Bitshares(MIT) bitsharesbase/operations.py
    """

    def __init__(self, *args, **kwargs):
        if is_args_this_class(self, args):
            self.data = args[0].data
        else:
            if len(args) == 1 and len(kwargs) == 0:
                kwargs = args[0]
            super().__init__(
                OrderedDict(
                    [
                        ("fee", Asset(kwargs["fee"])),
                        (
                            "fee_paying_account",
                            ObjectId(kwargs["fee_paying_account"], "account"),
                        ),
                        (
                            "order",
                            ObjectId(kwargs["order"], "limit_order"),
                        ),
                        ("extensions", Array([])),
                    ]
                )
            )


# MESSAGE VERIFICATION
def verify_message(message, signature):
    """
    Bitshares(MIT) raphenebase/ecdsa.py stripped of non-secp256k1 methods
    returns bytes
    """
    # require message and signature to be bytes
    if not isinstance(message, bytes):
        message = bytes(message, "utf-8")
    if not isinstance(signature, bytes):
        signature = bytes(signature, "utf-8")
    # recover parameter only
    recover_parameter = bytearray(signature)[0] - 4 - 27
    # "bitwise or"; each bit of the output is 0
    # if the corresponding bit of x AND of y is 0, otherwise it's 1
    # ecdsa.PublicKey with additional functions to serialize
    # in uncompressed and compressed formats
    pub = secp256k1_PublicKey(
        flags=secp256k1_lib.SECP256K1_CONTEXT_VERIFY | secp256k1_lib.SECP256K1_CONTEXT_SIGN
    )
    # recover raw signature
    sig = pub.ecdsa_recoverable_deserialize(signature[1:], recover_parameter)
    # recover public key
    verify_pub = secp256k1_PublicKey(pub.ecdsa_recover(message, sig))
    # convert recoverable sig to normal sig
    normal_sig = verify_pub.ecdsa_recoverable_convert(sig)
    # verify
    verify_pub.ecdsa_verify(message, normal_sig)
    return verify_pub.serialize(compressed=True)


def sign_transaction(trx, message, wif, prefix):
    """
    # Bitshares(MIT) graphenebase/ecdsa.py
    # tools.ietf.org/html/rfc6979
    # @xeroc/steem-transaction-signing-in-a-nutshell
    # @dantheman/steem-and-bitshares-cryptographic-security-update
    # deterministic signatures retain the cryptographic
    # security features associated with digital signatures
    # but can be more easily implemented
    # since they do not need high-quality randomness
    """

    def canonical(sig):
        """
        1 in 4 signatures are randomly canonical; "normal form"
        using the other three causes vulnerability to maleability attacks
        as a metaphor; "require reduced fractions in simplest terms"
        note: 0x80 hex = 10000000 binary = 128 integer
        :return bool():
        """
        sig = bytearray(sig)
        return not any(
            [
                int(sig[0]) & 0x80,
                int(sig[32]) & 0x80,
                sig[0] == 0 and not int(sig[1]) & 0x80,
                sig[32] == 0 and not int(sig[33]) & 0x80,
            ]
        )

    # create fixed length representation of arbitrary length data
    # this will thoroughly obfuscate and compress the transaction
    # signing large data is computationally expensive and time consuming
    # the hash of the data is a relatively small
    # signing hash is more efficient than signing serialization
    digest = sha256(message).digest()
    # ECDSA
    # eliptical curve digital signature algorithm
    # this is where the real hocus pocus lies
    # all of the ordering, typing, serializing, and digesting
    # culminates with the message meeting the wif
    # begin with the 8 bit string representation of private key
    private_key = bytes(PrivateKey(wif=wif, prefix=prefix))
    # create some arbitrary data used by the nonce generation
    ndata = secp256k1_ffi.new("const int *ndata")
    ndata[0] = 0  # it adds "\0x00", then "\0x00\0x00", etc..
    while True:  # repeat process until deterministic and cannonical
        ndata[0] += 1  # increment the arbitrary nonce
        # obtain compiled/binary private key from the wif
        privkey = secp256k1_PrivateKey(private_key, raw=True)
        # create a new recoverable 65 byte ECDSA signature
        sig = secp256k1_ffi.new("secp256k1_ecdsa_recoverable_signature *")
        # parse a compact ECDSA signature (64 bytes + recovery id)
        # returns: 1 = deterministic; 0 = not deterministic
        deterministic = secp256k1_lib.secp256k1_ecdsa_sign_recoverable(
            privkey.ctx,  # initialized context object
            sig,  # array where signature is held
            digest,  # 32-byte message hash being signed
            privkey.private_key,  # 32-byte secret key
            secp256k1_ffi.NULL,  # default nonce function
            ndata,  # incrementing nonce data
        )
        if not deterministic:
            continue
        # we derive the recovery parameter
        # which simplifies the verification of the signature
        # it links the signature to a single unique public key
        # without this parameter, the back-end would need to test
        # for multiple public keys instead of just one
        signature, i = privkey.ecdsa_recoverable_serialize(sig)
        # we ensure that the signature is canonical; simplest/reduced form
        if canonical(signature):
            # add 4 and 27 to stay compatible with other protocols
            i += 4  # compressed
            i += 27  # compact
            # and have now obtained our signature
            break
    # having derived a valid canonical signature
    # we format it in its hexadecimal representation
    # and add it our transactions signatures
    # note that we do not only add the signature
    # but also the recover parameter
    # this kind of signature is then called "compact signature"
    signature = hexlify(pack("<B", i) + signature).decode("ascii")
    trx["signatures"].append(signature)
    return trx


class Asset(GrapheneObject):
    """
    Bitshares(MIT) bitsharesbase/objects.py
    """

    def __init__(self, *args, **kwargs):
        if is_args_this_class(self, args):
            self.data = args[0].data
        else:
            if len(args) == 1 and len(kwargs) == 0:
                kwargs = args[0]
            super().__init__(
                OrderedDict(
                    [
                        ("amount", Int64(kwargs["amount"])),
                        (
                            "asset_id",
                            ObjectId(kwargs["asset_id"], "asset"),
                        ),
                    ]
                )
            )


class Operation:
    """
    "class GPHOperation():"
    # Bitshares(MIT) graphenebase/objects.py
    "class Operation(GPHOperation):"
    # Bitshares(MIT) bitsharesbase/objects.py
    """

    def __init__(self, operation):
        if not isinstance(operation, list):
            raise ValueError("expecting operation to be a list")
        if len(operation) != 2:
            raise ValueError("expecting operation to be two items")
        if not isinstance(operation[0], int):
            raise ValueError("expecting operation[0] to be integer")
        self.op_id = operation[0]
        name = CONSTANTS.core.OP_NAMES[self.op_id]
        self.name = name[0].upper() + name[1:]
        if operation[0] == 1:
            self.operation = LimitOrderCreate(operation[1])
        if operation[0] == 2:
            self.operation = LimitOrderCancel(operation[1])

    def __bytes__(self):
        return bytes(Id(self.op_id)) + bytes(self.operation)


def verify_transaction(trx, wif, constants):
    """
    # gist.github.com/xeroc/9bda11add796b603d83eb4b41d38532b
    # once you have derived your new trx including the signatures
    # verify your transaction and it's signature
    """
    tx2 = SignedTransaction(**trx, constants=constants)
    tx2.derive_digest()
    pubkeys = [PrivateKey(wif=wif, prefix=constants.chain.PREFIX).pubkey]
    tx2.verify(pubkeys)
    return trx


# SERIALIZATION
def serialize_transaction(trx, constants, rpc):
    """
    {"method":"call","params":[
        2,
        "get_required_signatures",
            [{"ref_block_num":0,
            "ref_block_prefix":0,
            "expiration":"1970-01-01T00:00:00",
            "operations":
                [[3,{
                "fee":{"amount":"48260","asset_id":"1.3.0"},
                "funding_account":"1.2.11111111",
                "delta_collateral":{"amount":"1","asset_id":"1.3.5650"},
                "delta_debt":{"amount":"0","asset_id":"1.3.5662"},
                "extensions":{"target_collateral_ratio":2000}}]],
                "extensions":[],"signatures":[]},
                ["BTS6upQe7upQe7upQe7upQe7upQe7upQe7upQe7upQe7upQe7upQe7"]]],
            "id":371}
    """
    if trx["operations"] == []:
        return trx, b""
    # gist.github.com/xeroc/9bda11add796b603d83eb4b41d38532b
    # RPC call for ordered dicts which are dumped by the query
    tx_ops = trx["operations"]
    for idx, _ in enumerate(tx_ops):
        if "memo" in tx_ops[idx][1].keys() and tx_ops[idx][1]["memo"] == "":
            tx_ops[idx][1] = {k: v for k, v in tx_ops[idx][1].items() if k != "memo"}
    rpc_tx = dict(trx)
    rpc_tx["operations"] = tx_ops
    # find out how the backend suggests to serialize the trx
    rpc_tx_hex = rpc.get_transaction_hex(json_loads(json_dumps(rpc_tx)))
    buf = b""  # create an empty byte string buffer
    # add block number, prefix, and trx expiration to the buffer
    buf += pack("<H", trx["ref_block_num"])  # 2 byte int
    buf += pack("<I", trx["ref_block_prefix"])  # 4 byte int
    buf += pack("<I", from_iso_date(trx["expiration"]))  # 4 byte int
    # add length of operations list to buffer
    buf += bytes(varint(len(trx["operations"])))
    # add the operations list to the buffer in graphene type fashion
    for ops in trx["operations"]:
        # print(ops[0])  # Int (1=create, 2=cancel)
        # print(ops[1])  # OrderedDict of operations
        buf += varint(ops[0])
        if ops[0] == CONSTANTS.core.OP_IDS["LimitOrderCreate"]:  # 1
            buf += bytes(LimitOrderCreate(ops[1]))
        if ops[0] == CONSTANTS.core.OP_IDS["LimitOrderCancel"]:  # 2
            buf += bytes(LimitOrderCancel(ops[1]))
    # add legth of (empty) extensions list to buffer
    buf += bytes(varint(len(trx["extensions"])))  # usually, effectively varint(0)
    # this the final manual transaction hex, which should match rpc
    manual_tx_hex = hexlify(buf)
    # prepend the chain constants.chain.ID to the buffer to create final serialized msg
    message = unhexlify(constants.chain.ID) + buf
    # if serialization is correct: rpc_tx_hex = manual_tx_hex plus an empty signature
    assert rpc_tx_hex == manual_tx_hex + b"00", "Serialization Failed"
    return trx, message


class SignedTransaction(GrapheneObject):
    """ "
    merged litepresence2019
    Bitshares(MIT) graphenebase/signedtransactions.py
    Bitshares(MIT) bitsharesbase/signedtransactions.py
    """

    def __init__(self, constants, *args, **kwargs):
        """Create a signed transaction and
            offer method to create the signature
        (see ``getBlockParams``)
        :param num refNum: parameter ref_block_num
        :param num refPrefix: parameter ref_block_prefix
        :param str expiration: expiration date
        :param Array operations:  array of operations
        """
        self.message = None
        self.digest = None
        self.constants = constants
        if is_args_this_class(self, args):
            self.data = args[0].data
        else:
            if len(args) == 1 and len(kwargs) == 0:
                kwargs = args[0]
            if (
                "extensions" not in kwargs
                or "extensions" in kwargs
                and not kwargs.get("extensions")
            ):
                kwargs["extensions"] = Array([])
            if "signatures" not in kwargs:
                kwargs["signatures"] = Array([])
            else:
                kwargs["signatures"] = Array(
                    [Signature(unhexlify(a)) for a in kwargs["signatures"]]
                )
            if "operations" in kwargs:
                opklass = Operation  # self.get_operation_klass()
                if all(not isinstance(a, opklass) for a in kwargs["operations"]):
                    kwargs["operations"] = Array([opklass(a) for a in kwargs["operations"]])
                else:
                    kwargs["operations"] = Array(kwargs["operations"])
            super().__init__(
                OrderedDict(
                    [
                        (
                            "ref_block_num",
                            Uint16(kwargs["ref_block_num"]),
                        ),
                        (
                            "ref_block_prefix",
                            Uint32(kwargs["ref_block_prefix"]),
                        ),
                        (
                            "expiration",
                            PointInTime(kwargs["expiration"]),
                        ),
                        ("operations", kwargs["operations"]),
                        ("extensions", kwargs["extensions"]),
                        ("signatures", kwargs["signatures"]),
                    ]
                )
            )

    def derive_digest(self):
        """
        # do not serialize signatures
        # get message to sign
        # bytes(self) will give the wire formated data according to
        # GrapheneObject and the data given in __init__()
        # then restore signatures to starting state
        """
        sigs = self.data["signatures"]
        self.data["signatures"] = []
        self.message = unhexlify(self.constants.chain.ID) + bytes(self)
        self.digest = sha256(self.message).digest()
        self.data["signatures"] = sigs

    def verify(self, pubkeys=None):
        """
        ensure pubkeys are an array and test for missing signatures
        """
        if pubkeys is None:
            pubkeys = []
        self.derive_digest()
        signatures = self.data["signatures"].data
        pub_keys_found = []
        for signature in signatures:
            byte_string = verify_message(self.message, bytes(signature))
            phex = hexlify(byte_string).decode("ascii")
            pub_keys_found.append(phex)
        for pubkey in pubkeys:
            if not isinstance(pubkey, PublicKey):
                raise Exception("Pubkeys must be array of 'PublicKey'")
            key = pubkey.un_compressed()[2:]
            if key not in pub_keys_found and repr(pubkey) not in pub_keys_found:
                raise Exception("signature missing")
        return pub_keys_found


class Address:
    """
    Example :: Address("BTSFN9r6VYzBK8EKtMewfNbfiGCr56pHDBFi")
    Bitshares(MIT) graphenebase/account.py
    """

    def __init__(self, address=None, pubkey=None, prefix="PPY"):
        print(it("red", "Address"), "pubkey", pubkey)
        self.prefix = prefix
        self.pubkey = Base58(pubkey, prefix=prefix)
        self._address = address


class PublicKey(Address):
    """
    This class deals with Public Keys and inherits ``Address``.
    :param str pubkey: Base58 encoded public key
    :param str prefix: Network prefix (defaults to ``PPY``)
    Bitshares(MIT) graphenebase/account.py
    """

    def __init__(self, pubkey, prefix="PPY"):
        print(it("red", "PublicKey"))
        # super().__init__()
        self.prefix = prefix
        self.pubkey = Base58(pubkey, prefix=prefix)
        self.address = Address(pubkey=pubkey, prefix=prefix)

    def _derive_y_from_x(self, x_val, is_even):
        """
        Derive y point from x point
        """
        print(it("purple", "           y^2 = x^3 + ax + b          "))
        print(self, x_val)
        curve = ecdsa_SECP256k1.curve
        curve_a, curve_b, curve_p = curve.a(), curve.b(), curve.p()
        alpha = (pow(x_val, 3, curve_p) + curve_a * x_val + curve_b) % curve_p
        beta = ecdsa_numbertheory.square_root_mod_prime(alpha, curve_p)
        if (beta % 2) == is_even:
            beta = curve_p - beta
        print(beta)
        return beta

    def compressed(self):
        """
        Derive compressed public key
        """
        order = ecdsa_SECP256k1.generator.order()
        point = ecdsa_VerifyingKey.from_string(bytes(self), curve=ecdsa_SECP256k1).pubkey.point
        x_str = ecdsa_util.number_to_string(point.x(), order)
        # y_str = ecdsa_util.number_to_string(point.y(), order)
        compressed = hexlify(bytes(chr(2 + (point.y() & 1)), "ascii") + x_str).decode("ascii")
        return compressed

    def un_compressed(self):
        """
        Derive uncompressed key
        """
        public_key = repr(self.pubkey)
        prefix = public_key[0:2]
        if prefix == "04":
            return public_key
        assert prefix in ["02", "03"]
        x_val = int(public_key[2:], 16)
        y_val = self._derive_y_from_x(x_val, (prefix == "02"))
        return "04" + "%064x" % x_val + "%064x" % y_val

    def __repr__(self):
        """
        Gives the hex representation of the Graphene public key.
        """
        return repr(self.pubkey)

    def __format__(self, _format):
        """
        Formats the instance of:doc:`Base58 <base58>
        ` according to ``_format``
        """
        return format(self.pubkey, _format)

    def __bytes__(self):
        """
        Returns the raw public key (has length 33)
        """
        return bytes(self.pubkey)


class PrivateKey(PublicKey):
    """
    # Bitshares(MIT) graphenebase/account.py
    # Bitshares(MIT) bitsharesbase/account.py
    Derives the compressed and uncompressed public keys and
    constructs two instances of ``PublicKey``:
    """

    def __init__(self, wif=None, prefix="PPY"):
        print(prefix)
        print(it("red", "PrivateKey"))
        print(PublicKey)
        # super().__init__()
        if wif is None:
            print("wif is None")
            self.wif = Base58(hexlify(os.urandom(32)).decode("ascii"), prefix)
        elif isinstance(wif, Base58):
            self.wif = wif
        else:
            self.wif = Base58(wif, prefix)
        # compress pubkeys only
        self._pubkeyhex, self._pubkeyuncompressedhex = self.compressedpubkey()
        self.pubkey = PublicKey(self._pubkeyhex, prefix=prefix)
        self.uncompressed = PublicKey(self._pubkeyuncompressedhex, prefix=prefix)
        self.uncompressed.address = Address(pubkey=self._pubkeyuncompressedhex, prefix=prefix)
        self.address = Address(pubkey=self._pubkeyhex, prefix=prefix)

    def compressedpubkey(self):
        """
        Derive uncompressed public key
        """
        secret = unhexlify(repr(self.wif))
        order = ecdsa_SigningKey.from_string(secret, curve=ecdsa_SECP256k1).curve.generator.order()
        point = ecdsa_SigningKey.from_string(
            secret, curve=ecdsa_SECP256k1
        ).verifying_key.pubkey.point
        x_str = ecdsa_util.number_to_string(point.x(), order)
        y_str = ecdsa_util.number_to_string(point.y(), order)
        compressed = hexlify(chr(2 + (point.y() & 1)).encode("ascii") + x_str).decode("ascii")
        uncompressed = hexlify(chr(4).encode("ascii") + x_str + y_str).decode("ascii")
        return [compressed, uncompressed]

    def __bytes__(self):
        """
        Returns the raw private key
        """
        return bytes(self.wif)


class Base58:
    """
    Bitshares(MIT)
    This class serves as an abstraction layer
    to deal with base58 encoded strings
    and their corresponding hex and binary representation
    """

    def __init__(self, data, prefix="PPY"):
        try:
            self._prefix = prefix
            if all(c in CONSTANTS.core.HEXDIGITS for c in data):
                self._hex = data
            elif data[0] in ["5", "6"]:
                self._hex = base58_check_decode(data)
            elif data[0] in ["K", "L"]:
                self._hex = base58_check_decode(data)[:-2]
            elif data[: len(self._prefix)] == self._prefix:
                self._hex = gph_base58_check_decode(data[len(self._prefix) :])
            else:
                raise ValueError("Error loading Base58 object")
        except Exception as error:
            print("Base58 error", trace(error))

    def __format__(self, _format):
        if _format.upper() != "PPY":
            print("Format %s unkown. You've been warned!\n" % _format)
        return _format.upper() + str(self)

    def __repr__(self):  # hex string of data
        return self._hex

    def __str__(self):  # base58 string of data
        return gph_base58_check_encode(self._hex)

    def __bytes__(self):  # raw bytes of data
        return unhexlify(self._hex)
