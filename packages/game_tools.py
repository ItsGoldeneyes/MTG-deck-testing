import pandas as pd
import subprocess
from datetime import datetime
import uuid
import os
import io
import logging
from packages.database_tools import conn, cur
from packages.deck_tools import fetch_deck_versions


def create_game(deck_versions,
                format='constructed',
                num_games=1,
                print_decks=False):
    """_summary_

    Args:
        deck_versions (List): List of deck_version_ids
        format (str): Game format. Defaults to 'constructed'.
        num_games (int): Number of games in job. Defaults to 1.
        print_decks (bool): Print available decks for a format without creating a game. Defaults to False.
    """

    # Ensure all variables have valid values
    valid_formats = ['constructed', 'commander', 'jumpstart']
    if format not in valid_formats:
        raise ValueError(f"Invalid format '{format}'. Valid options are: {', '.join(valid_formats)}.")

    # Retrieve unique deck names from database for the specified format
    decks = fetch_deck_versions(format)

    # Print decks if argument is true
    if print_decks == True:
        print(decks)
        return False

    # Check decks against deck_names
    selected_decks = [d.strip() for d in deck_versions.split(',')]
    missing_decks = set(selected_decks) - set(str(v) for v in decks.keys())
    if missing_decks:
        raise ValueError(f"Deck(s) not found: {', '.join(missing_decks)}")

    if format == 'commander' or format == 'jumpstart':
        player_count = 4
        assert len(selected_decks) == 4, f"{format} games require four decks, to be paired as two half decks"
    else:
        player_count = 2
        assert len(selected_decks) == 2, f"{format} games require two decks"

    # Assign deck names
    player_dict = {}
    for i in range(player_count):
        player_dict[f'deck{i+1}_id'] = selected_decks[i]
    # Fill remaining with None if less than 4 players
    for i in range(player_count, 4):
        player_dict[f'deck{i+1}_id'] = None

    games_df = pd.DataFrame([player_dict])

    games_df.insert(0, 'primary_key', [str(uuid.uuid4()) for _ in range(len(games_df))])
    games_df['job_id'] = str(uuid.uuid4())
    games_df['game_count'] = num_games
    games_df['deck1_wins'] = [0] * len(games_df)
    games_df['deck2_wins'] = [0] * len(games_df)
    games_df['deck3_wins'] = [0] * len(games_df)
    games_df['deck4_wins'] = [0] * len(games_df)
    games_df['turn_counts'] = [[]] * len(games_df)
    games_df['device_id'] = [None] * len(games_df)
    games_df['format'] = format
    games_df['created_on'] = datetime.now().isoformat()
    games_df['finished_on'] = [None] * len(games_df)

    print(games_df.head())

    # Prepare a CSV buffer from the DataFrame
    csv_buffer = io.StringIO()
    games_df.to_csv(csv_buffer, index=False, header=False, sep='\t', na_rep='\\N')
    csv_buffer.seek(0)

    cur.copy_from(csv_buffer, 'games', sep='\t')
    conn.commit()
    print("Successfully uploaded game to database")

    cur.close()
    conn.close()

def run_game(deck1_name,
             deck2_name,
             deck3_name=None,
             deck4_name=None,
             game_count=1,
             working_dir=None,
             format='constructed',
             ):
    """
    Run a single game between two to four decks

    Args:
        deck1_name (str): Name of the first deck
        deck2_name (str): Name of the second deck
        deck3_name (str, optional): Name of the third deck
        deck4_name (str, optional): Name of the fourth deck
        game_count (int): Number of games to run (default 1)
        working_dir (str): Working directory for the Java process

    Returns:
        subprocess.CompletedProcess: Game output
    """
    if working_dir is None:
        working_dir = os.path.dirname(os.environ.get("FORGE_JAR_PATH", ""))

    logging.info(f"Running game: {deck1_name} vs {deck2_name} vs {deck3_name} vs {deck4_name}")
    logging.info(f"Game count: {game_count}, Format: {format}")
    logging.info(f"Working directory: {working_dir}")
    original_cwd = os.getcwd()
    # logging.info("start try")
    try:
        if working_dir:
            # logging.info("working dir:", working_dir)
            os.chdir(working_dir)
            logging.info(f"Changed to working directory: {os.getcwd()}")
        # logging.info("creating deck paths")
        # deck1_path = os.path.join(format.upper(), f'{deck1_name}.dck')
        # deck2_path = os.path.join(format.upper(), f'{deck2_name}.dck')
        logging.info("creating cmd")
        cmd = [
            "java", "-jar", os.path.basename(os.environ.get("FORGE_JAR_PATH", "")),
            "sim", "-d",
            deck1_name,
            deck2_name,
        ]
        logging.info(f"Added deck1: {deck1_name}")
        logging.info(f"Added deck2: {deck2_name}")

        # Add deck3 and deck4 if provided (for 3 to 4 player games)
        if deck3_name:
            cmd.append(deck3_name)
        if deck4_name:
            cmd.append(deck4_name)

        # Old logic for when game mode was Jumpstart
        # if deck3_name:
        #     # deck3_path = os.path.join(format.upper(), f'{deck3_name}.dck')
        #     deck3_path = deck3_name
        #     cmd.append(deck3_path)
        #     logging.info(f"Added deck3: {deck3_path}")
        # if deck4_name:
        #     # deck4_path = os.path.join(format.upper(), f'{deck4_name}.dck')
        #     deck4_path = deck4_name
        #     cmd.append(deck4_path)
        #     logging.info(f"Added deck4: {deck4_path}")


        cmd.extend([
            "-n", str(game_count),
            "-q"
        ])

        logging.info(f"Running command: {' '.join(cmd)}")

        game_output = subprocess.run(cmd, capture_output=True, text=True, timeout=game_count*120)
        logging.info("Game subprocess completed")
        # logging.info(game_output)
        # logging.info(f"Game completed with return code: {game_output.returncode}")
        if game_output.returncode != 0:
            logging.error(f"Game failed with stderr: {game_output.stderr}")

        return game_output
    except Exception as e:
        logging.error(f"Exception during game execution: {e}")
        raise
    finally:
        os.chdir(original_cwd)
        logging.debug(f"Restored working directory: {os.getcwd()}")

def parse_game_results(results):
    """
    Parse game results to extract win rates and statistics, creating one row per deck

    Args:
        results (list): Results from run_games_multithreaded or run_games_batch

    Returns:
        pandas.DataFrame: DataFrame with one row per deck including wins, winrate, and turn count statistics
    """
    from statistics import mode, median

    # First, parse individual game results
    game_data = []

    for result in results:
        if result['success'] and result['result']:
            output = result['result'].stdout
            lines = output.strip().split('\n')

            wins_deck1 = 0
            wins_deck2 = 0
            total_games = 0
            turn_counts = []

            for line in lines:
                if 'game outcome: turn' in line.lower():
                    try:
                        turn_count = int(line.lower().split()[-1])
                        turn_counts.append(turn_count)
                    except (ValueError, IndexError):
                        pass

                if 'won!' in line.lower():
                    total_games += 1
                    if result['deck1'].lower() in line.lower():
                        wins_deck1 += 1
                    elif result['deck2'].lower() in line.lower():
                        wins_deck2 += 1

            # Add data for each deck in this matchup
            if total_games > 0:
                avg_turns = sum(turn_counts) / len(turn_counts) if turn_counts else 0
                median_turns = median(turn_counts) if turn_counts else 0
                try:
                    mode_turns = mode(turn_counts) if turn_counts else 0
                except:
                    mode_turns = turn_counts[0] if turn_counts else 0

                # Add deck1 data
                game_data.append({
                    'deck': result['deck1'],
                    'wins': wins_deck1,
                    'losses': wins_deck2,
                    'total_games': total_games,
                    'avg_turns': avg_turns,
                    'median_turns': median_turns,
                    'mode_turns': mode_turns
                })

                # Add deck2 data
                game_data.append({
                    'deck': result['deck2'],
                    'wins': wins_deck2,
                    'losses': wins_deck1,
                    'total_games': total_games,
                    'avg_turns': avg_turns,
                    'median_turns': median_turns,
                    'mode_turns': mode_turns
                })

    if not game_data:
        return pd.DataFrame()

    # Convert to DataFrame for easier aggregation
    df = pd.DataFrame(game_data)

    # Aggregate by deck name
    deck_summary = df.groupby('deck').agg({
        'wins': 'sum',
        'losses': 'sum',
        'total_games': 'sum',
        'avg_turns': 'mean',
        'median_turns': 'mean',
        'mode_turns': 'mean'
    }).reset_index()

    # Calculate win rate
    deck_summary['winrate'] = deck_summary['wins'] / deck_summary['total_games']
    deck_summary['winrate'] = deck_summary['winrate'].round(4)

    # Round turn statistics
    deck_summary['avg_turns'] = deck_summary['avg_turns'].round(2)
    deck_summary['median_turns'] = deck_summary['median_turns'].round(2)
    deck_summary['mode_turns'] = deck_summary['mode_turns'].round(2)

    # Sort by win rate (descending)
    deck_summary = deck_summary.sort_values('winrate', ascending=False).reset_index(drop=True)

    # Reorder columns for better readability
    deck_summary = deck_summary[['deck', 'wins', 'losses', 'total_games', 'winrate',
                                'avg_turns', 'median_turns', 'mode_turns']]

    print(f"\nDeck Performance Summary:")
    print(f"Total decks analyzed: {len(deck_summary)}")
    print(f"Best performing deck: {deck_summary.iloc[0]['deck']} ({deck_summary.iloc[0]['winrate']:.2%} win rate)")
    print(f"Worst performing deck: {deck_summary.iloc[-1]['deck']} ({deck_summary.iloc[-1]['winrate']:.2%} win rate)")

    return deck_summary

def parse_single_game_result(result):
    """
    Parse a single game result dict (as used in worker.py) and return a dict with deck win counts and turn counts.

    Args:
        result (dict): Should have keys 'deck1', 'deck2', 'deck3', 'deck4', 'result', 'success'

    Returns:
        dict: {deck1_wins, deck2_wins, deck3_wins, deck4_wins, turn_counts}
    """
    logging.info(f"Parsing game result - Success: {result.get('success')}")

    if not result.get('success') or not result.get('result'):
        logging.warning("Game result marked as unsuccessful or no result object found")
        return {
            'deck1_wins': 0,
            'deck2_wins': 0,
            'deck3_wins': 0,
            'deck4_wins': 0,
            'turn_counts': []
        }

    output = result['result'].stdout
    logging.info(f"Game output length: {len(output) if output else 0} characters")

    if not output or not output.strip():
        logging.warning("Game stdout is empty or whitespace only")
        return {
            'deck1_wins': 0,
            'deck2_wins': 0,
            'deck3_wins': 0,
            'deck4_wins': 0,
            'turn_counts': []
        }

    lines = output.strip().split('\n')
    logging.info(f"Game output has {len(lines)} lines")

    deck_names = [result.get('deck1'), result.get('deck2'), result.get('deck3'), result.get('deck4')]
    logging.info(f"Deck names: {deck_names}")

    win_counts = [0, 0, 0, 0]
    turn_counts = []

    for i, line in enumerate(lines):
        if 'game outcome: turn' in line.lower():
            try:
                turn_count = int(line.lower().split()[-1])
                turn_counts.append(turn_count)
                logging.debug(f"Found turn count: {turn_count} from line: {line.strip()}")
            except (ValueError, IndexError) as e:
                logging.warning(f"Failed to parse turn count from line: {line.strip()} - Error: {e}")
                pass
        if 'won!' in line.lower():
            logging.debug(f"Found win line: {line.strip()}")
            for j, name in enumerate(deck_names):
                if name and name.lower() in line.lower():
                    win_counts[j] += 1
                    logging.debug(f"Win credited to deck {j} ({name})")
                    break
            else:
                logging.warning(f"Win line found but no deck name matched: {line.strip()}")

    result_dict = {
        'deck1_wins': win_counts[0],
        'deck2_wins': win_counts[1],
        'deck3_wins': win_counts[2],
        'deck4_wins': win_counts[3],
        'turn_counts': turn_counts
    }

    # logging.info(f"Final parsed result: {result_dict}")
    total_wins = sum(win_counts)
    total_turns = len(turn_counts)
    # logging.info(f"Total wins found: {total_wins}, Total turn counts found: {total_turns}")

    return result_dict