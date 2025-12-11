from flask import Flask, jsonify
from dotenv import load_dotenv
import threading
import multiprocessing
import time
import os
import logging

from packages.database_tools import connect
from packages.deck_tools import generate_deck_files
from packages.game_tools import run_game, parse_single_game_result
import pandas as pd

# Configure logging
os.makedirs('output/logs', exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('output/logs/worker.log'),
        logging.StreamHandler()
    ]
)

app = Flask(__name__)
logger = logging.getLogger(__name__)

load_dotenv()
DEVICE_ID = os.getenv("DEVICE_ID")
FORGE_JAR_PATH = os.getenv("FORGE_JAR_PATH")

# Log environment setup
logging.info(f"Device ID: {DEVICE_ID}")
logging.info(f"Forge JAR Path: {FORGE_JAR_PATH}")

if not FORGE_JAR_PATH:
    logging.error("FORGE_JAR_PATH environment variable not set!")
if not DEVICE_ID:
    logging.error("DEVICE_ID environment variable not set!")

current_games = {}

def update_decks(
    decks = [],
    format='constructed'
    ):
    """
    Update local deck files by pulling from database
    Args:
        decks (list): List of deck names to update. If empty, update all decks.
        format (str): Game format (constructed, commander, jumpstart)
    """

    conn, cur = connect()
    # TODO: Check if decks need to be updated
    # cur.execute(f"""
    #             SELECT MAX(uploaded_on) FROM decks
    #             WHERE format = {format}
    #             """)
    # latest_uploaded_on = cur.fetchone()[0]

    query = f"""
        SELECT * FROM decks
        WHERE format = '{format}'
        """
    if decks:
        placeholders = ','.join(['%s'] * len(decks))
        query += f"\nAND deck_name IN ({placeholders})"
        cur.execute(query, decks)
    else:
        cur.execute(query)

    rows = cur.fetchall()
    decks_df = pd.DataFrame(rows, columns=[desc[0] for desc in cur.description])

    if format == 'jumpstart':
        if len(decks) != 4:
            raise ValueError("Jumpstart games must include exactly 4 decks (2 half decks)")

        mask1 = (decks_df['deck_name'] == decks[0]) | (decks_df['deck_name'] == decks[1])
        decks_df.loc[mask1, 'deck_name'] = str(decks[0]) + ' ' + str(decks[1])

        mask2 = (decks_df['deck_name'] == decks[2]) | (decks_df['deck_name'] == decks[3])
        decks_df.loc[mask2, 'deck_name'] = str(decks[2]) + ' ' + str(decks[3])
        decks = (
            decks[0] + ' ' + decks[1],
            decks[2] + ' ' + decks[3],
            None,
            None
            )

    generate_deck_files(decks_df, format)

    conn.close()

    return decks

def setup_game(game):
    logging.info(f"Starting game {game['primary_key']} with decks: {game['deck1_name']}, {game['deck2_name']}, {game.get('deck3_name')}, {game.get('deck4_name')}")

    updated_decks = update_decks(
        [
            game['deck1_name'],
            game['deck2_name'],
            game['deck3_name'],
            game['deck4_name'],
        ],
        game['format'],
    )

    # Update deck names with modified names (usually running Jumpstart half decks)
    if game['format'] == 'jumpstart':
        game['deck1_name'] = updated_decks[0]
        game['deck2_name'] = updated_decks[1]
        game['deck3_name'] = updated_decks[2]
        game['deck4_name'] = updated_decks[3]

        # Change format to constructed so game doesn't look in Jumpstart subdirectory
        game['format'] = 'constructed'



    game['results'] = run_game(
        deck1_name=game['deck1_name'],
        deck2_name=game['deck2_name'],
        deck3_name=game['deck3_name'],
        deck4_name=game['deck4_name'],
        format=game['format'],
        game_count=game['game_count']
    )

    logging.info(f"Game {game['primary_key']} - Return code: {getattr(game['results'], 'returncode', 'N/A')}")

    if hasattr(game['results'], 'stdout') and game['results'].stdout:
        logging.info(f"Game {game['primary_key']} - STDOUT length: {len(game['results'].stdout)} characters")
        logging.debug(f"Game {game['primary_key']} - STDOUT first 500 chars: {game['results'].stdout[:500]}")

        # Ensure output/logs directory exists before writing
        os.makedirs('output/logs', exist_ok=True)
        # Save full output to file for debugging
        with open(f"output/logs/game_{game['primary_key']}_output.txt", 'w', encoding='utf-8') as f:
            f.write(f"Game {game['primary_key']} Output\n")
            f.write(f"Decks: {game['deck1_name']}, {game['deck2_name']}, {game.get('deck3_name')}, {game.get('deck4_name')}\n")
            f.write(f"Return code: {game['results'].returncode}\n")
            f.write(f"STDOUT:\n{game['results'].stdout}\n")
            if game['results'].stderr:
                f.write(f"STDERR:\n{game['results'].stderr}\n")
        logging.info(f"Game {game['primary_key']} - Full output saved to output/logs/game_{game['primary_key']}_output.txt")
    else:
        logging.warning(f"Game {game['primary_key']} - No stdout found")

    # if hasattr(game['results'], 'stderr') and game['results'].stderr:
    #     logging.warning(f"Game {game['primary_key']} - STDERR: {game['results'].stderr}")

    single_result = {
        'deck1': game['deck1_name'],
        'deck2': game['deck2_name'],
        'deck3': game.get('deck3_name'),
        'deck4': game.get('deck4_name'),
        'result': game['results'],
        'success': getattr(game['results'], 'returncode', 0) == 0
    }

    logging.info(f"Game {game['primary_key']} - Single result success: {single_result['success']}")

    parsed_result = parse_single_game_result(single_result)
    logging.info(f"Game {game['primary_key']} - Parsed result: {parsed_result}")

    # print(parsed_result)

    conn, cur = connect()
    cur.execute("""
        UPDATE games
        SET deck1_wins = %s,
            deck2_wins = %s,
            deck3_wins = %s,
            deck4_wins = %s,
            turn_counts = %s,
            finished_on = NOW()
        WHERE primary_key = %s
    """, (
        parsed_result.get('deck1_wins', 0),
        parsed_result.get('deck2_wins', 0),
        parsed_result.get('deck3_wins', 0),
        parsed_result.get('deck4_wins', 0),
        str(parsed_result.get('turn_counts', [])),
        game['primary_key']
    ))
    conn.commit()
    conn.close()
    # Remove from current_games after finishing
    current_games.pop(game['primary_key'], None)


def check_game_data(interval=10):
    while True:
        max_games = multiprocessing.cpu_count()
        if len(current_games) >= max_games:
            logging.info(f"Max games running ({max_games}). Sleeping...")
            time.sleep(30)
            continue

        time.sleep(interval)

        logging.info("Checking for games...")
        conn, cur = connect()
        slots = max_games - len(current_games)
        cur.execute(f"""
            SELECT primary_key,
                   deck1_name,
                   deck2_name,
                   deck3_name,
                   deck4_name,
                   created_on,
                   format,
                   game_count
            FROM games
            WHERE device_id IS NULL
            ORDER BY created_on ASC
            LIMIT {slots}
        """)
        rows = cur.fetchall()
        logging.info(f"Found {len(rows)} available games to process")

        for row in rows:
            game = {
                "primary_key": row[0],
                "deck1_name": row[1],
                "deck2_name": row[2],
                "deck3_name": row[3],
                "deck4_name": row[4],
                "created_on": row[5],
                "format": row[6],
                "game_count": row[7]
            }
            logging.info(f"Processing game {row[0]}: {row[1]} vs {row[2]} vs {row[3]} vs {row[4]} ({row[7]} games)")

            cur.execute("""
                UPDATE games
                SET device_id = %s
                WHERE primary_key = %s
            """, (DEVICE_ID, row[0]))
            conn.commit()
            logging.info(f"Game {row[0]} successfully claimed by device {DEVICE_ID}")

            t = threading.Thread(target=setup_game, args=(game,), daemon=True)
            t.start()
            current_games[row[0]] = t
        conn.close()

        if rows:
            logging.info(f"Started {len(rows)} new games. Currently running: {len(current_games)} games")
        logging.debug('Sleeping before next check...')


if __name__ == '__main__':
    thread = threading.Thread(target=check_game_data, daemon=True)
    thread.start()
    app.run(debug=True, use_reloader=False)