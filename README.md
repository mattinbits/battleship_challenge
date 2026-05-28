# Battleship Challenge 🚢

A competitive coding challenge where teams build AI bots to play Battleship against each other. May the best algorithm win!

## 🎯 Challenge Overview

In this challenge, you'll implement a bot that can:
1. **Place ships** on a game board
2. **Hunt** the opponent's ships  
3. **Make decisions** based on shot results

Your bot will compete against other teams' bots in head-to-head matches. The bot that consistently wins more games will be crowned the champion!

## 🚀 Getting Started

### Prerequisites
- Python 3.11 or higher
- A competitive spirit! 💪

### Setup
1. **Clone and navigate to the project:**
   ```bash
   cd battleship_challenge
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python3 -m venv env  # Use 'python' if 'python3' is not available
   source env/bin/activate  # On Windows: env\Scripts\activate
   ```

3. **Install the project in editable mode:**
   ```bash
   pip install -e ".[test]"
   ```

4. **Test the installation:**
   ```bash
   battleship_challenge RandomBot RandomBot --visualize
   ```

You should see two random bots battling it out with a visual display!

## 🤖 Creating Your Bot

### Step 1: Create Your Bot File
Create a new Python file for your bot (e.g., `my_awesome_bot.py`):

```python
from battleship_challenge.interface import BattleshipBot, ShotResponse
import random

class MyAwesomeBot(BattleshipBot):
    def __init__(self, player_id, board_size, ships):
        super().__init__(player_id, board_size, ships)
        # Initialize any data structures you need
        self.shots_taken = set()
        self.hits = set()
        self.target_queue = []
    
    def place_ships(self):
        """Implement your ship placement strategy here."""
        # Return list of ships as (start_pos, end_pos) tuples
        # Example: [((0,0), (0,4)), ((2,1), (4,1))]
        pass
    
    def take_shot(self):
        """Implement your targeting strategy here."""
        # Return (x, y) coordinates to shoot at
        pass
    
    def receive_shot_result(self, shot, result):
        """Process the result of your shot."""
        # Update your internal state based on the result
        pass
```

### Step 2: Implement the Interface Methods

#### `place_ships()` → List[Tuple[Tuple[int, int], Tuple[int, int]]]
Place your ships on the board. Return a list where each ship is represented as `((start_x, start_y), (end_x, end_y))`.

**Example:**
```python
def place_ships(self):
    # Place a 5-ship horizontally at row 0
    # Place a 3-ship vertically at column 2
    return [
        ((0, 0), (4, 0)),  # 5-ship: (0,0) to (4,0)  
        ((2, 2), (2, 4)),  # 3-ship: (2,2) to (2,4)
    ]
```

#### `take_shot()` → Tuple[int, int]
Choose where to shoot. Return `(x, y)` coordinates. Firing at a square you've already shot is an illegal move and forfeits the game.

#### `receive_shot_result(shot, result)`
Process the result of your shot to update your strategy.

**Result types:**
- `ShotResult.MISS` - You missed
- `ShotResult.HIT` - You hit a ship  
- `ShotResult.SUNK` - You sank a ship (includes ship length)

### Step 3: Test Your Bot
```bash
# Test against RandomBot
battleship_challenge MyAwesomeBot RandomBot --visualize

# Test on different board sizes
battleship_challenge MyAwesomeBot RandomBot --board-size 8x8 --ships 4,3,2

# Run multiple games quickly (no visualization)
battleship_challenge MyAwesomeBot RandomBot
```

## 🎮 Running Games

### Command Line Options
```bash
battleship_challenge <bot1> <bot2> [options]

Options:
  --board-size WxH     Board dimensions (default: 10x10)
  --ships A,B,C        Ship lengths (default: 5,4,3,3,2)
  --visualize          Show real-time game board
  --verbose            Detailed output
```

### Examples
```bash
# Visual game with default settings  
battleship_challenge MyBot RandomBot --visualize

# Tournament-style quick games
battleship_challenge TeamA_Bot TeamB_Bot

# Custom rules
battleship_challenge MyBot RandomBot --board-size 12x12 --ships 6,5,4,3,2,2

# Debug mode
battleship_challenge MyBot RandomBot --verbose --visualize
```

## 📊 Game Rules

### Standard Rules
- **Board:** 10×10 grid (customizable)
- **Ships:** 5 ships with lengths [5, 4, 3, 3, 2] (customizable)
- **Placement:** Ships must be horizontal or vertical, no overlaps
- **Turns:** Players alternate shooting until all ships are sunk
- **Winner:** First player to sink all opponent ships

### Coordinate System
- Origin (0,0) is top-left corner
- X increases rightward, Y increases downward
- Example: (3,2) means column 3, row 2

## 🏆 Competition Format

During the event, bots will compete in:
1. **Round-robin** or **bracket** tournament
2. **Multiple game matches** to reduce randomness
3. **Different board configurations** to test adaptability

## 🐛 Debugging Tips

### Common Issues
- **Invalid ship placement** - Check bounds and overlaps
- **Repeated shots** - Track shots you've taken
- **Index errors** - Remember coordinates are (x,y) not (row,col)

### Debugging Tools
```python
# Add logging to see what your bot is thinking
import logging
logging.basicConfig(level=logging.DEBUG)

def take_shot(self):
    shot = self.calculate_best_shot()
    logging.debug(f"Shooting at {shot}")
    return shot
```

### Testing Strategies
```bash
# Test against yourself
battleship_challenge MyBot MyBot --visualize

# Test different scenarios
battleship_challenge MyBot RandomBot --board-size 6x6 --ships 3,2
```

## 📁 Project Structure
```
battleship_challenge/
├── src/battleship_challenge/
│   ├── interface.py      # Bot interface definition
│   ├── game.py          # Game engine
│   ├── main.py          # Command line runner
│   └── bots/
│       ├── random_bot.py # Example bot implementation
│       └── __init__.py
├── tests/               # Test files
├── env/                # Virtual environment  
├── pyproject.toml      # Project configuration
└── README.md           # This file
```

## 🤔 Frequently Asked Questions

**Q: Can I use external libraries?**
A: Stick to Python standard library for the competition. Focus on algorithms, not dependencies.

**Q: How do I handle the different ship lengths?**
A: The `self.ships` list tells you what ships to place: `[5, 4, 3, 3, 2]` means place one 5-length ship, one 4-length ship, two 3-length ships, and one 2-length ship.

**Q: What if my bot crashes?**
A: Fix the bug! The game engine will report errors. Use `--verbose` mode to debug.

**Q: Can I see my opponent's board?**
A: No! This is hidden information. You only know the results of your own shots.

**Q: How do I make my bot faster?**
A: Avoid expensive operations in `take_shot()` — it's called once per turn.

## 🏅 Good Luck!

Remember: shooting the same square twice is an illegal move and will forfeit the game — make sure your bot tracks its shots!

May your algorithms be swift and your aim be true! 🎯

---

*Built with ❤️ for competitive programming enthusiasts*