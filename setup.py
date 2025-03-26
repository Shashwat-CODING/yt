import os
import http.cookiejar
from flask import Flask, jsonify
from flask_cors import CORS
from datetime import datetime
from innertube import InnerTube  # Import from local module

app = Flask(__name__)
CORS(app)

# Get the absolute path of cookies.txt in the same folder as the script
cookies_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookies.txt")

def parse_netscape_cookie_file(cookie_file):
    """
    Parse a Netscape-style cookie file and return raw cookie string
    """
    cookie_jar = http.cookiejar.MozillaCookieJar(cookie_file)
    cookie_jar.load(ignore_discard=True, ignore_expires=True)
    
    # Generate cookie string in the format "COOKIE1=value; COOKIE2=value;"
    cookie_string = '; '.join([f"{cookie.name}={cookie.value}" for cookie in cookie_jar])
    return cookie_string

@app.route('/streams/<video_id>', methods=['GET'])
def get_video_info(video_id):
    try:
        # Attempt to parse cookies
        cookie_string = None
        if os.path.exists(cookies_path):
            try:
                cookie_string = parse_netscape_cookie_file(cookies_path)
                print("Parsed cookie string:", cookie_string[:100] + "..." if len(cookie_string) > 100 else cookie_string)  # Truncated debug print
            except Exception as e:
                print(f"Warning: Unable to parse cookies. Error: {e}")

        # Initialize InnerTube
        try:
            # Try to pass cookie string directly if available
            yt = InnerTube("ANDROID", proxy=None)
            
            # If a cookie string exists, set it manually
            if cookie_string:
                # Attempt to set cookies via a method that might exist
                if hasattr(yt, 'set_cookie'):
                    yt.set_cookie(cookie_string)
                elif hasattr(yt, '_InnerTube__cookie'):
                    yt._InnerTube__cookie = cookie_string
        except Exception as e:
            print(f"Error initializing InnerTube: {e}")
            yt = InnerTube("ANDROID")
        
        data = yt.player(video_id)

        if "videoDetails" not in data or "streamingData" not in data:
            return jsonify({"error": "No video details found"}), 404

        video_details = data["videoDetails"]
        streaming_data = data["streamingData"]

        # Piped-like response structure
        response = {
            "title": video_details.get("title", ""),
            "description": video_details.get("shortDescription", ""),
            "uploadDate": video_details.get("publishDate", ""),
            "uploader": video_details.get("author", ""),
            "uploaderUrl": f"/channel/{video_details.get('channelId', '')}",
            "uploaderAvatar": "",
            "thumbnailUrl": video_details.get("thumbnail", {}).get("thumbnails", [{}])[-1].get("url", "") if "thumbnail" in video_details else "",
            "hls": streaming_data.get("hlsManifestUrl", ""),
            "dash": streaming_data.get("dashManifestUrl", ""),
            "duration": int(video_details.get("lengthSeconds", 0)),
            "views": int(video_details.get("viewCount", 0)),
            "likes": 0,  # YouTube no longer provides likes count
            "audioStreams": [
                {
                    "url": audio_fmt.get("url", ""),
                    "format": "AUDIO",
                    "quality": audio_fmt.get("audioQuality", "").replace("AUDIO_QUALITY_", "").capitalize(),
                    "mimeType": audio_fmt.get("mimeType", ""),
                    "bitrate": audio_fmt.get("bitrate", 0),
                    "codec": audio_fmt.get("mimeType", "").split(";")[0].split("/")[-1] if "mimeType" in audio_fmt else "",
                    "size": int(audio_fmt.get("contentLength", 0))
                }
                for audio_fmt in streaming_data.get("adaptiveFormats", []) 
                if "audio" in audio_fmt.get("mimeType", "").lower()
            ],
            "videoStreams": [
                {
                    "url": video_fmt.get("url", ""),
                    "format": "VIDEO",
                    "quality": video_fmt.get("qualityLabel", ""),
                    "mimeType": video_fmt.get("mimeType", ""),
                    "bitrate": video_fmt.get("bitrate", 0),
                    "codec": video_fmt.get("mimeType", "").split(";")[0].split("/")[-1] if "mimeType" in video_fmt else "",
                    "width": video_fmt.get("width", 0),
                    "height": video_fmt.get("height", 0),
                    "size": int(video_fmt.get("contentLength", 0))
                }
                for video_fmt in streaming_data.get("adaptiveFormats", []) 
                if "video" in video_fmt.get("mimeType", "").lower() and "audio" not in video_fmt.get("mimeType", "").lower()
            ],
            "relatedStreams": [],
            "livestreamStream": streaming_data.get("hlsManifestUrl", "") if video_details.get("isLiveContent", False) else ""
        }

        return jsonify(response)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=3001, debug=True)