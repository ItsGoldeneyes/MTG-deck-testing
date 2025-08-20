from flask import Flask, jsonify
from dotenv import load_dotenv
import threading
import multiprocessing
import time
import os
import logging

from tools.database_tools import connect
from tools.deck_tools import generate_deck_files
from tools.game_tools import run_game, parse_single_game_result
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
last_deck_update = None

def update_decks(format='jumpstart'):
    global last_deck_update

    conn, cur = connect()
    cur.execute("SELECT MAX(uploaded_on) FROM decks")
    latest_uploaded_on = cur.fetchone()[0]

    if last_deck_update is None or (latest_uploaded_on and last_deck_update < latest_uploaded_on):

        cur.execute("SELECT * FROM decks WHERE uploaded_on = (SELECT MAX(uploaded_on) FROM decks)")
        decks = cur.fetchall()
        decks_df = pd.DataFrame(decks, columns=[desc[0] for desc in cur.description])
        # print(decks_df.head())

        generate_deck_files(decks_df, output_path=f'output/{format}')
        last_deck_update = latest_uploaded_on

    conn.close()

def setup_game(game):
    logging.info(f"Starting game {game['primary_key']} with decks: {game['deck1_name']}, {game['deck2_name']}, {game.get('deck3_name')}, {game.get('deck4_name')}")

    game_results = run_game(
        deck1_name=game['deck1_name'],
        deck2_name=game['deck2_name'],
        deck3_name=game['deck3_name'],
        deck4_name=game['deck4_name'],
        format=game['format'],
        game_count=game['game_count']
    )

    logging.info(f"Game {game['primary_key']} - Return code: {getattr(game_results, 'returncode', 'N/A')}")

    if hasattr(game_results, 'stdout') and game_results.stdout:
        logging.info(f"Game {game['primary_key']} - STDOUT length: {len(game_results.stdout)} characters")
        logging.debug(f"Game {game['primary_key']} - STDOUT first 500 chars: {game_results.stdout[:500]}")

        # Ensure output/logs directory exists before writing
        os.makedirs('output/logs', exist_ok=True)
        # Save full output to file for debugging
        with open(f"output/logs/game_{game['primary_key']}_output.txt", 'w', encoding='utf-8') as f:
            f.write(f"Game {game['primary_key']} Output\n")
            f.write(f"Decks: {game['deck1_name']}, {game['deck2_name']}, {game.get('deck3_name')}, {game.get('deck4_name')}\n")
            f.write(f"Return code: {game_results.returncode}\n")
            f.write(f"STDOUT:\n{game_results.stdout}\n")
            if game_results.stderr:
                f.write(f"STDERR:\n{game_results.stderr}\n")
        logging.info(f"Game {game['primary_key']} - Full output saved to output/logs/game_{game['primary_key']}_output.txt")
    else:
        logging.warning(f"Game {game['primary_key']} - No stdout found")

    if hasattr(game_results, 'stderr') and game_results.stderr:
        logging.warning(f"Game {game['primary_key']} - STDERR: {game_results.stderr}")

    single_result = {
        'deck1': game['deck1_name'],
        'deck2': game['deck2_name'],
        'deck3': game.get('deck3_name'),
        'deck4': game.get('deck4_name'),
        'result': game_results,
        'success': getattr(game_results, 'returncode', 0) == 0
    }

    logging.info(f"Game {game['primary_key']} - Single result success: {single_result['success']}")

    parsed_result = parse_single_game_result(single_result)
    logging.info(f"Game {game['primary_key']} - Parsed result: {parsed_result}")

    print(parsed_result)

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
    deck_update_interval = 600
    last_deck_check = 0
    while True:
        now = time.time()
        if now - last_deck_check > deck_update_interval:
            logging.info("Checking if decks need update...")
            update_decks(format='jumpstart')
            last_deck_check = now

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