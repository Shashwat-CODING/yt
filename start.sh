#!/bin/bash
set -e

# Load environment variables from .env file if it exists
if [ -f .env ]; then
    echo "Loading environment variables from .env file"
    export $(grep -v '^#' .env | xargs)
fi

# Set default VPN credentials if not set in environment
if [ -z "$VPN_USERNAME" ]; then
    export VPN_USERNAME="vpnuser"
    echo "Using default VPN username"
fi

if [ -z "$VPN_PASSWORD" ]; then
    export VPN_PASSWORD="vpnpass2025"
    echo "Using default VPN password"
fi

# Function to check current IP
check_ip() {
    echo "Current IP address:"
    IP_INFO=$(curl -s https://ipinfo.io/json)
    IP=$(echo $IP_INFO | grep -o '"ip": "[^"]*' | cut -d'"' -f4)
    COUNTRY=$(echo $IP_INFO | grep -o '"country": "[^"]*' | cut -d'"' -f4)
    REGION=$(echo $IP_INFO | grep -o '"region": "[^"]*' | cut -d'"' -f4)
    CITY=$(echo $IP_INFO | grep -o '"city": "[^"]*' | cut -d'"' -f4)
    ISP=$(echo $IP_INFO | grep -o '"org": "[^"]*' | cut -d'"' -f4)

    echo "IP: $IP"
    echo "Country: $COUNTRY"
    echo "Region: $REGION"
    echo "City: $CITY"
    echo "ISP: $ISP"

    # Log to persistent log file for Render logs
    if [ -n "$RENDER" ]; then
        echo "[$(date)] VPN STATUS - IP: $IP, Country: $COUNTRY, Region: $REGION, City: $CITY, ISP: $ISP" >> /var/log/vpn-status.log
        echo "[RENDER_VPN_STATUS] IP: $IP, Country: $COUNTRY, Region: $REGION, City: $CITY"
    fi

    # Check if IP is from India
    if [ "$COUNTRY" = "IN" ]; then
        echo "✓ Successfully connected through Indian IP address"
        if [ -n "$RENDER" ]; then
            echo "[RENDER_VPN_STATUS] ✓ SUCCESS: Connected through Indian IP ($REGION, $CITY)"
            echo "CONNECTED_TO_INDIA=true" > /tmp/vpn_status
            echo "IP=$IP" >> /tmp/vpn_status
            echo "COUNTRY=$COUNTRY" >> /tmp/vpn_status
            echo "REGION=$REGION" >> /tmp/vpn_status
            echo "CITY=$CITY" >> /tmp/vpn_status
        fi
    else
        echo "⚠ Warning: Not connected through Indian IP address"
        if [ -n "$RENDER" ]; then
            echo "[RENDER_VPN_STATUS] ⚠ WARNING: Not connected through Indian IP (Current: $COUNTRY)"
            echo "CONNECTED_TO_INDIA=false" > /tmp/vpn_status
            echo "IP=$IP" >> /tmp/vpn_status
            echo "COUNTRY=$COUNTRY" >> /tmp/vpn_status
        fi
    fi
}

# Check initial IP before VPN connection
echo "Initial IP before VPN connection:"
check_ip

# Setup cookies first
echo "Setting up YouTube cookies..."
COOKIES_PATHS=(
    "./cookies.txt"
    "/app/cookies.txt"
    "./attached_assets/cookies.txt"
    "/app/attached_assets/cookies.txt"
    "/etc/youtube/cookies.txt"
)

COOKIES_FOUND=false
for path in "${COOKIES_PATHS[@]}"; do
    if [ -f "$path" ]; then
        echo "Found cookies at: $path"
        cp "$path" "./cookies.txt"
        chmod 644 "./cookies.txt"
        COOKIES_FOUND=true
        echo "✓ Copied and set permissions for cookies.txt"
        break
    fi
done

if [ "$COOKIES_FOUND" = false ]; then
    echo "⚠ WARNING: No cookies.txt found in any location"
    # Create an empty cookies file to prevent errors
    touch "./cookies.txt"
    chmod 644 "./cookies.txt"
fi

# Look for VPN config in multiple locations with clear logging
VPN_CONFIG_PATHS=(
    "/etc/openvpn/vpn-config.ovpn"
    "./vpn-config.ovpn"
    "/app/vpn-config.ovpn"
)

VPN_CONFIG_PATH=""
for path in "${VPN_CONFIG_PATHS[@]}"; do
    if [ -f "$path" ]; then
        VPN_CONFIG_PATH="$path"
        echo "Found VPN configuration at $VPN_CONFIG_PATH"
        break
    fi
done

if [ -n "$VPN_CONFIG_PATH" ]; then
    echo "Processing VPN configuration..."
    # Create a temporary file with proper permissions
    TMP_CONFIG="/tmp/processed-vpn-config.ovpn"
    cp "$VPN_CONFIG_PATH" "$TMP_CONFIG"
    chmod 600 "$TMP_CONFIG"

    # Replace placeholders with actual values
    sed -i "s/##VPN_USERNAME##/$VPN_USERNAME/g" "$TMP_CONFIG"
    sed -i "s/##VPN_PASSWORD##/$VPN_PASSWORD/g" "$TMP_CONFIG"

    # Ensure compression is enabled
    if ! grep -q "comp-lzo" "$TMP_CONFIG"; then
        echo "comp-lzo yes" >> "$TMP_CONFIG"
    fi

    echo "Starting OpenVPN connection..."
    if [ -n "$RENDER" ]; then
        # On Render, ensure we have proper permissions
        chmod 600 "$TMP_CONFIG"
        mkdir -p /dev/net
        if [ ! -c /dev/net/tun ]; then
            mknod /dev/net/tun c 10 200
        fi
        chmod 600 /dev/net/tun
    fi

    # Start OpenVPN in the background
    openvpn --config "$TMP_CONFIG" --daemon

    # Wait for VPN connection
    echo "Waiting for VPN connection to establish..."
    MAX_ATTEMPTS=15
    CONNECTED=false

    for i in $(seq 1 $MAX_ATTEMPTS); do
        sleep 5
        if pgrep -x "openvpn" > /dev/null; then
            echo "OpenVPN process is running (Attempt $i), checking IP..."
            check_ip
            if [ "$(cat /tmp/vpn_status | grep CONNECTED_TO_INDIA | cut -d= -f2)" = "true" ]; then
                echo "✓ VPN connected to Indian IP successfully"
                CONNECTED=true
                break
            else
                echo "VPN connected but not to Indian IP (Attempt $i)"
            fi
        else
            echo "OpenVPN process not running. Attempt $i/$MAX_ATTEMPTS..."
        fi
    done

    # Clean up
    rm -f "$TMP_CONFIG"

    if [ "$CONNECTED" = false ]; then
        echo "⚠ WARNING: Failed to establish VPN connection after $MAX_ATTEMPTS attempts"
        if [ -n "$RENDER" ]; then
            echo "[RENDER_VPN_STATUS] ⚠ Failed to establish VPN connection"
        fi
    fi
else
    echo "⚠ No VPN configuration found at any of the expected locations."
    echo "Available files in current directory:"
    ls -la
    echo "Available files in /etc/openvpn:"
    ls -la /etc/openvpn || echo "Directory not accessible"
fi

# Create cache directory
CACHE_DIR=${CACHE_DIR:-"/tmp/youtube_audio_cache"}
mkdir -p "$CACHE_DIR"
echo "Created cache directory at $CACHE_DIR"

# Double-check cookies file one last time
if [ -f "./cookies.txt" ]; then
    echo "✓ Cookies file is present and ready"
    ls -l "./cookies.txt"
else
    echo "⚠ WARNING: cookies.txt still not found after setup"
fi

# Start the Flask application
echo "Starting Flask application..."
exec gunicorn --bind 0.0.0.0:5000 --workers 4 --timeout 120 --access-logfile - --error-logfile - main:app