# Deploying to Render with VPN Support

This guide explains how to deploy the YouTube Audio Player application to Render with VPN support to route traffic through an Indian IP address.

## Prerequisites

1. A Render account (https://render.com)
2. An OpenVPN configuration file for a VPN server in India
3. Your application code pushed to a Git repository (GitHub, GitLab, etc.)

## Setup Steps

### 1. Prepare OpenVPN Configuration

First, you need to obtain an OpenVPN configuration file (`.ovpn`) for a VPN server located in India. You can get this from a VPN provider that offers servers in India.

The configuration file should include all necessary certificates and credentials embedded within it for simplicity. Alternatively, you can use Render's environment variables to store sensitive information.

### 2. Deploy to Render

#### Option 1: Using the Dashboard

1. Log in to your Render account
2. Create a new Web Service
3. Connect your Git repository
4. Select "Docker" as the Environment
5. Configure the service:
   - Name: youtube-audio-player (or your preferred name)
   - Environment: Docker
   - Branch: main (or your default branch)
   - Root Directory: ./ (or the directory containing your Dockerfile)
   - Disk: Create a new disk mounted at `/etc/openvpn` with at least 1GB space

6. Set environment variables:
   - `SESSION_SECRET`: Generate a secure random string
   - `DATABASE_URL`: Your PostgreSQL connection string if using a database

7. Create the service

#### Option 2: Using Blueprint (render.yaml)

1. Add the provided `render.yaml` file to your repository
2. Log in to your Render dashboard
3. Click "Blueprint" and select your repository
4. Follow the prompts to deploy the services defined in the YAML file

### 3. Upload VPN Configuration

After deployment:

1. In your Render dashboard, navigate to your web service
2. Go to the "Disks" tab
3. You should see a disk mounted at `/etc/openvpn`
4. Upload your `.ovpn` file to this disk, naming it `vpn-config.ovpn`

### 4. Restart the Service

After uploading the VPN configuration:

1. Go to the "Overview" tab of your service
2. Click "Manual Deploy" and select "Clear build cache & deploy"

## Testing the VPN Connection

Once deployed, you can verify if the VPN connection is working by:

1. Go to the "Logs" tab of your service
2. Check for messages like "Starting OpenVPN connection..." and "VPN connection established"
3. You should see the output of the IP address check, which should show an Indian IP address

## Troubleshooting

If the VPN connection fails:

1. Check the logs for error messages
2. Verify that your `.ovpn` file is correctly formatted and includes all necessary certificates
3. Try using a different VPN server or provider if issues persist

For application-specific errors, check the logs for any error messages and debug accordingly.

## Configuration Notes

- The Dockerfile installs OpenVPN and sets up the environment
- The `start.sh` script handles connecting to the VPN before starting the Flask application
- The application is configured to use Gunicorn as the WSGI server on port 5000

## Security Considerations

- Ensure your VPN credentials are kept secure
- The OpenVPN configuration should be treated as sensitive information
- Consider using a dedicated VPN service for production applications