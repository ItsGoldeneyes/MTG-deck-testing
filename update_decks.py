import argparse
import io
import uuid
from datetime import datetime

from tools.deck_tools import *
# from tools.game_tools import *
from tools.database_tools import conn, cur

"""
Parse jumpstart decks at input directory or commandline argument, if specified
"""

# Set up commandline argument parser
parser = argparse.ArgumentParser(description="Parse Jumpstart decks from input file, then upload to database",
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("-f", "--file", action="store", help="input file", default='input/jumpstart.txt')
args = parser.parse_args()
args = vars(parser.parse_args())


# Read input file
input_file = args['file']
try:
    with open(input_file, 'r') as file:
        cards = file.readlines()
except FileNotFoundError:
    raise FileNotFoundError(f"Input file '{input_file}' not found.")


# Read decks from input, add lands if missing
cards_df = parse_decks(cards)
cards_df = add_lands(cards_df)

assert len(cards_df['deck_name'].unique()) == cards_df['quantity'].astype(int).sum() // 20, "Deck count does not match expected value (cards/20)"

decks_df = generate_decklists(cards_df)

# Add audit columns to decks_df
decks_df.insert(0, 'primary_key', [str(uuid.uuid4()) for _ in range(len(decks_df))])
decks_df.insert(1, 'uploaded_on', datetime.now().isoformat())
decks_df.insert(2, 'format', 'jumpstart')
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
