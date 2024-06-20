#!/usr/bin/env python
# DISABLE SELECT PYLINT TESTS
# pylint: disable=import-error, invalid-name, line-too-long, broad-except
# pylint: disable=too-many-branches, too-many-statements, bad-continuation
r"""
 ╔════════════════════════════════════════════════════╗
 ║ ╔═╗╦═╗╔═╗╔═╗╦ ╦╔═╗╔╗╔╔═╗  ╔╦╗╔═╗╔╦╗╔═╗╔╗╔╔═╗╔╦╗╔═╗ ║
 ║ ║ ╦╠╦╝╠═╣╠═╝╠═╣║╣ ║║║║╣   ║║║║╣  ║ ╠═╣║║║║ ║ ║║║╣  ║
 ║ ╚═╝╩╚═╩ ╩╩  ╩ ╩╚═╝╝╚╝╚═╝  ╩ ╩╚═╝ ╩ ╩ ╩╝╚╝╚═╝═╩╝╚═╝ ║
 ╚════════════════════════════════════════════════════╝
UTILITIES
A COLLECTION OF SHARED UTILITY FUNCTIONS FOR DEX CONNECTIVITY
"""
# STANDARD MODULES
import inspect
import json
import time
from calendar import timegm
from datetime import datetime
from random import random
from time import strptime
from traceback import format_exc
from typing import Dict


def trace(error):
    """
    print stack trace upon exception
    """
    msg = str(type(error).__name__) + "\n"
    msg += str(error.args) + "\n"
    msg += str(format_exc()) + "\n"
    return msg


def exception_handler(error):
    """
    :return str(): red formatted error name and args
    """
    return f"{type(error).__name__} {error.args}"


def line_info():
    """
    :return str(): red formatted function and line number
    """
    info = inspect.getframeinfo(inspect.stack()[1][0])
    return "function " + str(info.function) + " line " + str(info.lineno)


def ld2dd(list_of_dicts: list, key: str) -> dict:
    """
    IN [
        {a:1, b:2, c:3},
        {a:1.1, b:2.1, c:3.1},
    ]
    OUT key=a {
        1 : { b:1 , c:3},
        1.1 : {b:2.1, c:3.1},
    }
    """
    return {d[key]: {k: v for k, v in d.items() if k != key} for d in list_of_dicts}


def blip(
    dur: float = 0.1,  # duration of the pause
    rand: bool = True,  # implements a random pause up to duration
):
    """
    sleep for a short period to cog events
    """
    if rand:
        dur *= random()
    time.sleep(dur)


def almost(
    sample: float,
    benchmark: float,
    threshold: float = 0.99,
) -> bool:
    """
    returns True if sample is within threshold of the benchmark, else False
    """
    return benchmark * threshold < sample < benchmark / threshold


def sls(container) -> list:
    """
    sorted list set
    """
    return sorted(list(set(container)))


def merge_dicts(source: Dict, destination: Dict) -> Dict:
    """
    deeply merge two dictionaries
    """
    for key, value in source.items():
        if isinstance(value, dict):
            # get node or create one
            node = destination.setdefault(key, {})
            merge_dicts(value, node)
        else:
            destination[key] = value
    return destination


def remove_chars(
    string: str,
    chars: str,
) -> str:
    """
    Return string without given characters
    """
    return "".join(c for c in string if c not in set(chars))


def get_new_client_order_id(
    is_buy: bool,
    trading_pair: str,
) -> str:
    """
    when sending authenticated request create a unique client side identifier
    """
    side = "B" if is_buy else "S"
    return f"{side}-{trading_pair}-{int(100*time.time())}"  # FIXME get_tracking_nonce()


def reference_swap(my_dict: dict) -> dict:
    """
    swap keys with values, note values must be immutable
    """
    return {v: k for k, v in my_dict.items()}


def assets_from_pairs(trading_pairs: list) -> list:
    """
    get a list of assets from a list of trading_pairs
    :param list(trading_pairs): ["AAA-BBB", "BBB-CCC", "DDD-AAA"]
    :return list(assets): ['AAA', 'BBB', 'CCC', 'DDD']
    """
    assets = []
    for pair in trading_pairs:
        assets += pair.split("-")
    return sls(assets)


def invert_pairs(trading_pairs: list) -> list:
    """
    swap quote w/ base
    :param list(trading_pairs): ["AAA-BBB", "BBB-CCC", "DDD-AAA"]
    :return list(trading_pairs): ["BBB-AAA", "CCC-BBB", "AAA-DDD"]
    """
    return [f"{i.split('-')[1]}-{i.split('-')[0]}" for i in trading_pairs]


def precision(number, places):
    """
    String representation of float to n decimal places
    """
    return ("%." + str(places) + "f") % float(number)


def jprint(obj: str) -> None:
    """
    pretty print json
    """
    print(json.dumps(obj, indent=4))


def it(style, text: str, background: int = None) -> str:
    """
    format string w/ escape sequence to a specific color "style":
       ~ RGB as tuple(red, green, blue)
       ~ HEX prefixed with # as #EEEEEE
       ~ integer 256 color
       ~ or one of ten named color "emphasis" strings from the 256 pallette
    background needs to an integer 256 color
    """

    def hex_to_rgb(value):
        value = value.lstrip("#")
        lenv = len(value)
        return tuple(int(value[i : i + lenv // 3], 16) for i in range(0, lenv, lenv // 3))

    # monokai
    emphasis = {
        "red": 197,
        "green": 154,
        "yellow": 227,
        "orange": 208,
        "purple": 141,  # 177,
        "blue": 51,
        "white": 231,
        "gray": 250,
        "grey": 250,
        "black": 236,
        "cyan": 51,
    }
    ret = text
    if background is not None:
        text = f"\033[48;5;{background}m" + str(text)
    if isinstance(style, str):
        if style[0] == "#":
            style = hex_to_rgb(style)
            red, green, blue = style
            ret = f"\033[38;2;{red};{green};{blue}m" + str(text) + "\033[0m"
        else:
            ret = f"\033[38;5;{emphasis[style]}m" + str(text) + "\033[0m"
    elif isinstance(style, int):
        ret = f"\033[38;5;{style}m" + str(text) + "\033[0m"
    elif isinstance(style, tuple):
        red, green, blue = style
        ret = f"\033[38;2;{red};{green};{blue}m" + str(text) + "\033[0m"
    return ret


def at(
    spot: tuple,  # (col, row, width, height,)
    # ~ col: int,  # begin at this x counting from left of terminal right
    # ~ row: begin at this y counting from top of terminal down
    # ~ width: int,  # from x, y clear space this wide toward the right
    # ~ height: int,  # and from there, this far down
    data: str,  # return to row, col and insert this multi line block text
):
    """
    format string w/ escape sequence
    to clear a terminal area at specific location of specified size
    and print a multi line text in that area
    """
    final = "".join(f"\033[{spot[1] + i};{spot[0]}H" + " " * spot[2] for i in range(spot[3]))
    for ldx, line in enumerate(data.split("\n")):
        final += f"\033[{spot[1]+ldx};{spot[0]}H" + line
    return final


def two_tone(data, fgr, bgr):
    """
    given a dict or list convert it to indented json and return as two tone string
    """
    return "".join(
        it(fgr, char) if char.isdigit() else it(bgr, char)
        for char in json.dumps(data, indent=2).strip('"')
    )


def to_iso_date(unix: int) -> str:  #
    """
    returns CONSTANTS.core.ISO8601 datetime given unix epoch
    """
    return datetime.utcfromtimestamp(int(unix)).isoformat()


def from_iso_date(iso: str) -> int:
    """
    returns unix epoch given CONSTANTS.core.ISO8601 datetime
    """
    return int(timegm(strptime((iso + "UTC"), "%Y-%m-%dT%H:%M:%S%Z")))
