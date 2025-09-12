"""Tests for tournament functionality."""

import pytest
from battleship_challenge.tournament import Tournament, GameConfig, TournamentResult
from battleship_challenge.bots.random_bot import RandomBot


def test_game_config():
    """Test GameConfig creation and naming."""
    config = GameConfig(board_size=(8, 8), ships=[4, 3, 2])
    assert config.board_size == (8, 8)
    assert config.ships == [4, 3, 2]
    assert config.name == "8x8_ships4_3_2"
    
    # Test custom name
    config_named = GameConfig(board_size=(10, 10), ships=[5, 4], name="Custom")
    assert config_named.name == "Custom"


def test_tournament_init():
    """Test tournament initialization."""
    bots = ["RandomBot", "RandomBot"]
    configs = [GameConfig(board_size=(8, 8), ships=[3, 2])]
    tournament = Tournament(bots, configs, games_per_matchup=2)
    
    assert tournament.bot_names == ["RandomBot", "RandomBot"]
    assert tournament.bot_identifiers == ["RandomBot", "RandomBot_2"]
    assert len(tournament.configs) == 1
    assert tournament.games_per_matchup == 2


def test_tournament_unique_identifiers():
    """Test that duplicate bot names get unique identifiers."""
    bots = ["RandomBot", "RandomBot", "RandomBot"]
    configs = [GameConfig(board_size=(8, 8), ships=[3, 2])]
    tournament = Tournament(bots, configs)
    
    assert tournament.bot_identifiers == ["RandomBot", "RandomBot_2", "RandomBot_3"]


def test_small_tournament():
    """Test running a small tournament."""
    bots = ["RandomBot", "RandomBot"]
    configs = [GameConfig(board_size=(6, 6), ships=[3, 2])]
    tournament = Tournament(bots, configs, games_per_matchup=1)
    
    # This will test the tournament can run without errors
    results = tournament.run_tournament(verbose=False)
    
    assert isinstance(results, TournamentResult)
    assert len(results.bot_scores) == 2
    assert results.total_games == 1
    assert len(results.match_results) == 1
    
    # Check that exactly one bot won
    total_wins = sum(results.bot_scores.values())
    assert total_wins == 1