#!/bin/bash
# Security Camera System - Setup Script
# Prepares a fresh Raspberry Pi for camera operation

set -e  # Exit on error

echo "================================================"
echo "Security Camera System - Setup"
echo "================================================"
echo ""

# Check if running as pi user
if [ "$USER" != "pi" ]; then
    echo "❌ This script must be run as the 'pi' user"
    exit 1
fi

# Check if in correct directory
if [ ! -f "sec_cam_main.py" ]; then
    echo "❌ Please run this script from /home/pi/sec_cam directory"
    exit 1
fi

echo "✓ Running as pi user"
echo "✓ In correct directory"
echo ""

# Create required directories
echo "Creating directories..."
mkdir -p videos pictures thumbs tmp logs www/api
echo "✓ Directories created"

# Set initial permissions
echo "Setting permissions..."
chmod 755 videos pictures thumbs www www/assets www/includes www/api
chmod 644 www/*.php www/includes/*.php www/api/*.php www/assets/*.css www/assets/*.js 2>/dev/null || true
echo "✓ Permissions set"

# Check if nginx is installed
if ! command -v nginx &> /dev/null; then
    echo "❌ nginx is not installed. Please run:"
    echo "   sudo apt install nginx"
    exit 1
fi
echo "✓ nginx installed"

# Check if PHP is installed
if ! command -v php &> /dev/null; then
    echo "❌ PHP is not installed. Please run:"
    echo "   sudo apt install php-fpm php-sqlite3"
    exit 1
fi
echo "✓ PHP installed"

# Check if Python packages are available
if ! python3 -c "import picamera2" 2>/dev/null; then
    echo "⚠ picamera2 not installed. Please run:"
    echo "   sudo apt install python3-picamera2"
fi

# Configure nginx
if [ -f "nginx.conf" ]; then
    echo "Configuring nginx..."
    sudo cp nginx.conf /etc/nginx/sites-available/sec-cam
    sudo ln -sf /etc/nginx/sites-available/sec-cam /etc/nginx/sites-enabled/
    sudo rm -f /etc/nginx/sites-enabled/default
    
    # Test nginx config
    if sudo nginx -t 2>&1 | grep -q "successful"; then
        echo "✓ nginx configured"
        sudo systemctl restart nginx
        echo "✓ nginx restarted"
    else
        echo "❌ nginx configuration error"
        exit 1
    fi
else
    echo "⚠ nginx.conf not found - skipping nginx setup"
fi

# Set up systemd service
if [ -f "sec-cam.service" ]; then
    echo "Setting up systemd service..."
    sudo cp sec-cam.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable sec-cam
    echo "✓ Systemd service installed and enabled"
else
    echo "⚠ sec-cam.service not found - skipping service setup"
fi

echo ""
echo "================================================"
echo "✓ Setup complete!"
echo "================================================"
echo ""
echo "Next steps:"
echo "1. Start the camera system:"
echo "   sudo systemctl start sec-cam"
echo ""
echo "2. Check status:"
echo "   sudo systemctl status sec-cam"
echo ""
echo "3. View logs:"
echo "   sudo journalctl -u sec-cam -f"
echo ""
echo "4. Access web interface:"
echo "   http://$(hostname -I | awk '{print $1}')/"
echo ""
