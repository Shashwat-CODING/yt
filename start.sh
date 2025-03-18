#!/bin/bash
set -e

# Function to check current IP
check_ip() {
    echo "Current IP address:"
    curl -s https://httpbin.org/ip
}

# Check initial IP before VPN connection
echo "Initial IP before VPN connection:"
check_ip

# Check if VPN config file exists
VPN_CONFIG_PATH="/etc/openvpn/vpn-config.ovpn"
if [ -f "$VPN_CONFIG_PATH" ]; then
    echo "Found VPN configuration at $VPN_CONFIG_PATH"
    
    # Process the VPN config to replace environment variable placeholders
    if [ -n "$VPN_USERNAME" ] && [ -n "$VPN_PASSWORD" ]; then
        echo "Substituting VPN credentials from environment variables..."
        # Create a temporary file
        TMP_CONFIG="/tmp/processed-vpn-config.ovpn"
        cp "$VPN_CONFIG_PATH" "$TMP_CONFIG"
        
        # Replace placeholders with actual values
        sed -i "s/##VPN_USERNAME##/$VPN_USERNAME/g" "$TMP_CONFIG"
        sed -i "s/##VPN_PASSWORD##/$VPN_PASSWORD/g" "$TMP_CONFIG"
        
        # Use the processed config
        VPN_CONFIG_PATH="$TMP_CONFIG"
        echo "VPN config processed with credentials"
    fi
    
    echo "Starting OpenVPN connection..."
    # Start OpenVPN in the background
    openvpn --config "$VPN_CONFIG_PATH" --daemon
    
    # Give VPN a moment to connect
    echo "Waiting for VPN connection to establish..."
    MAX_ATTEMPTS=12
    CONNECTED=false
    
    for i in $(seq 1 $MAX_ATTEMPTS); do
        sleep 5
        if pgrep -x "openvpn" > /dev/null; then
            echo "OpenVPN process is running, checking IP..."
            check_ip
            echo "VPN connection established. Starting application..."
            CONNECTED=true
            break
        else
            echo "OpenVPN process not running. Attempt $i/$MAX_ATTEMPTS..."
            if [ $i -eq $MAX_ATTEMPTS ]; then
                echo "WARNING: OpenVPN failed to start. Continuing without VPN..."
            fi
        fi
    done
    
    # Clean up the temporary config file if it was created
    if [ -f "$TMP_CONFIG" ]; then
        rm -f "$TMP_CONFIG"
    fi
    
    # If connected to VPN successfully, verify we can access YouTube
    if [ "$CONNECTED" = true ]; then
        echo "Testing YouTube connectivity through VPN..."
        if curl -s --head --fail "https://www.youtube.com" > /dev/null; then
            echo "Successfully connected to YouTube through VPN"
        else
            echo "WARNING: Connected to VPN but YouTube access may be restricted"
        fi
    fi
else
    echo "No VPN configuration found at $VPN_CONFIG_PATH"
    echo "Starting application without VPN..."
fi

# Start the Flask application with gunicorn
echo "Starting Flask application..."
exec gunicorn --bind 0.0.0.0:5000 --workers 4 --timeout 120 main:app