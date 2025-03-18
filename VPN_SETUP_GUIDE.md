# VPN Setup Guide for Render Deployment

This guide will help you set up a VPN connection on your Render deployment to route traffic through an Indian IP address, which is useful for accessing region-restricted content.

## Prerequisites

1. A VPN service that provides servers in India
2. An OpenVPN configuration file (`.ovpn`) for an Indian server

## Step 1: Obtain OpenVPN Configuration

1. Sign up for a VPN service that offers servers in India
2. Download the OpenVPN configuration file (`.ovpn`) for an Indian server
3. Make sure the configuration file includes all necessary certificates and keys

## Step 2: Prepare OpenVPN Configuration

You have two options for handling VPN credentials:

### Option 1: Embed Credentials in the Config File

1. Open the `.ovpn` file in a text editor
2. If you have separate certificate and key files, copy their contents into the appropriate sections:
   ```
   <ca>
   ... (CA certificate content) ...
   </ca>
   
   <cert>
   ... (Client certificate content) ...
   </cert>
   
   <key>
   ... (Client key content) ...
   </key>
   ```
3. If your VPN requires username/password authentication, you can either:
   - Hardcode them in the config (less secure):
     ```
     <auth-user-pass>
     your_username
     your_password
     </auth-user-pass>
     ```
   - Or use environment variable placeholders (more secure):
     ```
     <auth-user-pass>
     ##VPN_USERNAME##
     ##VPN_PASSWORD##
     </auth-user-pass>
     ```

### Option 2: Use Environment Variables

1. In your Render dashboard, add the following environment variables:
   - `VPN_USERNAME`: Your VPN username
   - `VPN_PASSWORD`: Your VPN password
2. Make sure your `.ovpn` file contains the placeholder section:
   ```
   <auth-user-pass>
   ##VPN_USERNAME##
   ##VPN_PASSWORD##
   </auth-user-pass>
   ```

## Step 3: Upload Configuration to Render

1. Save your prepared `.ovpn` file as `vpn-config.ovpn`
2. Deploy your service to Render using either the dashboard or Blueprint method described in `RENDER_DEPLOYMENT.md`
3. Once deployed, go to your service's "Disks" tab
4. Upload the `vpn-config.ovpn` file to the `/etc/openvpn` directory

## Step 4: Restart and Verify

1. Restart your service
2. Check the logs to verify that:
   - The VPN connection is established
   - The reported IP address is from India
   - The application can successfully connect to YouTube

## Troubleshooting

### VPN Connection Issues

If the VPN fails to connect:

1. Check the logs for specific error messages
2. Make sure your `.ovpn` file is properly formatted
3. Verify that your VPN credentials are correct
4. Try a different VPN server or provider

### YouTube Access Issues

If you can connect to the VPN but still can't access YouTube:

1. Verify that your VPN provider allows access to YouTube from Indian servers
2. Some VPN providers may be blocked by YouTube, try a different provider
3. Check if the VPN provider has specialized servers for streaming

## Security Considerations

1. Store your VPN credentials securely using Render's environment variables
2. Regularly update your VPN configuration and credentials
3. Monitor your application's logs for any unauthorized access attempts