# Security Camera System

Web-based interface for Raspberry Pi security camera with motion detection and live streaming.

## Hardware Requirements

- Raspberry Pi Zero 2 W (512MB RAM minimum)
- Raspberry Pi Camera Module (v2 or v3)
- MicroSD card (32GB+ recommended)
- Stable power supply (5V 2.5A recommended)

## Features

- **Motion Detection**: Automatic capture when movement detected
- **Event Recording**: 30-second videos with before/after images
- **Live Streaming**: Real-time camera view at 10fps (MJPEG)
- **Web Interface**: Browse events, view logs, control streaming
- **Responsive Design**: Works on desktop, tablet, and mobile

## System Architecture

### Backend (Python)
- **Thread 1**: Circular buffer (camera + H.264 recording)
- **Thread 2**: Motion detection (pixel-difference algorithm)
- **Thread 3**: Event processor (saves pictures/videos)
- **Thread 4**: MJPEG server (live streaming)

### Frontend (Web)
- **nginx**: Web server
- **PHP 8.4**: Dynamic page generation
- **JavaScript**: Interactive features (AJAX, lightbox, streaming control)
- **SQLite**: Event and log storage

## Installation

### Prerequisites
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y \
    nginx \
    php8.4-fpm php8.4-sqlite3 \
    python3-picamera2 python3-opencv python3-pil \
    sqlite3 \
    git

# Enable camera
sudo raspi-config
# Interface Options → Camera → Enable
```

### Clone Repository
```bash
cd /home/pi
git clone https://github.com/kklasmeier/security-camera.git sec_cam
cd sec_cam
```

### Setup Script
```bash
# Make setup script executable
chmod +x setup.sh

# Run setup
./setup.sh
```

This will:
- Create required directories
- Set up file permissions
- Configure nginx
- Create systemd service
- Initialize database

### Manual Setup (if setup.sh not available)
```bash
# Create directories
mkdir -p videos pictures thumbs tmp logs www/api

# Set permissions
chmod 755 videos pictures thumbs www www/assets www/includes www/api
chmod 664 events.db  # (after first run)

# Configure nginx
sudo cp nginx.conf /etc/nginx/sites-available/sec-cam
sudo ln -s /etc/nginx/sites-available/sec-cam /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default  # Remove default site
sudo nginx -t
sudo systemctl restart nginx

# Set up systemd service
sudo cp sec-cam.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable sec-cam
sudo systemctl start sec-cam
```

## Configuration

Edit `config.py` to customize:
```python
# Video settings
VIDEO_RESOLUTION = (1280, 720)
VIDEO_FRAMERATE = 15

# Motion detection
MOTION_THRESHOLD = 60
MOTION_SENSITIVITY = 50
MOTION_COOLDOWN_SECONDS = 65

# Streaming
LIVESTREAM_PORT = 8080
```

## Usage

### Web Interface

Access at: `http://[your-pi-ip]/`

**Pages:**
- **Events** - Browse captured motion events
- **Event Detail** - View video and images
- **Live View** - Real-time camera stream
- **Logs** - System log viewer

### System Control
```bash
# Start/stop camera system
sudo systemctl start sec-cam
sudo systemctl stop sec-cam
sudo systemctl restart sec-cam

# View logs
sudo journalctl -u sec-cam -f

# Check status
sudo systemctl status sec-cam
```

## File Structure
```
/home/pi/sec_cam/
├── Python files (camera system)
│   ├── sec_cam_main.py       (main orchestrator)
│   ├── circular_buffer.py    (camera & buffer)
│   ├── motion_detector.py    (motion detection)
│   ├── event_processor.py    (save events)
│   ├── mjpeg_server.py       (live streaming)
│   ├── database.py           (SQLite interface)
│   ├── logger.py             (logging system)
│   ├── motion_event.py       (thread coordination)
│   └── config.py             (configuration)
│
├── Web interface
│   └── www/
│       ├── index.php         (events list)
│       ├── event.php         (event detail)
│       ├── live.php          (live view)
│       ├── logs.php          (log viewer)
│       ├── includes/         (PHP modules)
│       ├── assets/           (CSS/JS)
│       └── api/              (AJAX endpoints)
│
├── Data (NOT in Git)
│   ├── events.db            (SQLite database)
│   ├── videos/              (MP4 event videos)
│   ├── pictures/            (full-res images)
│   ├── thumbs/              (thumbnails)
│   └── logs/                (system logs)
│
└── Configuration
    ├── nginx.conf           (nginx config)
    └── sec-cam.service      (systemd service)
```

## Troubleshooting

### Camera won't start
```bash
# Check if camera is detected
vcgencmd get_camera

# Check logs
sudo journalctl -u sec-cam -n 50

# Kill stuck processes
sudo pkill -9 python3
sudo systemctl restart sec-cam
```

### Web pages not loading
```bash
# Check nginx
sudo systemctl status nginx
sudo nginx -t

# Check PHP-FPM
sudo systemctl status php8.4-fpm

# Check permissions
ls -la /home/pi/sec_cam/www/
```

### High memory usage
```bash
# Check memory
free -h

# Check processes
ps aux | grep python

# Restart system
sudo systemctl restart sec-cam
```

### Stream won't start
```bash
# Check streaming flag
sqlite3 events.db "SELECT * FROM system_control;"

# Reset flag
sqlite3 events.db "UPDATE system_control SET streaming=0 WHERE id=1;"

# Check MJPEG server logs
sudo journalctl -u sec-cam -f | grep -i mjpeg
```

## Performance

**Typical resource usage:**
- CPU: 15-25% (idle), 40-60% (motion event)
- RAM: ~260MB (normal), ~280MB (streaming)
- Storage: ~2-3MB per event (30s video + images)

**Recommendations:**
- Use Class 10 or better microSD card
- 32GB+ storage for ~2-3 months of events
- Regular backups recommended

## Maintenance

### Backup Database
```bash
cp events.db events.db.backup.$(date +%Y%m%d)
```

### Clean Old Events
```bash
# Delete videos older than 30 days
find videos/ -name "*.mp4" -mtime +30 -delete
find pictures/ -name "*.jpg" -mtime +30 -delete
find thumbs/ -name "*.jpg" -mtime +30 -delete
```

### Vacuum Database
```bash
sqlite3 events.db "VACUUM;"
```

## Contributing

This is a personal project, but suggestions and improvements are welcome!

## License

MIT License - See LICENSE file for details

## Author

Kevin Klasmeier - https://github.com/kklasmeier

## Acknowledgments

Built with the help of Claude AI (Anthropic) over 8 development sessions.
