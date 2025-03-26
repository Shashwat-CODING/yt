# YouTube Audio Player

A Python-based YouTube audio player that allows you to search, extract, and play audio from YouTube videos. This application features both a terminal-based interface and a web interface for a more user-friendly experience.

## Features

- Search for YouTube videos using keywords
- Play audio directly from YouTube without downloading the entire video
- Create and manage multiple playlists
- Terminal-based interface for command-line enthusiasts
- Web application interface with responsive design
- Support for cookies.txt for accessing age-restricted or member-only content
- Direct streaming of audio for faster playback

## Getting Started

### Prerequisites

- Python 3.6 or higher
- Required packages: flask, flask-cors, innertube, pytube, pyaudio, requests, rich

### Installation

#### Method 1: Using pip to install dependencies

1. Clone the repository or download the source code
2. Install the required packages:

```bash
pip install flask flask-cors innertube pytube pyaudio requests rich
```

#### Method 2: Install as a package (For developers)

Install directly from the repository:

```bash
pip install git+https://github.com/yourusername/youtube-audio-player.git
```

Or install in development mode after cloning:

```bash
git clone https://github.com/yourusername/youtube-audio-player.git
cd youtube-audio-player
pip install -e .
```

#### Method 3: Using Poetry (Recommended)

1. Clone the repository or download the source code
2. Make sure you have [Poetry](https://python-poetry.org/docs/#installation) installed
3. Install dependencies using Poetry:

```bash
poetry install
```

4. Activate the Poetry virtual environment:

```bash
poetry shell
```

### Running the Terminal Application

#### Method 1: Direct execution

To run the terminal-based application:

```bash
python youtube_audio_player.py
```

#### Method 2: Using Poetry scripts (if installed with Poetry)

```bash
poetry run youtube-terminal
```

The terminal application provides a text-based interface with the following features:
- Search for YouTube videos
- Play/pause/stop audio playback
- Create and manage playlists
- Navigate using keyboard shortcuts

### Running the Web Application

#### Method 1: Direct execution

To run the web application:

```bash
python web_app.py
```

#### Method 2: Using Poetry scripts (if installed with Poetry)

```bash
poetry run youtube-web
```

Then open your browser and navigate to http://localhost:5000

The web interface offers:
- Clean, responsive design
- Search functionality with thumbnail previews
- One-click audio playback
- Create, view, and manage playlists
- Add/remove tracks from playlists

## Using Cookies (Optional)

For accessing age-restricted videos or member-only content, you can use cookies from your YouTube account:

1. Log in to your YouTube account in a browser
2. Install a browser extension to export cookies in Netscape/Mozilla format (e.g., "Get cookies.txt" for Chrome or "cookies.txt" for Firefox)
3. Export your cookies to a file named `cookies.txt`
4. Place the `cookies.txt` file in the root directory of the application
5. Restart the application

The application will automatically detect and use the cookies file if it exists. This allows:
- Playback of age-restricted content
- Access to member-only videos (if you're a channel member)
- Personalized recommendations based on your account (if using the search feature)

An example `cookies.txt.example` file is included to show the expected format.

## Usage Examples

### Web Interface

1. **Searching for videos**:
   - Enter keywords in the search bar and click "Search"
   - Results will display with thumbnails, titles, and channel information

2. **Playing audio**:
   - Click the play button next to any search result to start playback
   - Use the player controls to pause/resume or stop playback

3. **Creating a playlist**:
   - Click "Create Playlist" and enter a name
   - Your new playlist will appear in the playlists section

4. **Adding to a playlist**:
   - Click the "+" button next to any track
   - Select a playlist from the dropdown menu

### Terminal Interface

1. **Navigating the menu**:
   - Use arrow keys to navigate
   - Press Enter to select an option

2. **Searching for videos**:
   - Select "Search YouTube" from the main menu
   - Enter your search terms
   - Use arrow keys to navigate results

3. **Playing audio**:
   - Select a track and press Enter to play
   - Use keyboard shortcuts for playback control

## Project Structure

- `youtube_audio_player.py` - Terminal-based application entry point
- `web_app.py` - Web application entry point
- `modules/` - Core modules
  - `youtube_client.py` - YouTube API client using innertube and pytube
  - `audio_player.py` - Audio playback functionality with PyAudio
  - `playlist_manager.py` - Playlist creation and management
  - `terminal_ui.py` - Terminal user interface using the Rich library
- `static/` - Web application static files (CSS, JavaScript)
- `templates/` - Web application HTML templates
- `playlists/` - Directory for stored playlist files (JSON format)
- `temp_audio/` - Temporary audio files (not used with direct streaming)

## Troubleshooting

- **Audio not playing**: Check if your system has the necessary audio drivers installed.
- **Search not working**: Make sure you have an active internet connection.
- **Age-restricted content**: Add a valid cookies.txt file from your logged-in YouTube account.

## License

This project is licensed under the MIT License - see the LICENSE file for details.