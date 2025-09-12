from battleship_challenge.main import discover_bot_class
from battleship_challenge.bots.random_bot import RandomBot


def test_discover_bot_class():
    """Test bot discovery functionality."""
    bot_class = discover_bot_class("RandomBot")
    assert bot_class == RandomBot
    assert issubclass(bot_class, RandomBot)