from flask import Flask, jsonify
from dotenv import load_dotenv
import threading
import multiprocessing
import time
import os

from tools.database_tools import connect
from tools.deck_tools import generate_deck_files
from tools.game_tools import run_game, parse_single_game_result
import pandas as pd

app = Flask(__name__)


load_dotenv()
DEVICE_ID = os.getenv("DEVICE_ID")
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
    update_decks(format=game['format'])
    print(f"decks updated for game {game['primary_key']}!")
    print(f"running game {game['primary_key']}...")
    game_results = run_game(
        deck1_name=game['deck1_name'],
        deck2_name=game['deck2_name'],
        deck3_name=game['deck3_name'],
        deck4_name=game['deck4_name'],
        format=game['format'],
        game_count=game['game_count']
    )
    single_result = {
        'deck1': game['deck1_name'],
        'deck2': game['deck2_name'],
        'deck3': game.get('deck3_name'),
        'deck4': game.get('deck4_name'),
        'result': game_results,
        'success': getattr(game_results, 'returncode', 0) == 0
    }
    parsed_result = parse_single_game_result(single_result)
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


def check_game_data(interval=30):
    while True:
        max_games = multiprocessing.cpu_count()
        if len(current_games) >= max_games:
            print(f"Max games running ({max_games}). Sleeping...\n")
            time.sleep(interval)
            continue

        time.sleep(interval)

        print("checking for games...")
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
            print("game found!", row[1], row[2], row[3], row[4])

            cur.execute("""
                UPDATE games
                SET device_id = %s
                WHERE primary_key = %s
            """, (DEVICE_ID, row[0]))
            conn.commit()
            print(f"game {row[0]} successfully claimed")
            t = threading.Thread(target=setup_game, args=(game,), daemon=True)
            t.start()
            current_games[row[0]] = t
        conn.close()

        print('sleeping...', end='\n\n')


if __name__ == '__main__':
    thread = threading.Thread(target=check_game_data, daemon=True)
    thread.start()
    app.run(debug=True, use_reloader=False)