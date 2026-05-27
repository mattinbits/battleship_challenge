"""Tests for BattleshipGame engine logic."""

import pytest
from battleship_challenge.game import BattleshipGame
from battleship_challenge.bots.random_bot import RandomBot
from battleship_challenge.interface import BattleshipBot, ShotResponse, ShotResult


BOARD_SIZE = (10, 10)
SHIPS = [5, 4, 3, 3, 2]

# Fixed valid placement whose lengths match SHIPS = [5, 4, 3, 3, 2]
VALID_SHIPS = [
    ((0, 0), (0, 4)),  # length 5
    ((2, 0), (2, 3)),  # length 4
    ((4, 0), (4, 2)),  # length 3
    ((6, 0), (6, 2)),  # length 3
    ((8, 0), (8, 1)),  # length 2
]


def _new_game():
    return BattleshipGame(
        RandomBot("Player1", BOARD_SIZE, SHIPS),
        RandomBot("Player2", BOARD_SIZE, SHIPS),
        BOARD_SIZE,
        SHIPS,
    )


# ── Helpers ────────────────────────────────────────────────────────────────────

class _RepeatShotBot(BattleshipBot):
    """Always fires (0, 0) — will repeat on its second turn."""

    @property
    def name(self):
        return "RepeatShotBot"

    def place_ships(self):
        return list(VALID_SHIPS)

    def take_shot(self):
        return (0, 0)

    def receive_shot_result(self, shot, result):
        pass


class _SequentialShotBot(BattleshipBot):
    """Fires squares in order (0,0), (1,0), ... — never repeats."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._x = 0
        self._y = 0

    @property
    def name(self):
        return "SequentialShotBot"

    def place_ships(self):
        return list(reversed(VALID_SHIPS))  # reversed order: [2,3,3,4,5]

    def take_shot(self):
        x, y = self._x, self._y
        self._x += 1
        if self._x >= self.board_size[0]:
            self._x = 0
            self._y += 1
        return (x, y)

    def receive_shot_result(self, shot, result):
        pass


# ── Repeat-shot tests ──────────────────────────────────────────────────────────

def test_repeat_shot_forfeits_game():
    """Bot firing the same square twice loses immediately."""
    bot1 = _RepeatShotBot("Player1", BOARD_SIZE, SHIPS)
    bot2 = RandomBot("Player2", BOARD_SIZE, SHIPS)
    game = BattleshipGame(bot1, bot2, BOARD_SIZE, SHIPS)
    assert game.play_game() == "Player2"


def test_validate_shot_rejects_repeat():
    """_validate_shot raises when the square already appears in shots_taken."""
    game = _new_game()
    with pytest.raises(ValueError, match="already been fired"):
        game._validate_shot((3, 3), [(1, 1), (3, 3)])


def test_validate_shot_accepts_new_square():
    """_validate_shot does not raise for a square not yet in shots_taken."""
    game = _new_game()
    game._validate_shot((3, 3), [(1, 1), (2, 2)])  # must not raise


def test_validate_shot_accepts_empty_history():
    """_validate_shot does not raise when shots_taken is empty."""
    game = _new_game()
    game._validate_shot((0, 0), [])


def test_validate_shot_without_history_argument():
    """_validate_shot still validates bounds when shots_taken is omitted."""
    game = _new_game()
    game._validate_shot((9, 9))  # must not raise
    with pytest.raises(ValueError):
        game._validate_shot((10, 0))


# ── Ship-placement order tests ─────────────────────────────────────────────────

def test_ship_placement_reversed_order_accepted():
    """Ships in ascending-length order [2,3,3,4,5] are accepted."""
    game = _new_game()
    game._validate_ship_placement(list(reversed(VALID_SHIPS)), "TestPlayer")


def test_ship_placement_arbitrary_permutation_accepted():
    """Any permutation of the correct ship lengths is accepted."""
    game = _new_game()
    permuted = [VALID_SHIPS[4], VALID_SHIPS[1], VALID_SHIPS[0], VALID_SHIPS[3], VALID_SHIPS[2]]
    game._validate_ship_placement(permuted, "TestPlayer")


def test_ship_placement_wrong_length_multiset_rejected():
    """Correct ship count but wrong length multiset raises ValueError."""
    game = _new_game()
    # Replace the 5-length ship with a 3-length one → lengths become [3,4,3,3,2]
    wrong = [
        ((0, 0), (0, 2)),  # length 3 — should be 5
        ((2, 0), (2, 3)),  # length 4
        ((4, 0), (4, 2)),  # length 3
        ((6, 0), (6, 2)),  # length 3
        ((8, 0), (8, 1)),  # length 2
    ]
    with pytest.raises(ValueError, match="do not match required"):
        game._validate_ship_placement(wrong, "TestPlayer")


def test_ship_placement_duplicate_lengths_rejected():
    """Two ships of the same length that exceed the required count are rejected."""
    game = _new_game()
    # Five 3-length ships instead of [5,4,3,3,2]
    five_threes = [
        ((0, 0), (0, 2)),
        ((2, 0), (2, 2)),
        ((4, 0), (4, 2)),
        ((6, 0), (6, 2)),
        ((8, 0), (8, 2)),
    ]
    with pytest.raises(ValueError, match="do not match required"):
        game._validate_ship_placement(five_threes, "TestPlayer")


def test_game_runs_with_reversed_ship_placement():
    """A complete game succeeds when a bot returns ships in reversed length order."""
    bot1 = _SequentialShotBot("Player1", BOARD_SIZE, SHIPS)
    bot2 = RandomBot("Player2", BOARD_SIZE, SHIPS)
    game = BattleshipGame(bot1, bot2, BOARD_SIZE, SHIPS)
    winner = game.play_game()
    assert winner in ("Player1", "Player2")
