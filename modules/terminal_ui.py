"""
Terminal UI module
Provides a text-based user interface using the Rich library
"""

import os
import time
import threading
from typing import List, Dict, Any, Optional, Callable
from rich.console import Console
from rich.panel import Panel
from rich.layout import Layout
from rich.table import Table
from rich.progress import Progress, BarColumn, TimeRemainingColumn
from rich.text import Text
from rich.prompt import Prompt, Confirm
from rich.style import Style
from rich.live import Live

from modules.youtube_client import YouTubeClient
from modules.audio_player import AudioPlayer
from modules.playlist_manager import PlaylistManager

class TerminalUI:
    """
    Terminal UI for the YouTube Audio Player
    """
    
    def __init__(self, 
                 youtube_client: YouTubeClient, 
                 audio_player: AudioPlayer, 
                 playlist_manager: PlaylistManager):
        """
        Initialize the terminal UI
        
        Args:
            youtube_client: YouTube client instance
            audio_player: Audio player instance
            playlist_manager: Playlist manager instance
        """
        self.youtube_client = youtube_client
        self.audio_player = audio_player
        self.playlist_manager = playlist_manager
        
        self.console = Console()
        self.search_results = []
        self.current_playlist_tracks = []
        
        # UI state
        self.running = True
        self.live = None
        self.progress = None
        self.current_position = 0
        self.current_duration = 0
        self.update_lock = threading.Lock()
    
    def run(self):
        """Main UI loop"""
        # Clear the screen
        os.system('cls' if os.name == 'nt' else 'clear')
        
        # Show welcome message
        self.console.print(Panel.fit(
            "[bold yellow]Welcome to YouTube Audio Player[/bold yellow]\n"
            "A terminal-based application to play audio from YouTube videos.",
            title="YouTube Audio Player",
            border_style="yellow"
        ))
        
        # Start UI update thread
        self.ui_thread = threading.Thread(target=self._ui_update_loop)
        self.ui_thread.daemon = True
        self.ui_thread.start()
        
        # Main menu loop
        while self.running:
            self._show_main_menu()
    
    def _ui_update_loop(self):
        """
        Background thread to update UI elements
        """
        while self.running:
            with self.update_lock:
                # Update current playback position
                if self.audio_player.is_playing():
                    self.current_position = self.audio_player.get_position()
                    self.current_duration = self.audio_player.get_duration()
            
            # Sleep to avoid excessive CPU usage
            time.sleep(0.1)
    
    def _show_main_menu(self):
        """Display the main menu and handle user input"""
        options = [
            "Search YouTube",
            "Manage Playlists",
            "Now Playing",
            "Exit"
        ]
        
        # Show current track if playing
        now_playing = ""
        if self.audio_player.is_playing() or self.audio_player.is_paused():
            track_info = self.audio_player.get_current_info()
            if track_info:
                status = "[bold green]▶ Playing[/bold green]" if self.audio_player.is_playing() else "[bold yellow]⏸ Paused[/bold yellow]"
                now_playing = f"\nNow {status}: [bold]{track_info['title']}[/bold] by {track_info['channel']}"
        
        # Build menu
        self.console.print()
        self.console.print(Panel.fit(
            "Please select an option:" + now_playing,
            title="Main Menu",
            border_style="blue"
        ))
        
        for i, option in enumerate(options, 1):
            self.console.print(f"  [bold cyan]{i}.[/bold cyan] {option}")
        
        # Get user input
        choice = Prompt.ask("Enter your choice", choices=[str(i) for i in range(1, len(options) + 1)])
        
        # Process choice
        if choice == "1":
            self._search_youtube()
        elif choice == "2":
            self._manage_playlists()
        elif choice == "3":
            self._now_playing()
        elif choice == "4":
            self._exit()
    
    def _search_youtube(self):
        """Search YouTube and display results"""
        query = Prompt.ask("[bold yellow]Enter search query[/bold yellow]")
        
        if not query:
            return
        
        self.console.print("[bold yellow]Searching YouTube...[/bold yellow]")
        
        # Search YouTube
        self.search_results = self.youtube_client.search(query)
        
        if not self.search_results:
            self.console.print("[bold red]No results found.[/bold red]")
            return
        
        # Display search results
        self._display_search_results()
    
    def _display_search_results(self):
        """Display search results in a table"""
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("#", style="dim", width=4)
        table.add_column("Title", min_width=30)
        table.add_column("Channel", min_width=20)
        table.add_column("Duration", width=10)
        
        for i, result in enumerate(self.search_results, 1):
            table.add_row(
                str(i),
                result['title'],
                result['channel'],
                result['duration']
            )
        
        self.console.print(Panel(table, title="Search Results", border_style="green"))
        
        # Show options
        self.console.print("\n[bold cyan]Options:[/bold cyan]")
        self.console.print("  [bold cyan]1-{0}.[/bold cyan] Play track".format(len(self.search_results)))
        self.console.print("  [bold cyan]a.[/bold cyan] Add to playlist")
        self.console.print("  [bold cyan]b.[/bold cyan] Back to main menu")
        
        # Get user input
        choices = [str(i) for i in range(1, len(self.search_results) + 1)] + ["a", "b"]
        choice = Prompt.ask("Enter your choice", choices=choices)
        
        if choice == "b":
            return
        elif choice == "a":
            self._add_to_playlist(self.search_results)
        else:
            # Play selected track
            track_index = int(choice) - 1
            self._play_track(self.search_results[track_index])
    
    def _play_track(self, track: Dict[str, Any]):
        """
        Play a YouTube track
        
        Args:
            track: Dictionary containing track information
        """
        self.console.print(f"[bold yellow]Getting audio for:[/bold yellow] {track['title']}")
        
        # Get audio stream
        audio_path, video_info = self.youtube_client.get_audio_stream(track['id'])
        
        if not audio_path:
            self.console.print("[bold red]Failed to get audio stream.[/bold red]")
            return
        
        # Play the track
        self.console.print(f"[bold green]Now playing:[/bold green] {video_info['title']}")
        
        def on_complete():
            """Callback when playback completes"""
            self.console.print("[bold green]Playback complete.[/bold green]")
            
            # Play next track in playlist if available
            if self.playlist_manager.get_current_playlist():
                next_track = self.playlist_manager.next_track()
                if next_track:
                    self.console.print(f"[bold yellow]Playing next track:[/bold yellow] {next_track['title']}")
                    self._play_track(next_track)
        
        self.audio_player.play(
            audio_path, 
            video_info,
            on_complete=on_complete
        )
        
        # Show now playing screen
        self._now_playing()
    
    def _now_playing(self):
        """Display the now playing screen with playback controls"""
        # Check if a track is playing
        if not (self.audio_player.is_playing() or self.audio_player.is_paused()):
            self.console.print("[bold yellow]No track is currently playing.[/bold yellow]")
            time.sleep(1)
            return
        
        # Get current track info
        track_info = self.audio_player.get_current_info()
        
        if not track_info:
            return
        
        # Create a live display
        layout = Layout()
        
        # Track info panel
        track_panel = Panel(
            f"[bold]{track_info['title']}[/bold]\n"
            f"Channel: {track_info['channel']}\n"
            f"Duration: {track_info['duration']}",
            title="Now Playing",
            border_style="green"
        )
        
        # Progress bar
        progress = Progress(
            "[progress.description]{task.description}",
            BarColumn(),
            "[progress.percentage]{task.percentage:>3.0f}%",
            TimeRemainingColumn(),
        )
        progress_task = progress.add_task("Playing", total=100)
        
        # Controls panel
        controls_panel = Panel(
            "[bold cyan]Controls:[/bold cyan]\n"
            "[p] Play/Pause  [s] Stop  [n] Next  [b] Previous  [m] Main Menu",
            title="Playback Controls",
            border_style="blue"
        )
        
        # Combine panels
        layout.split(
            Layout(track_panel, name="track", size=3),
            Layout(progress, name="progress", size=1),
            Layout(controls_panel, name="controls", size=2)
        )
        
        # Create live display
        with Live(layout, refresh_per_second=4) as live:
            while (self.audio_player.is_playing() or self.audio_player.is_paused()) and self.running:
                # Update progress
                if self.current_duration > 0:
                    percent_complete = min(100, (self.current_position / self.current_duration) * 100)
                    progress.update(progress_task, completed=percent_complete)
                
                # Update status
                status = "Playing" if self.audio_player.is_playing() else "Paused"
                progress.update(progress_task, description=status)
                
                # Check for user input
                if self.console.input_ready():
                    key = self.console.getch()
                    
                    if key == 'p':
                        self.audio_player.toggle_pause()
                    elif key == 's':
                        self.audio_player.stop()
                        break
                    elif key == 'n':
                        if self.playlist_manager.get_current_playlist():
                            next_track = self.playlist_manager.next_track()
                            if next_track:
                                self.audio_player.stop()
                                self._play_track(next_track)
                                break
                    elif key == 'b':
                        if self.playlist_manager.get_current_playlist():
                            prev_track = self.playlist_manager.previous_track()
                            if prev_track:
                                self.audio_player.stop()
                                self._play_track(prev_track)
                                break
                    elif key == 'm':
                        break
                
                time.sleep(0.1)
    
    def _manage_playlists(self):
        """Display playlist management menu"""
        options = [
            "View Playlists",
            "Create Playlist",
            "Delete Playlist",
            "Back to Main Menu"
        ]
        
        self.console.print(Panel.fit(
            "Please select an option:",
            title="Playlist Management",
            border_style="blue"
        ))
        
        for i, option in enumerate(options, 1):
            self.console.print(f"  [bold cyan]{i}.[/bold cyan] {option}")
        
        # Get user input
        choice = Prompt.ask("Enter your choice", choices=[str(i) for i in range(1, len(options) + 1)])
        
        # Process choice
        if choice == "1":
            self._view_playlists()
        elif choice == "2":
            self._create_playlist()
        elif choice == "3":
            self._delete_playlist()
        elif choice == "4":
            return
    
    def _view_playlists(self):
        """Display available playlists"""
        playlists = self.playlist_manager.get_playlists()
        
        if not playlists:
            self.console.print("[bold yellow]No playlists found.[/bold yellow]")
            return
        
        # Display playlists
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("#", style="dim", width=4)
        table.add_column("Playlist", min_width=30)
        
        for i, playlist in enumerate(playlists, 1):
            table.add_row(str(i), playlist)
        
        self.console.print(Panel(table, title="Available Playlists", border_style="green"))
        
        # Show options
        self.console.print("\n[bold cyan]Options:[/bold cyan]")
        self.console.print("  [bold cyan]1-{0}.[/bold cyan] View playlist".format(len(playlists)))
        self.console.print("  [bold cyan]b.[/bold cyan] Back to playlist menu")
        
        # Get user input
        choices = [str(i) for i in range(1, len(playlists) + 1)] + ["b"]
        choice = Prompt.ask("Enter your choice", choices=choices)
        
        if choice == "b":
            self._manage_playlists()
            return
        
        # View selected playlist
        playlist_index = int(choice) - 1
        self._view_playlist_tracks(playlists[playlist_index])
    
    def _view_playlist_tracks(self, playlist_name: str):
        """
        Display tracks in a playlist
        
        Args:
            playlist_name: Name of the playlist
        """
        tracks = self.playlist_manager.load_playlist(playlist_name)
        
        if not tracks:
            self.console.print(f"[bold yellow]Playlist '{playlist_name}' is empty.[/bold yellow]")
            return
        
        # Display tracks
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("#", style="dim", width=4)
        table.add_column("Title", min_width=30)
        table.add_column("Channel", min_width=20)
        table.add_column("Duration", width=10)
        
        for i, track in enumerate(tracks, 1):
            table.add_row(
                str(i),
                track['title'],
                track['channel'],
                track['duration']
            )
        
        self.console.print(Panel(table, title=f"Playlist: {playlist_name}", border_style="green"))
        
        # Show options
        self.console.print("\n[bold cyan]Options:[/bold cyan]")
        self.console.print("  [bold cyan]1-{0}.[/bold cyan] Play track".format(len(tracks)))
        self.console.print("  [bold cyan]p.[/bold cyan] Play entire playlist")
        self.console.print("  [bold cyan]r.[/bold cyan] Remove track")
        self.console.print("  [bold cyan]b.[/bold cyan] Back to playlists")
        
        # Get user input
        choices = [str(i) for i in range(1, len(tracks) + 1)] + ["p", "r", "b"]
        choice = Prompt.ask("Enter your choice", choices=choices)
        
        if choice == "b":
            self._view_playlists()
            return
        elif choice == "p":
            # Play entire playlist
            self.playlist_manager.load_playlist(playlist_name)
            first_track = self.playlist_manager.get_current_track()
            if first_track:
                self._play_track(first_track)
        elif choice == "r":
            # Remove track from playlist
            track_index = Prompt.ask(
                "Enter track number to remove",
                choices=[str(i) for i in range(1, len(tracks) + 1)]
            )
            track_index = int(track_index) - 1
            self.playlist_manager.remove_from_playlist(playlist_name, tracks[track_index]['id'])
            self._view_playlist_tracks(playlist_name)
        else:
            # Play selected track
            track_index = int(choice) - 1
            self.playlist_manager.load_playlist(playlist_name)
            self.playlist_manager.current_index = track_index
            self._play_track(tracks[track_index])
    
    def _add_to_playlist(self, tracks: List[Dict[str, Any]]):
        """
        Add tracks to a playlist
        
        Args:
            tracks: List of track dictionaries
        """
        # Get available playlists
        playlists = self.playlist_manager.get_playlists()
        
        if not playlists:
            # No playlists exist, create one
            self.console.print("[bold yellow]No playlists found. Creating a new playlist.[/bold yellow]")
            self._create_playlist()
            playlists = self.playlist_manager.get_playlists()
            
            if not playlists:
                return
        
        # Display playlists
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("#", style="dim", width=4)
        table.add_column("Playlist", min_width=30)
        
        for i, playlist in enumerate(playlists, 1):
            table.add_row(str(i), playlist)
        
        self.console.print(Panel(table, title="Available Playlists", border_style="green"))
        
        # Get user input for playlist selection
        choices = [str(i) for i in range(1, len(playlists) + 1)] + ["n", "c"]
        self.console.print("  [bold cyan]1-{0}.[/bold cyan] Select playlist".format(len(playlists)))
        self.console.print("  [bold cyan]n.[/bold cyan] Create new playlist")
        self.console.print("  [bold cyan]c.[/bold cyan] Cancel")
        
        choice = Prompt.ask("Enter your choice", choices=choices)
        
        if choice == "c":
            return
        elif choice == "n":
            # Create new playlist
            new_playlist = self._create_playlist()
            if not new_playlist:
                return
            selected_playlist = new_playlist
        else:
            # Use existing playlist
            playlist_index = int(choice) - 1
            selected_playlist = playlists[playlist_index]
        
        # Select tracks to add
        if len(tracks) == 1:
            # Only one track, add it directly
            self.playlist_manager.add_to_playlist(selected_playlist, tracks[0])
            self.console.print(f"[bold green]Added '{tracks[0]['title']}' to playlist '{selected_playlist}'.[/bold green]")
        else:
            # Multiple tracks, ask which ones to add
            self.console.print(f"[bold yellow]Select tracks to add to '{selected_playlist}':[/bold yellow]")
            self.console.print("  [bold cyan]1-{0}.[/bold cyan] Individual track".format(len(tracks)))
            self.console.print("  [bold cyan]a.[/bold cyan] Add all tracks")
            self.console.print("  [bold cyan]c.[/bold cyan] Cancel")
            
            choices = [str(i) for i in range(1, len(tracks) + 1)] + ["a", "c"]
            choice = Prompt.ask("Enter your choice", choices=choices)
            
            if choice == "c":
                return
            elif choice == "a":
                # Add all tracks
                added_count = 0
                for track in tracks:
                    if self.playlist_manager.add_to_playlist(selected_playlist, track):
                        added_count += 1
                
                self.console.print(f"[bold green]Added {added_count} tracks to playlist '{selected_playlist}'.[/bold green]")
            else:
                # Add individual track
                track_index = int(choice) - 1
                if self.playlist_manager.add_to_playlist(selected_playlist, tracks[track_index]):
                    self.console.print(f"[bold green]Added '{tracks[track_index]['title']}' to playlist '{selected_playlist}'.[/bold green]")
                else:
                    self.console.print("[bold red]Failed to add track to playlist.[/bold red]")
    
    def _create_playlist(self) -> Optional[str]:
        """
        Create a new playlist
        
        Returns:
            Name of the created playlist or None if creation failed
        """
        playlist_name = Prompt.ask("[bold yellow]Enter playlist name[/bold yellow]")
        
        if not playlist_name:
            return None
        
        if self.playlist_manager.create_playlist(playlist_name):
            self.console.print(f"[bold green]Playlist '{playlist_name}' created successfully.[/bold green]")
            return playlist_name
        else:
            self.console.print("[bold red]Failed to create playlist.[/bold red]")
            return None
    
    def _delete_playlist(self):
        """Delete a playlist"""
        playlists = self.playlist_manager.get_playlists()
        
        if not playlists:
            self.console.print("[bold yellow]No playlists found.[/bold yellow]")
            return
        
        # Display playlists
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("#", style="dim", width=4)
        table.add_column("Playlist", min_width=30)
        
        for i, playlist in enumerate(playlists, 1):
            table.add_row(str(i), playlist)
        
        self.console.print(Panel(table, title="Available Playlists", border_style="green"))
        
        # Get user input
        choices = [str(i) for i in range(1, len(playlists) + 1)] + ["c"]
        self.console.print("  [bold cyan]1-{0}.[/bold cyan] Select playlist to delete".format(len(playlists)))
        self.console.print("  [bold cyan]c.[/bold cyan] Cancel")
        
        choice = Prompt.ask("Enter your choice", choices=choices)
        
        if choice == "c":
            return
        
        # Confirm deletion
        playlist_index = int(choice) - 1
        playlist_name = playlists[playlist_index]
        
        if Confirm.ask(f"Are you sure you want to delete playlist '{playlist_name}'?"):
            if self.playlist_manager.delete_playlist(playlist_name):
                self.console.print(f"[bold green]Playlist '{playlist_name}' deleted successfully.[/bold green]")
            else:
                self.console.print("[bold red]Failed to delete playlist.[/bold red]")
    
    def _exit(self):
        """Exit the application"""
        if Confirm.ask("Are you sure you want to exit?"):
            self.running = False
            self.audio_player.stop()
