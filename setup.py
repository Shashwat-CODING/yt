import os
from flask import Flask, jsonify
from flask_cors import CORS
from datetime import datetime
from innertube import InnerTube  # Import from local module
import json  # Added for handling cookies

app = Flask(__name__)
CORS(app)

# Get the absolute path of cookies.txt in the same folder as the script
cookies_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookies.txt")

@app.route('/streams/<video_id>', methods=['GET'])
def get_video_info(video_id):
    try:
        # Read cookies from file if it exists and is not empty
        cookies = None
        if os.path.exists(cookies_path) and os.path.getsize(cookies_path) > 0:
            try:
                with open(cookies_path, 'r') as f:
                    cookies = json.load(f)
            except json.JSONDecodeError:
                print(f"Warning: Unable to parse cookies from {cookies_path}. Proceeding without cookies.")

        # Initialize InnerTube with optional cookies
        yt = InnerTube("ANDROID", cookies=cookies) if cookies else InnerTube("ANDROID")
        
        data = yt.player(video_id)

        if "videoDetails" not in data or "streamingData" not in data:
            return jsonify({"error": "No video details found"}), 404

        video_details = data["videoDetails"]
        streaming_data = data["streamingData"]

        # Convert upload date to timestamp
        try:
            upload_timestamp = int(datetime.strptime(video_details.get("publishDate", ""), "%Y-%m-%d").timestamp())
        except:
            upload_timestamp = 0

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