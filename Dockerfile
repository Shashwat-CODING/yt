FROM python:3.11-slim

# Install OpenVPN and other dependencies
RUN apt-get update && \
    apt-get install -y \
    openvpn \
    ffmpeg \
    curl \
    ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy requirements first for better caching
COPY render_requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app
COPY . .

# Create directory for VPN config
RUN mkdir -p /etc/openvpn

# Volume for VPN config files (you'll need to mount this when running the container)
VOLUME /etc/openvpn

# Expose port for Flask app
EXPOSE 5000

# Start script to connect VPN and run app
COPY start.sh /start.sh
RUN chmod +x /start.sh

# Run the start script when the container launches
CMD ["/start.sh"]