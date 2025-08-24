### Overview

This tool is designed to enable the playtesting of decks using [Forge](https://github.com/Card-Forge/forge).

### Requirements

- [Forge](https://github.com/Card-Forge/forge) must be installed and configured.
- An environment variable `FORGE_PATH` must be set to the path where Forge decks are stored (e.g., `C:\Users\USER\AppData\Roaming\Forge\decks\constructed\`).
- An Archidekt decklist in [this format](https://archidekt.com/decks/10786371/jumpstart), saved as a txt to `input/jumpstart.txt` with quantity, set code, categories, and colour tag data.

### Output

- Individual `.dck` files for each deck in the `output/` directory.
- Games run through `worker.py`