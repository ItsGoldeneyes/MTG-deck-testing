import argparse
import io
import uuid
import logging
import sys
from pathlib import Path
from datetime import datetime

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from packages.deck_tools import create_deck
from packages.database_tools import conn, cur

"""
Parse jumpstart decks at input directory or commandline argument, if specified
"""

# Set up commandline argument parser
parser = argparse.ArgumentParser(description="Parse Jumpstart decks from input file, then upload to database",
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("-i", "--input", action="store", help="input file", default='input/decks.txt')
parser.add_argument("-d", "--deck_name", action="store", help="Name of deck", default='deckname')
parser.add_argument("-f", "--format", action="store", help="game format (constructed, commander, jumpstart)", default='constructed')
parser.add_argument("-u", "--user_id", action="store", default='None')
args = parser.parse_args()
args = vars(parser.parse_args())
logging.info('Logs parsed!')

# Read input file
input_file = args['input']
try:
    with open(input_file, 'r') as file:
        cards = file.readlines()
except FileNotFoundError:
    print('File not found')
    raise FileNotFoundError(f"Input file '{input_file}' not found.")

# Read decks from input, add lands if missing
user_id = args['user_id']
deck_name = args['deck_name']
format = args['format']

# print(f'''
#         Creating decks for:
#              user: {user_id}\n
#              deck_name: {deck_name}\n
#              format: {format}\n
#              ''')
result = create_deck(cards,
            user_id,
            deck_name,
            format)
if result[0] == True:
    print("Decks uploaded successfully!")
else:
    print(f"Deck upload failed, {result}")