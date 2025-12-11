import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from packages.deck_tools import *
from packages.game_tools import *
from packages.database_tools import conn, cur
import pandas as pd

"""
Add games to database queue for workers to run
"""

# Set up commandline argument parser
parser = argparse.ArgumentParser(description="Add game to database queue for workers to run",
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("-d", "--decks", action="store", help="comma separated list of deck names", required=True)
parser.add_argument("-n", "--games", action="store", help="number of games to run (per combination if tournament)", default='1')
parser.add_argument("-f", "--format", action="store", help="game format (constructed, commander, jumpstart)", default='constructed')
parser.add_argument("-p", "--print_decks", action="store_true", help="print all decks for format, then quit")
args = vars(parser.parse_args())

# Ensure all variables have valid values
try:
    args['games'] = int(args['games'])
except (ValueError, TypeError):
    raise ValueError("The value for --games must be an integer.")
assert isinstance(args['games'], int), 'failed to convert "games" to int'

valid_formats = ['constructed', 'commander', 'jumpstart']
if args['format'] not in valid_formats:
    raise ValueError(f"Invalid format '{args['format']}'. Valid options are: {', '.join(valid_formats)}.")

create_game(
    args['decks'],
    args['format'],
    args['games'],
    args['print_decks'],
)