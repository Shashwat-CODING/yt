# YouTube Audio Player with VPN Support

A Flask-based web application that allows you to stream audio from YouTube videos through a VPN connection. This implementation specifically targets routing traffic through Indian IP addresses to access region-specific content.

## Features

- Stream audio from YouTube videos
- OpenVPN integration for routing traffic through Indian IP addresses
- Resilient connection handling with automatic retries
- Caching of audio streams for better performance
- Playlist management system
- Responsive web interface

## System Requirements

- Python 3.11+
- Docker (for containerized deployment)
- OpenVPN configuration for an Indian server

## Local Development Setup

1. Clone this repository
2. Create a virtual environment and activate it:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Set up environment variables (see `.env.example`)
5. Set up a PostgreSQL database and update the `DATABASE_URL` in your environment
6. Run the application:
   ```
   python main.py
   ```

## VPN Setup

For VPN functionality, you'll need:

1. An OpenVPN configuration file (`.ovpn`) for an Indian server
2. Proper credentials for your VPN service

See [VPN_SETUP_GUIDE.md](VPN_SETUP_GUIDE.md) for detailed instructions on setting up the VPN connection.

## Deployment to Render

This application is designed to be deployed on [Render](https://render.com) with VPN support. 

See [RENDER_DEPLOYMENT.md](RENDER_DEPLOYMENT.md) for step-by-step deployment instructions.

## Architecture

- **Flask Backend**: Handles requests and YouTube data extraction
- **yt-dlp**: Extracts audio streams from YouTube
- **OpenVPN**: Routes traffic through Indian IP addresses
- **SQLAlchemy**: Database ORM for playlist and cache management
- **Gunicorn**: WSGI HTTP server for production

## Database Schema

The application uses the following database models:

- **Playlist**: Stores user-created playlists
- **PlaylistItem**: Stores YouTube videos within playlists
- **AudioCache**: Tracks cached audio files for better performance

## Usage

1. Open the web application in your browser
2. Enter a YouTube URL in the input field
3. Click "Play" to stream the audio
4. Optionally add the current track to a playlist

## Security Considerations

- VPN credentials should be kept secure
- Use environment variables for sensitive information
- The OpenVPN configuration file contains sensitive data and should be protected

## Troubleshooting

- If you encounter VPN connection issues, check the Render logs
- For YouTube extraction errors, verify that your VPN is correctly routing traffic through an Indian IP

## License

[MIT License](LICENSE)

## Acknowledgements

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) for YouTube extraction
- [Flask](https://flask.palletsprojects.com/) for the web framework
- [OpenVPN](https://openvpn.net/) for VPN connectivity