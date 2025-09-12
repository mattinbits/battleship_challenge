"""
Tournament system for battleship bot competitions.

This module manages tournaments where multiple bots compete against each other
across different game configurations.
"""

import itertools
from dataclasses import dataclass
from typing import List, Tuple, Dict, Type
from .interface import BattleshipBot
from .game import BattleshipGame
from .main import discover_bot_class, create_bot_instances


@dataclass
class GameConfig:
    """Configuration for a single game type in the tournament."""
    board_size: Tuple[int, int]
    ships: List[int]
    name: str = ""
    
    def __post_init__(self):
        if not self.name:
            self.name = f"{self.board_size[0]}x{self.board_size[1]}_ships{'_'.join(map(str, self.ships))}"


@dataclass
class MatchResult:
    """Result of a single match between two bots."""
    bot1_id: str
    bot2_id: str
    config_name: str
    winner_id: str
    game_number: int


@dataclass
class TournamentResult:
    """Overall tournament results."""
    bot_scores: Dict[str, int]  # bot_id -> total wins
    match_results: List[MatchResult]
    configs: List[GameConfig]
    total_games: int


class Tournament:
    """Manages a tournament between multiple bots across multiple configurations."""
    
    def __init__(self, bot_names: List[str], configs: List[GameConfig], games_per_matchup: int = 10):
        """Initialize the tournament.
        
        Args:
            bot_names: List of bot class names to compete
            configs: List of game configurations to play
            games_per_matchup: Number of games each pair plays per configuration (default: 10)
        """
        # Create unique identifiers for bots when there are duplicates
        self.bot_identifiers = []
        bot_counts = {}
        for bot_name in bot_names:
            if bot_name in bot_counts:
                bot_counts[bot_name] += 1
                unique_id = f"{bot_name}_{bot_counts[bot_name]}"
            else:
                bot_counts[bot_name] = 1
                unique_id = bot_name
            self.bot_identifiers.append(unique_id)
        
        self.bot_names = bot_names  # Original class names
        self.configs = configs
        self.games_per_matchup = games_per_matchup
        self.bot_classes: Dict[str, Type[BattleshipBot]] = {}
        self.match_results: List[MatchResult] = []
        
    def load_bots(self):
        """Load all bot classes."""
        print("Loading bot classes...")
        for i, bot_name in enumerate(self.bot_names):
            try:
                self.bot_classes[self.bot_identifiers[i]] = discover_bot_class(bot_name)
                print(f"  ✓ {self.bot_identifiers[i]} ({bot_name})")
            except ImportError as e:
                raise ImportError(f"Failed to load bot '{bot_name}': {e}")
    
    def run_tournament(self, verbose: bool = False) -> TournamentResult:
        """Run the complete tournament.
        
        Args:
            verbose: Whether to print detailed progress information
            
        Returns:
            TournamentResult with all match results and final scores
        """
        self.load_bots()
        
        # Calculate total number of games
        num_bot_pairs = len(list(itertools.combinations(self.bot_names, 2)))
        total_games = num_bot_pairs * len(self.configs) * self.games_per_matchup
        
        print(f"\nStarting tournament with {len(self.bot_names)} bots, {len(self.configs)} configs")
        print(f"Each bot pair will play {self.games_per_matchup} games per config")
        print(f"Total games to play: {total_games}")
        print("-" * 60)
        
        game_count = 0
        
        # Play all bot combinations in all configurations
        for config in self.configs:
            print(f"\nPlaying configuration: {config.name}")
            print(f"Board: {config.board_size[0]}x{config.board_size[1]}, Ships: {config.ships}")
            
            for bot1_id, bot2_id in itertools.combinations(self.bot_identifiers, 2):
                if verbose:
                    print(f"  {bot1_id} vs {bot2_id}:")
                
                # Play the specified number of games, alternating who goes first
                for game_num in range(self.games_per_matchup):
                    game_count += 1
                    
                    # Alternate who goes first by swapping bot order every other game
                    if game_num % 2 == 0:
                        first_bot_id, second_bot_id = bot1_id, bot2_id
                    else:
                        first_bot_id, second_bot_id = bot2_id, bot1_id
                    
                    # Create fresh bot instances for this game
                    first_bot_class = self.bot_classes[first_bot_id]
                    second_bot_class = self.bot_classes[second_bot_id]
                    first_bot, second_bot = create_bot_instances(
                        first_bot_class, second_bot_class, 
                        config.board_size, config.ships
                    )
                    
                    # Play the game
                    game = BattleshipGame(
                        first_bot, second_bot, 
                        config.board_size, config.ships, 
                        visualize=False
                    )
                    winner_id = game.play_game()
                    
                    # Record the result
                    result = MatchResult(
                        bot1_id=bot1_id,
                        bot2_id=bot2_id,
                        config_name=config.name,
                        winner_id=self._get_original_bot_id(winner_id, first_bot_id, second_bot_id),
                        game_number=game_num + 1
                    )
                    self.match_results.append(result)
                    
                    if verbose:
                        winner_display = self._get_original_bot_id(winner_id, first_bot_id, second_bot_id)
                        print(f"    Game {game_num + 1}: {winner_display} wins")
                    
                    # Progress indicator
                    if not verbose and game_count % 10 == 0:
                        print(f"  Progress: {game_count}/{total_games} games completed")
        
        print(f"\nTournament completed! {total_games} games played.")
        return self._calculate_final_results()
    
    def _get_original_bot_id(self, winner_player_id: str, first_bot_id: str, second_bot_id: str) -> str:
        """Map the winner's player_id back to the original bot identifier."""
        # The game assigns Player1 to the first bot and Player2 to the second bot
        if winner_player_id == "Player1":
            return first_bot_id
        elif winner_player_id == "Player2":
            return second_bot_id
        else:
            # Fallback, shouldn't happen
            return winner_player_id
    
    def _calculate_final_results(self) -> TournamentResult:
        """Calculate final tournament scores and return results."""
        # Count wins for each bot
        bot_scores = {bot_id: 0 for bot_id in self.bot_identifiers}
        for result in self.match_results:
            bot_scores[result.winner_id] += 1
        
        return TournamentResult(
            bot_scores=bot_scores,
            match_results=self.match_results,
            configs=self.configs,
            total_games=len(self.match_results)
        )
    
    def print_results(self, results: TournamentResult):
        """Print formatted tournament results.
        
        Args:
            results: Tournament results to display
        """
        print("\n" + "=" * 60)
        print("TOURNAMENT RESULTS")
        print("=" * 60)
        
        # Overall standings
        print("\nFINAL STANDINGS:")
        sorted_bots = sorted(results.bot_scores.items(), key=lambda x: x[1], reverse=True)
        for rank, (bot_name, wins) in enumerate(sorted_bots, 1):
            win_percentage = (wins / results.total_games) * 100 if results.total_games > 0 else 0
            print(f"  {rank}. {bot_name:20} {wins:3} wins ({win_percentage:.1f}%)")
        
        # Head-to-head breakdown
        print(f"\nHEAD-TO-HEAD BREAKDOWN:")
        print(f"(Each pair played {self.games_per_matchup} games per configuration)")
        
        for config in results.configs:
            print(f"\n  Configuration: {config.name}")
            
            # Create head-to-head matrix for this config
            config_results = [r for r in results.match_results if r.config_name == config.name]
            
            for bot1_id, bot2_id in itertools.combinations(self.bot_identifiers, 2):
                matchup_results = [r for r in config_results 
                                 if (r.bot1_id == bot1_id and r.bot2_id == bot2_id) or
                                    (r.bot1_id == bot2_id and r.bot2_id == bot1_id)]
                
                bot1_wins = len([r for r in matchup_results if r.winner_id == bot1_id])
                bot2_wins = len([r for r in matchup_results if r.winner_id == bot2_id])
                
                print(f"    {bot1_id} vs {bot2_id}: {bot1_wins}-{bot2_wins}")
        
        print("\n" + "=" * 60)