import pandas as pd
import itertools
# import shutil
import os


def generate_decklists(cards_df):
    """
    Creates all possible Jumpstart decks (two half decks put together)

    Args:
        cards_df (DataFrame): Dataframe containing cards categorized into decks

    Returns:
        cards_df (DataFrame): Dataframe containing all combinations of Jumpstart decks
    """
    deck_names = cards_df['deck_name'].unique()
    deck_combinations = itertools.combinations(deck_names, 2)
    decks_df = pd.DataFrame()

    for deck1_name, deck2_name in deck_combinations:
        deck1 = cards_df[cards_df['deck_name'] == deck1_name]
        deck2 = cards_df[cards_df['deck_name'] == deck2_name]
        deck = pd.concat([deck1, deck2])
        deck['deck_name'] = f"{deck1_name} {deck2_name}"
        decks_df = pd.concat([decks_df, deck])

    return decks_df

def generate_deck_files(decks_df, output_path="output/decks"):
    """
    Creates .dck files for all decks in a decks_df

    Args:
        decks_df (DataFrame): Dataframe containing cards categorized into decks
    """

    os.makedirs(output_path, exist_ok=True)
    for filename in os.listdir(output_path):
        file_path = os.path.join(output_path, filename)
        if os.path.isfile(file_path):
            os.unlink(file_path)

    deck_names = decks_df['deck_name'].unique()

    for deck_name in deck_names:
        deck = decks_df[decks_df['deck_name'] == deck_name]
        generate_deck_file(deck, deck_name, output_path)

    # Copy decks to Forge directory if specified
    FORGE_DECKS_PATH = os.environ.get("FORGE_DECKS_PATH") + f"\\{format}"
    if FORGE_DECKS_PATH and os.path.exists(FORGE_DECKS_PATH):
        print(f"Copying decks to Forge directory: {FORGE_DECKS_PATH}")

        # Wipe the forge deck directory
        try:
            for filename in os.listdir(FORGE_DECKS_PATH):
                dst_file = os.path.join(FORGE_DECKS_PATH, filename)
                if os.path.isfile(dst_file) and filename.endswith('.dck'):
                    os.unlink(dst_file)
                    print(f"Removed old deck: {filename}")
        except Exception as e:
            print(f"Error cleaning Forge decks directory: {e}")

        # Copy new decks
        try:
            deck_count = 0
            for filename in os.listdir(output_path):
                if filename.endswith('.dck'):
                    src = os.path.join(output_path, filename)
                    dst = os.path.join(FORGE_DECKS_PATH, filename)
                    if os.path.isfile(src):
                        with open(src, "rb") as fsrc, open(dst, "wb") as fdst:
                            fdst.write(fsrc.read())
                        deck_count += 1
            print(f"Successfully copied {deck_count} decks to Forge directory")
        except Exception as e:
            print(f"Error copying decks to Forge directory: {e}")
    elif FORGE_DECKS_PATH:
        print(f"Warning: FORGE_DECKS_PATH is set but directory does not exist: {FORGE_DECKS_PATH}")
    else:
        print("FORGE_DECKS_PATH not set, skipping copy to Forge directory")

def generate_deck_file(deck, name='Sample Deck', output_path='output/decks'):
    """
    Saves deck as a .dck file for Forge

    Args:
        deck (DataFrame): Dataframe containing cards in a deck
        name (String): Deck name
        output_path (String): Path to output folder
    """
    os.makedirs(output_path, exist_ok=True)

    with open(os.path.join(output_path, f"{name}.dck"), 'w') as f:
        f.write('[metadata]\n')
        f.write(f'Name={name}\n')
        f.write('[Avatar]\n\n')
        f.write('[Main]\n')
        for _, row in deck.iterrows():
            set_code = row['set_code'] if row['set_code'] else ''
            f.write(f"{row['quantity']} {row['card_name']}|{set_code}|1\n")

        f.write('[Sideboard]\n\n')
        f.write('[Planes]\n\n')
        f.write('[Schemes]\n\n')
        f.write('[Conspiracy]\n\n')
        f.write('[Dungeon]')

def add_lands(cards_df):
    """
    Adds lands to decks that do not have lands. Tedious to do in Archidekt, so it's automated!

    Args:
        cards_df (DataFrame): Dataframe containing cards categorized into decks

    Returns:
        DataFrame: Dataframe containing cards categorized into decks, with added lands
    """
    deck_names = cards_df['deck_name'].unique()
    lands = {
        'W': [
            {
                'quantity':     '7',
                'card_name':    'Plains',
                'set_code':     'JMP',
                'tag':          'Land',
                'colour':       'W',
            },
            {
                'quantity':     '1',
                'card_name':    'Thriving Heath',
                'set_code':     'JMP',
                'tag':          'Land',
                'colour':       'W',
            }
        ],
        'U': [
            {
                'quantity':     '7',
                'card_name':    'Island',
                'set_code':     'JMP',
                'tag':          'Land',
                'colour':       'U',
            },
            {
                'quantity':     '1',
                'card_name':    'Thriving Isle',
                'set_code':     'JMP',
                'tag':          'Land',
                'colour':       'U',
            }
        ],
        'B': [
            {
                'quantity':     '7',
                'card_name':    'Swamp',
                'set_code':     'JMP',
                'tag':          'Land',
                'colour':       'B',
            },
            {
                'quantity':     '1',
                'card_name':    'Thriving Moor',
                'set_code':     'JMP',
                'tag':          'Land',
                'colour':       'B',
            }
        ],
        'R': [
            {
                'quantity':     '7',
                'card_name':    'Mountain',
                'set_code':     'JMP',
                'tag':          'Land',
                'colour':       'R',
            },
            {
                'quantity':     '1',
                'card_name':    'Thriving Bluff',
                'set_code':     'JMP',
                'tag':          'Land',
                'colour':       'R',
            }
        ],
        'G': [
            {
                'quantity':     '7',
                'card_name':    'Forest',
                'set_code':     'JMP',
                'tag':          'Land',
                'colour':       'G',
            },
            {
                'quantity':     '1',
                'card_name':    'Thriving Grove',
                'set_code':     'JMP',
                'tag':          'Land',
                'colour':       'G',
            }
        ],
    }

    for deck in deck_names:
        deck_df = cards_df[cards_df['deck_name'] == deck]
        colour = deck_df['colour'].iloc[0]

        if deck_df[deck_df['card_name'].isin(['Plains', 'Island', 'Swamp', 'Mountain', 'Forest'])].empty:
            lands_df = pd.DataFrame.from_dict(lands[colour])
            lands_df['deck_name'] = deck

            cards_df = pd.concat([cards_df, lands_df])


    return cards_df

def parse_card(card, format):
    """
    Parses an individual card line from input CSV

    Args:
        card (String): Individual card line from CSV

    Returns:
        Dictionary: Card line parsed into dictionary
    """
    split_card = card.split()

    card_dict = {
        'quantity': '',
        'card_name':     '',
        'colour':   '',
        'set_code': '',
        'deck_name':     '',
        'tag':      '',
    }

    card_dict['quantity'] = split_card[0].split('x')[0]

    step = 0

    if format == 'jumpstart':
        for index, word in enumerate(split_card[1:]):
            if step == 0 and '(' not in word:
                card_dict['card_name'] = card_dict['card_name'] + ' ' + word
            elif step == 0:
                step = 1
            if step == 1:
                card_dict['set_code'] = card_dict['set_code'] + ' ' + word.strip('()').upper()
                if ')' in word:
                    step = 2
                    continue

            if step == 2:
                deck_name = word.strip('[]')
                card_dict['deck_name'] = card_dict['deck_name'] + ' ' + deck_name
                if ' - ' in card_dict['deck_name']:
                    card_dict['colour'] = card_dict['deck_name'].split(' - ')[0].strip()
                    card_dict['deck_name'] = card_dict['deck_name'].split(' - ')[1].strip()
                if ']' in word:
                    step = 3
                continue

            if step == 3:
                card_dict['tag'] = word.split(',')[0].strip('^')

        for key in card_dict:
            card_dict[key] = card_dict[key].strip().replace('/', '')

        return card_dict

    else:
        for index, word in enumerate(split_card[1:]):
            if step == 0 and '(' not in word:
                card_dict['card_name'] = card_dict['card_name'] + ' ' + word
            elif step == 0:
                step = 1
            if step == 1:
                card_dict['set_code'] = card_dict['set_code'] + ' ' + word.strip('()').upper()
                if ')' in word:
                    step = 2
                    continue

        for key in card_dict:
            card_dict[key] = card_dict[key].strip().replace('/', '')

        return card_dict

def parse_decks(cards, format):
    """
    Parses an input CSV

    Args:
        cards (List): List of card lines from CSV

    Returns:
        DataFrame: All cards processed
    """
    card_list = [parse_card(card, format) for card in cards]
    cards_df = pd.DataFrame.from_dict(card_list)

    if format == 'jumpstart':
        cards_df = add_lands(cards_df)
        assert len(cards_df['deck_name'].unique()) == cards_df['quantity'].astype(int).sum() // 20, "Deck count does not match expected value (cards/20)"

    return cards_df