import types
from unittest.mock import patch

import pytest

from battleship_challenge.main import discover_bot_class
from battleship_challenge.bots.random_bot import RandomBot
from battleship_challenge.interface import BattleshipBot


def test_discover_bot_class():
    """Test bot discovery functionality."""
    bot_class = discover_bot_class("RandomBot")
    assert bot_class == RandomBot
    assert issubclass(bot_class, RandomBot)


def test_discover_bot_class_collision():
    """Two modules that both expose a class of the same name raise an informative ImportError."""

    def _make_bot_class():
        return type("CollisionBot", (BattleshipBot,), {
            "name": property(lambda self: "CollisionBot"),
            "place_ships": lambda self: [],
            "take_shot": lambda self: (0, 0),
            "receive_shot_result": lambda self, s, r: None,
        })

    mod_a = types.ModuleType("battleship_challenge.bots.fake_a")
    mod_a.CollisionBot = _make_bot_class()
    mod_b = types.ModuleType("battleship_challenge.bots.fake_b")
    mod_b.CollisionBot = _make_bot_class()

    with patch("pkgutil.iter_modules", return_value=[
        (None, "battleship_challenge.bots.fake_a", False),
        (None, "battleship_challenge.bots.fake_b", False),
    ]):
        with patch("importlib.import_module", side_effect=[mod_a, mod_b]):
            with pytest.raises(ImportError, match="Multiple bot classes named 'CollisionBot'"):
                discover_bot_class("CollisionBot")


def test_discover_bot_class_single_match_no_error():
    """A unique class name is returned without error even when multiple modules are searched."""

    def _make_bot_class(name):
        return type(name, (BattleshipBot,), {
            "name": property(lambda self: name),
            "place_ships": lambda self: [],
            "take_shot": lambda self: (0, 0),
            "receive_shot_result": lambda self, s, r: None,
        })

    mod_a = types.ModuleType("battleship_challenge.bots.fake_a")
    mod_a.UniqueBotA = _make_bot_class("UniqueBotA")
    mod_b = types.ModuleType("battleship_challenge.bots.fake_b")
    mod_b.UniqueBotB = _make_bot_class("UniqueBotB")

    with patch("pkgutil.iter_modules", return_value=[
        (None, "battleship_challenge.bots.fake_a", False),
        (None, "battleship_challenge.bots.fake_b", False),
    ]):
        with patch("importlib.import_module", side_effect=[mod_a, mod_b]):
            result = discover_bot_class("UniqueBotA")
            assert result is mod_a.UniqueBotA