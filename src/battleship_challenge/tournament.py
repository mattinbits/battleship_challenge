"""
Tournament system for battleship bot competitions.

This module manages tournaments where multiple bots compete against each other
across different game configurations.
"""

import itertools
import time
from dataclasses import dataclass
from typing import List, Tuple, Dict, Type
from .interface import BattleshipBot
from .game import BattleshipGame
from .main import discover_bot_class, create_bot_instances
from .visualization import Colors


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
    
    def __init__(self, bot_names: List[str], configs: List[GameConfig], games_per_matchup: int = 10, 
                 visualize: bool = False, delay: float = 1.0):
        """Initialize the tournament.
        
        Args:
            bot_names: List of bot class names to compete
            configs: List of game configurations to play
            games_per_matchup: Number of games each pair plays per configuration (default: 10)
            visualize: Whether to enable visual effects and progress displays (default: False)
            delay: Delay in seconds between visual updates for suspense (default: 1.0)
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
        self.visualize = visualize
        self.delay = delay
        self.current_scores: Dict[str, int] = {}
        
    def _clear_screen(self):
        """Clear the console screen if visualization is enabled."""
        if self.visualize:
            print('\033[2J\033[H', end='', flush=True)
    
    def _print_progress_bar(self, current: int, total: int, width: int = 40, 
                           label: str = "Progress") -> None:
        """Display a visual progress bar."""
        if not self.visualize:
            return
        
        percentage = current / total if total > 0 else 0
        filled_width = int(width * percentage)
        bar = '█' * filled_width + '▒' * (width - filled_width)
        
        print(f"{Colors.CYAN}{label}: {Colors.WHITE}[{Colors.GREEN}{bar}{Colors.WHITE}] "
              f"{Colors.YELLOW}{current}/{total} {Colors.CYAN}({percentage:.1f}%){Colors.RESET}")
    
    def _display_tournament_header(self, total_games: int):
        """Display tournament header with configuration details."""
        if not self.visualize:
            return
            
        self._clear_screen()
        print(f"{Colors.BOLD}{Colors.MAGENTA}{'='*80}")
        print("🏆 BATTLESHIP TOURNAMENT 🏆")
        print(f"{'='*80}{Colors.RESET}")
        
        print(f"\n{Colors.CYAN}📋 Tournament Setup:{Colors.RESET}")
        print(f"   {Colors.WHITE}🤖 Competing Bots:{Colors.RESET} {Colors.YELLOW}{', '.join(self.bot_identifiers)}{Colors.RESET}")
        print(f"   {Colors.WHITE}🎮 Total Games:{Colors.RESET} {Colors.GREEN}{total_games}{Colors.RESET}")
        print(f"   {Colors.WHITE}⚙️  Games per matchup:{Colors.RESET} {Colors.GREEN}{self.games_per_matchup}{Colors.RESET}")
        
        print(f"\n{Colors.CYAN}🗺️  Game Configurations:{Colors.RESET}")
        for i, config in enumerate(self.configs, 1):
            print(f"   {Colors.WHITE}{i}. {config.name}:{Colors.RESET} "
                  f"{Colors.BLUE}{config.board_size[0]}x{config.board_size[1]}{Colors.RESET} board, "
                  f"ships {Colors.GREEN}{config.ships}{Colors.RESET}")
        
        print(f"\n{Colors.BOLD}{Colors.YELLOW}⏰ Get ready for battle!{Colors.RESET}")
        
    def _display_live_leaderboard(self, game_count: int, total_games: int):
        """Display current tournament standings."""
        if not self.visualize or not self.current_scores:
            return
        
        print(f"\n{Colors.BOLD}{Colors.CYAN}📊 Live Leaderboard:{Colors.RESET}")
        sorted_bots = sorted(self.current_scores.items(), key=lambda x: x[1], reverse=True)
        
        for rank, (bot_name, wins) in enumerate(sorted_bots, 1):
            total_played = sum(1 for r in self.match_results if r.winner_id == bot_name or 
                             r.bot1_id == bot_name or r.bot2_id == bot_name)
            win_rate = (wins / total_played * 100) if total_played > 0 else 0
            
            # Different colors for different ranks
            if rank == 1:
                rank_color = Colors.YELLOW + Colors.BOLD  # Gold
                emoji = "🥇"
            elif rank == 2:
                rank_color = Colors.WHITE + Colors.BOLD   # Silver  
                emoji = "🥈"
            elif rank == 3:
                rank_color = Colors.RED + Colors.BOLD     # Bronze
                emoji = "🥉"
            else:
                rank_color = Colors.GRAY
                emoji = f"{rank}."
            
            print(f"   {rank_color}{emoji} {bot_name:15} {Colors.GREEN}{wins:3} wins "
                  f"{Colors.CYAN}({win_rate:.1f}%){Colors.RESET}")
    
    def _display_match_header(self, config: GameConfig, bot1_id: str, bot2_id: str):
        """Display header for a new matchup."""
        if not self.visualize:
            return
        
        print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}")
        print(f"⚔️  {bot1_id} vs {bot2_id}")
        print(f"📍 Configuration: {config.name}")
        print(f"{'='*60}{Colors.RESET}")
    
    def _display_game_result(self, game_num: int, bot1_id: str, bot2_id: str, 
                           winner_id: str, suspense: bool = True):
        """Display individual game result with optional suspense."""
        if not self.visualize:
            return
        
        print(f"\n{Colors.WHITE}🎲 Game {game_num}: {bot1_id} vs {bot2_id}")
        
        if suspense and self.delay > 0:
            for dots in ["   .", "   ..", "   ..."]:
                print(f"\r{Colors.GRAY}   Battling{dots}{Colors.RESET}", end='', flush=True)
                time.sleep(self.delay / 3)
        
        winner_color = Colors.GREEN + Colors.BOLD
        print(f"\r{Colors.WHITE}   🏆 Winner: {winner_color}{winner_id}{Colors.RESET}")
        
        if suspense:
            time.sleep(self.delay / 2)

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
        
        # Initialize current scores
        self.current_scores = {bot_id: 0 for bot_id in self.bot_identifiers}
        
        # Calculate total number of games
        num_bot_pairs = len(list(itertools.combinations(self.bot_names, 2)))
        total_games = num_bot_pairs * len(self.configs) * self.games_per_matchup
        
        if self.visualize:
            self._display_tournament_header(total_games)
            if self.delay > 0:
                time.sleep(self.delay * 2)  # Pause to let users read setup
        else:
            print(f"\nStarting tournament with {len(self.bot_names)} bots, {len(self.configs)} configs")
            print(f"Each bot pair will play {self.games_per_matchup} games per config")
            print(f"Total games to play: {total_games}")
            print("-" * 60)
        
        game_count = 0
        
        # Play all bot combinations in all configurations
        for config in self.configs:
            if self.visualize:
                self._clear_screen()
                print(f"\n{Colors.BOLD}{Colors.MAGENTA}📍 Configuration: {config.name}{Colors.RESET}")
                print(f"{Colors.WHITE}Board: {Colors.BLUE}{config.board_size[0]}x{config.board_size[1]}{Colors.RESET}, "
                      f"Ships: {Colors.GREEN}{config.ships}{Colors.RESET}")
                self._print_progress_bar(game_count, total_games, label="Tournament Progress")
                self._display_live_leaderboard(game_count, total_games)
            else:
                print(f"\nPlaying configuration: {config.name}")
                print(f"Board: {config.board_size[0]}x{config.board_size[1]}, Ships: {config.ships}")
            
            for bot1_id, bot2_id in itertools.combinations(self.bot_identifiers, 2):
                if self.visualize:
                    self._display_match_header(config, bot1_id, bot2_id)
                elif verbose:
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
                    
                    # Map winner back to bot identifier
                    winner_bot_id = self._get_original_bot_id(winner_id, first_bot_id, second_bot_id)
                    
                    # Record the result
                    result = MatchResult(
                        bot1_id=bot1_id,
                        bot2_id=bot2_id,
                        config_name=config.name,
                        winner_id=winner_bot_id,
                        game_number=game_num + 1
                    )
                    self.match_results.append(result)
                    
                    # Update current scores
                    self.current_scores[winner_bot_id] += 1
                    
                    # Display results
                    if self.visualize:
                        self._display_game_result(game_num + 1, bot1_id, bot2_id, winner_bot_id)
                    elif verbose:
                        print(f"    Game {game_num + 1}: {winner_bot_id} wins")
                    
                    # Progress indicator for non-visual mode
                    if not verbose and not self.visualize and game_count % 10 == 0:
                        print(f"  Progress: {game_count}/{total_games} games completed")
                
                # Show updated leaderboard after each matchup in visual mode
                if self.visualize:
                    self._display_live_leaderboard(game_count, total_games)
                    time.sleep(self.delay / 2)
        
        if self.visualize:
            self._clear_screen()
            print(f"\n{Colors.BOLD}{Colors.GREEN}🎉 Tournament Complete! 🎉{Colors.RESET}")
            self._print_progress_bar(total_games, total_games, label="Tournament Progress")
        else:
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