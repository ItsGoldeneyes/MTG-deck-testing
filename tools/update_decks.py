import argparse
import io
import uuid
import sys
from pathlib import Path
from datetime import datetime

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from packages.deck_tools import *
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
args = parser.parse_args()
args = vars(parser.parse_args())


# Read input file
input_file = args['input']
try:
    with open(input_file, 'r') as file:
        cards = file.readlines()
except FileNotFoundError:
    raise FileNotFoundError(f"Input file '{input_file}' not found.")

# Read decks from input, add lands if missing
format = args['format']
cards_df = parse_decks(cards, format=format)

# Commented out to upload just half decks for testing
decks_df = cards_df

deck_name = args['deck_name']
if format != 'jumpstart':
    decks_df['deck_name'] = deck_name

# Add audit columns to decks_df
decks_df.insert(0, 'primary_key', [str(uuid.uuid4()) for _ in range(len(decks_df))])
decks_df.insert(1, 'uploaded_on', datetime.now().isoformat())
decks_df.insert(2, 'format', format)
decks_df.insert(2, 'category', 'main')

# Rearrange columns to match table layout
decks_df = decks_df[['primary_key', 'card_name', 'deck_name', 'set_code', 'quantity', 'uploaded_on', 'tag', 'colour', 'format', 'category']]

# Prepare a CSV buffer from the DataFrame
csv_buffer = io.StringIO()
decks_df.to_csv(csv_buffer, index=False, header=False, sep='\t')
csv_buffer.seek(0)

cur.copy_from(csv_buffer, 'decks', sep='\t')
conn.commit()
print("Successfully uploaded decks to database")

cur.close()
conn.close()
