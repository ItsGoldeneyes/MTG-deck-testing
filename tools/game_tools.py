from threading import Lock
import subprocess
import concurrent.futures
import pandas as pd
import time
import os
import logging

# Global lock for thread-safe operations if needed
game_lock = Lock()

def run_game(deck1_name, deck2_name, deck3_name=None, deck4_name=None, game_count=1, working_dir=None, format='jumpstart'):
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
    try:
        if working_dir:
            os.chdir(working_dir)
            logging.info(f"Changed to working directory: {os.getcwd()}")

        cmd = [
            "java", "-jar", os.path.basename(os.environ.get("FORGE_JAR_PATH", "")),
            "sim", "-d",
            f"{os.path.join(format.upper(), f'{deck1_name}.dck')}",
            f"{os.path.join(format.upper(), f'{deck2_name}.dck')}",
        ]

        # Add deck3 and deck4 if provided (for 3 to 4 player games)
        if deck3_name:
            deck3_path = f"{os.path.join(format.upper(), f'{deck3_name}.dck')}"
            cmd.append(deck3_path)
            logging.info(f"Added deck3: {deck3_path}")
        if deck4_name:
            deck4_path = f"{os.path.join(format.upper(), f'{deck4_name}.dck')}"
            cmd.append(deck4_path)
            logging.info(f"Added deck4: {deck4_path}")

        cmd.extend([
            "-n", str(game_count),
            "-q"
        ])

        logging.info(f"Running command: {' '.join(cmd)}")

        game_output = subprocess.run(cmd, capture_output=True, text=True, timeout=game_count*60)

        logging.info(f"Game completed with return code: {game_output.returncode}")
        if game_output.returncode != 0:
            logging.error(f"Game failed with stderr: {game_output.stderr}")

        return game_output
    except Exception as e:
        logging.error(f"Exception during game execution: {e}")
        raise
    finally:
        os.chdir(original_cwd)
        logging.debug(f"Restored working directory: {os.getcwd()}")

def run_games_multithreaded(deck_pairs, num_games_per_pair=10, max_workers=4):
    """
    Run multiple games concurrently using ThreadPoolExecutor

    Args:
        deck_pairs (list): List of tuples containing (deck1_name, deck2_name)
        num_games_per_pair (int): Number of games to run for each deck pair
        max_workers (int): Maximum number of concurrent threads

    Returns:
        list: List of results for each game
    """
    results = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all games to the thread pool
        future_to_decks = {}

        for deck1, deck2 in deck_pairs:
            future = executor.submit(run_game, deck1, deck2, num_games_per_pair)
            future_to_decks[future] = (deck1, deck2)

        # Collect results as they complete
        for future in concurrent.futures.as_completed(future_to_decks):
            deck1, deck2 = future_to_decks[future]
            try:
                result = future.result()
                results.append({
                    'deck1': deck1,
                    'deck2': deck2,
                    'result': result,
                    'success': result.returncode == 0
                })
                print(f"Completed: {deck1} vs {deck2}")
            except Exception as exc:
                print(f"Game {deck1} vs {deck2} generated an exception: {exc}")
                results.append({
                    'deck1': deck1,
                    'deck2': deck2,
                    'result': None,
                    'success': False,
                    'error': str(exc)
                })

    return results

def run_games_batch(deck_pairs, num_games_per_pair=10, max_workers=4, batch_size=None):
    """
    Run games in batches to avoid overwhelming the system

    Args:
        deck_pairs (list): List of tuples containing (deck1_name, deck2_name)
        num_games_per_pair (int): Number of games to run for each deck pair
        max_workers (int): Maximum number of concurrent threads
        batch_size (int): Number of deck pairs to process in each batch (default: max_workers * 2)

    Returns:
        list: List of results for all games
    """
    if batch_size is None:
        batch_size = max_workers * 2

    all_results = []

    for i in range(0, len(deck_pairs), batch_size):
        batch = deck_pairs[i:i + batch_size]
        print(f"Processing batch {i//batch_size + 1}/{(len(deck_pairs) + batch_size - 1)//batch_size}")

        batch_results = run_games_multithreaded(batch, num_games_per_pair, max_workers)
        all_results.extend(batch_results)

        # Optional: Add a small delay between batches to prevent system overload
        time.sleep(0.5)

    return all_results

def get_all_deck_combinations():
    """
    Get all possible deck combinations from the output directory
    Each .dck file is a complete deck, so we create pairs of these decks to play against each other

    Returns:
        list: List of tuples containing (deck1_name, deck2_name) where each name is a complete deck file name (without .dck extension)
    """
    jumpstart_dir = os.path.join('output', 'jumpstart')
    if not os.path.exists(jumpstart_dir):
        return []

    # Get all deck file names (without .dck extension)
    deck_names = [f[:-4] for f in os.listdir(jumpstart_dir) if f.endswith('.dck')]

    # deck_names = [name for name in deck_names if 'living' in name.lower() or 'dragons' in name.lower()]

    # Create all possible combinations of decks
    deck_pairs = []
    for i, deck1 in enumerate(deck_names):
        for deck2 in deck_names[i+1:]:  # Avoid duplicates and self-matches
            deck_pairs.append((deck1, deck2))
    return deck_pairs

def get_sample_deck_combinations(num_combinations=10):
    """
    Get a sample of deck combinations for testing

    Args:
        num_combinations (int): Number of random combinations to return

    Returns:
        list: List of tuples containing (deck1_name, deck2_name)
    """
    import random
    all_combinations = get_all_deck_combinations()

    if len(all_combinations) <= num_combinations:
        return all_combinations

    return random.sample(all_combinations, num_combinations)

def evaluate_all_decks_multithreaded(num_games=10, max_workers=4):
    """
    Evaluate all deck combinations using multithreading

    Args:
        num_games (int): Number of games to run for each deck pair
        max_workers (int): Maximum number of concurrent threads

    Returns:
        list: Results from all games
    """
    deck_pairs = get_all_deck_combinations()
    print(f"Found {len(deck_pairs)} deck combinations to evaluate")

    if not deck_pairs:
        print("No deck combinations found. Make sure decks have been generated first.")
        return []

    print(f"Running {num_games} games per combination with {max_workers} workers...")
    start_time = time.time()

    results = run_games_batch(deck_pairs, num_games, max_workers)

    end_time = time.time()
    print(f"Completed in {end_time - start_time:.2f} seconds")

    # Summary statistics
    successful_games = sum(1 for r in results if r['success'])
    failed_games = len(results) - successful_games

    print(f"Results: {successful_games} successful, {failed_games} failed")

    return results

def evaluate_sample_decks_multithreaded(num_combinations=10, num_games=10, max_workers=4):
    """
    Evaluate a sample of deck combinations using multithreading (useful for testing)

    Args:
        num_combinations (int): Number of random deck combinations to test
        num_games (int): Number of games to run for each deck pair
        max_workers (int): Maximum number of concurrent threads

    Returns:
        list: Results from all games
    """
    deck_pairs = get_sample_deck_combinations(num_combinations)
    print(f"Testing {len(deck_pairs)} random deck combinations")

    if not deck_pairs:
        print("No deck combinations found. Make sure decks have been generated first.")
        return []

    print(f"Running {num_games} games per combination with {max_workers} workers...")
    start_time = time.time()

    results = run_games_batch(deck_pairs, num_games, max_workers)

    end_time = time.time()
    print(f"Completed in {end_time - start_time:.2f} seconds")

    # Summary statistics
    successful_games = sum(1 for r in results if r['success'])
    failed_games = len(results) - successful_games

    print(f"Results: {successful_games} successful, {failed_games} failed")

    return results

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

# Single-game result parser
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

    logging.info(f"Final parsed result: {result_dict}")
    total_wins = sum(win_counts)
    total_turns = len(turn_counts)
    logging.info(f"Total wins found: {total_wins}, Total turn counts found: {total_turns}")

    return result_dict