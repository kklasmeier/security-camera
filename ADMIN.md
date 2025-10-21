# Security Camera System - Administrator Guide

Complete guide for system administration, maintenance, and troubleshooting.

---

## Table of Contents

1. [System Architecture](#system-architecture)
2. [File Structure](#file-structure)
3. [Service Management](#service-management)
4. [Database Management](#database-management)
5. [Log Management](#log-management)
6. [Backup & Restore](#backup--restore)
7. [Performance Monitoring](#performance-monitoring)
8. [Security Considerations](#security-considerations)
9. [Advanced Configuration](#advanced-configuration)
10. [Troubleshooting Guide](#troubleshooting-guide)
11. [System Recovery](#system-recovery)

---

## System Architecture

### Component Overview
```
┌─────────────────────────────────────────────────┐
│           Security Camera System                │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌─────────────┐  ┌─────────────────────────┐   │
│  │   nginx     │  │  Python Camera System   │   │
│  │  (Port 80)  │  │  (4 Threads)            │   │
│  └──────┬──────┘  └────────┬────────────────┘   │
│         │                  │                    │
│  ┌──────▼──────┐  ┌────────▼────────────────┐   │
│  │  PHP 8.4    │  │  Thread 1: Buffer       │   │
│  │  (FastCGI)  │  │  Thread 2: Motion Det.  │   │
│  └──────┬──────┘  │  Thread 3: Events       │   │
│         │         │  Thread 4: MJPEG Server │   │
│  ┌──────▼──────┐  └────────┬────────────────┘   │
│  │   SQLite    │◄───────────┘                   │
│  │  Database   │                                │
│  └─────────────┘                                │
│                                                 │
│  Storage: videos/, pictures/, thumbs/, logs/    │
└─────────────────────────────────────────────────┘
```

### Process Hierarchy
```
systemd
  └── sec-cam.service
      └── python3 sec_cam_main.py
          ├── Thread 1: CircularBuffer (Camera + H.264 recording)
          ├── Thread 2: MotionDetector (Pixel-diff algorithm)
          ├── Thread 3: EventProcessor (Save pictures/videos)
          ├── Thread 4: MJPEGServer (Live streaming)
          └── Watchdog: Camera recovery
```

### Data Flow

**Motion Detection Flow:**
```
Camera → Buffer → Motion Detection → Database Record
                       ↓
                  Signal Thread 3
                       ↓
              Save: Picture A (T+0s)
                    Picture B (T+4s)
                    Thumbnail
                    Video (30s: buffer + continuation)
```

**Live Streaming Flow:**
```
User clicks "Start Stream" → PHP sets streaming=1 in DB
                                    ↓
            MJPEG Server polls DB (detects flag=1)
                                    ↓
            Calls buffer.start_streaming()
                                    ↓
            Buffer increases capture rate (2fps → 10fps)
            Pauses motion detection
                                    ↓
            MJPEG Server starts HTTP on port 8080
            Serves MJPEG stream from buffer frames
```

---

## File Structure

### Project Directory
```
/home/pi/sec_cam/
├── Python Backend
│   ├── sec_cam_main.py          # Main orchestrator
│   ├── circular_buffer.py       # Camera & circular buffer
│   ├── motion_detector.py       # Motion detection
│   ├── event_processor.py       # Event saving
│   ├── mjpeg_server.py          # Live streaming (Thread 4)
│   ├── motion_event.py          # Thread coordination
│   ├── database.py              # SQLite interface
│   ├── logger.py                # Logging system
│   └── config.py                # Configuration
│
├── Web Interface
│   └── www/
│       ├── index.php            # Events list
│       ├── event.php            # Event detail
│       ├── live.php             # Live streaming
│       ├── logs.php             # Log viewer
│       ├── includes/
│       │   ├── db.php           # PHP database class
│       │   ├── functions.php    # Helper functions
│       │   ├── header.php       # Navigation
│       │   └── footer.php       # Footer
│       ├── assets/
│       │   ├── style.css        # Styling
│       │   ├── script.js        # JavaScript
│       │   └── *.png, *.ico     # Logo/favicon
│       └── api/
│           ├── set_streaming.php     # Streaming control
│           └── get_new_logs.php      # Log fetching
│
├── Data (NOT in Git)
│   ├── events.db                # SQLite database
│   ├── videos/                  # Event videos (*.mp4)
│   ├── pictures/                # Full-res images (*_a.jpg, *_b.jpg)
│   ├── thumbs/                  # Thumbnails
│   └── logs/                    # System logs (if file logging enabled)
│
├── Scripts
│   ├── setup.sh                 # Deployment script
│   ├── gitsync.sh               # Git helper (optional)
│   ├── run.sh                   # Manual run script
│   ├── killpython.sh            # Kill stuck processes
│   └── convert_pending.sh       # H.264 → MP4 converter
│
├── Configuration
│   ├── nginx.conf               # nginx site config
│   └── sec-cam.service          # systemd service
│
└── Documentation
    ├── README.md                # Overview & quick start
    ├── DEPLOYMENT.md            # Deployment guide
    ├── ADMIN.md                 # This file
    ├── LICENSE                  # MIT License
    └── .gitignore               # Git exclusions
```

### Important File Locations

**System Configuration:**
- nginx config: `/etc/nginx/sites-available/sec-cam`
- systemd service: `/etc/systemd/system/sec-cam.service`
- PHP config: `/etc/php/8.4/fpm/php.ini`

**Logs:**
- Camera system: `journalctl -u sec-cam`
- nginx access: `/var/log/nginx/sec-cam-access.log`
- nginx errors: `/var/log/nginx/sec-cam-error.log`
- PHP errors: `/var/log/php8.4-fpm.log`

---

## Service Management

### Systemd Service Control
```bash
# Start service
sudo systemctl start sec-cam

# Stop service
sudo systemctl stop sec-cam

# Restart service (apply config changes)
sudo systemctl restart sec-cam

# Check status
sudo systemctl status sec-cam

# Enable auto-start on boot
sudo systemctl enable sec-cam

# Disable auto-start
sudo systemctl disable sec-cam

# View service file
cat /etc/systemd/system/sec-cam.service
```

### Service Status Interpretation

**Healthy Output:**
```
● sec-cam.service - Security Camera System
     Loaded: loaded (/etc/systemd/system/sec-cam.service; enabled)
     Active: active (running) since Tue 2025-10-21 10:00:00 EDT; 2h 30min ago
   Main PID: 1234 (python3)
     Memory: 260.0M
        CPU: 15min 30s
```

**Problem Indicators:**
- `Active: failed` - Service crashed
- `Active: activating (auto-restart)` - Repeatedly crashing
- Memory very high (>400M) - Possible leak
- CPU very high (>80% sustained) - Performance issue

### Manual Process Management
```bash
# Check if Python process running
ps aux | grep python3 | grep sec_cam_main

# Kill stuck Python processes (emergency only!)
sudo pkill -9 python3
# Or use the provided script:
sudo /home/pi/sec_cam/killpython.sh

# Check active threads
ps -eLf | grep python3 | wc -l
# Should show ~10-15 threads (4 main + supporting threads)
```

### Web Server Management
```bash
# nginx
sudo systemctl status nginx
sudo systemctl restart nginx
sudo nginx -t  # Test configuration

# PHP-FPM
sudo systemctl status php8.4-fpm
sudo systemctl restart php8.4-fpm
```

---

## Database Management

### Database Schema
```sql
-- Events table (motion detection records)
CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    motion_score INTEGER,
    image_a_path TEXT,
    image_b_path TEXT,
    thumbnail_path TEXT,
    video_path TEXT,
    duration_seconds INTEGER DEFAULT 30,
    ai_processed BOOLEAN DEFAULT 0,
    ai_processed_at DATETIME,
    ai_objects TEXT,
    ai_tags TEXT,
    ai_description TEXT,
    ai_confidence FLOAT,
    ai_severity INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME
);

-- Logs table
CREATE TABLE logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    level TEXT,  -- 'INFO', 'WARNING', 'ERROR'
    message TEXT
);

-- System control table
CREATE TABLE system_control (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    streaming BOOLEAN DEFAULT 0,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Common Database Operations
```bash
# Connect to database
sqlite3 /home/pi/sec_cam/events.db

# Useful queries (at sqlite> prompt):

# Check schema
.schema

# Count records
SELECT COUNT(*) FROM events;
SELECT COUNT(*) FROM logs;

# Recent events
SELECT id, timestamp, motion_score FROM events 
ORDER BY timestamp DESC LIMIT 10;

# Check streaming status
SELECT * FROM system_control;

# Reset streaming flag (if stuck)
UPDATE system_control SET streaming=0 WHERE id=1;

# Events by date
SELECT DATE(timestamp) as date, COUNT(*) as count 
FROM events 
GROUP BY DATE(timestamp) 
ORDER BY date DESC;

# Log errors
SELECT timestamp, message FROM logs 
WHERE level='ERROR' 
ORDER BY timestamp DESC 
LIMIT 20;

# Database size
.database

# Exit
.quit
```

### Database Maintenance

**Vacuum (Reclaim Space & Optimize):**
```bash
# Stop services first
sudo systemctl stop sec-cam

# Backup
cp events.db events.db.backup

# Vacuum
sqlite3 events.db "VACUUM;"

# Restart
sudo systemctl start sec-cam

# Check new size
ls -lh events.db
```

**Integrity Check:**
```bash
sqlite3 events.db "PRAGMA integrity_check;"
# Should return: ok
```

**Analyze (Update Query Planner Stats):**
```bash
sqlite3 events.db "ANALYZE;"
```

### Data Cleanup

**Delete Old Events:**
```bash
# WARNING: This deletes data permanently!

# Stop service
sudo systemctl stop sec-cam

# Backup database
cp events.db events.db.backup

# Delete events older than 30 days
sqlite3 events.db "DELETE FROM events WHERE timestamp < datetime('now', '-30 days');"

# Delete corresponding media files
find videos/ -name "*.mp4" -mtime +30 -delete
find pictures/ -name "*.jpg" -mtime +30 -delete
find thumbs/ -name "*.jpg" -mtime +30 -delete

# Vacuum to reclaim space
sqlite3 events.db "VACUUM;"

# Restart service
sudo systemctl start sec-cam
```

**Delete Old Logs:**
```bash
# Delete logs older than 7 days
sqlite3 events.db "DELETE FROM logs WHERE timestamp < datetime('now', '-7 days');"
sqlite3 events.db "VACUUM;"
```

---

## Log Management

### Viewing Logs

**Camera System Logs (journalctl):**
```bash
# Real-time logs (follow mode)
sudo journalctl -u sec-cam -f

# Last 100 lines
sudo journalctl -u sec-cam -n 100

# Logs since boot
sudo journalctl -u sec-cam -b

# Logs from last hour
sudo journalctl -u sec-cam --since "1 hour ago"

# Only errors
sudo journalctl -u sec-cam -p err

# Search for text
sudo journalctl -u sec-cam | grep "motion detected"

# Export to file
sudo journalctl -u sec-cam > /tmp/sec-cam-logs.txt
```

**Filter by Component:**
```bash
# Motion detection
sudo journalctl -u sec-cam -f | grep -i motion

# MJPEG streaming
sudo journalctl -u sec-cam -f | grep -i mjpeg

# Watchdog
sudo journalctl -u sec-cam -f | grep -i watchdog

# Memory usage
sudo journalctl -u sec-cam -f | grep -i memory
```

**Web Server Logs:**
```bash
# nginx access log
sudo tail -f /var/log/nginx/sec-cam-access.log

# nginx error log
sudo tail -f /var/log/nginx/sec-cam-error.log

# PHP-FPM errors
sudo tail -f /var/log/php8.4-fpm.log
```

### Log Rotation

**journald (automatic):**
- Logs rotate automatically
- Default: Keep 3 days or 500MB
- Configure: `/etc/systemd/journald.conf`

**nginx logs:**
```bash
# Manually rotate if needed
sudo logrotate -f /etc/logrotate.d/nginx
```

---

## Backup & Restore

### What to Backup

**Critical (must backup):**
- `/home/pi/sec_cam/events.db` - Event metadata
- `/home/pi/sec_cam/config.py` - Custom configuration

**Important (if storage permits):**
- `/home/pi/sec_cam/videos/` - Event videos
- `/home/pi/sec_cam/pictures/` - Full-resolution images

**Optional:**
- `/home/pi/sec_cam/thumbs/` - Can regenerate from pictures

**Don't need to backup:**
- Code files (on GitHub)
- `/home/pi/sec_cam/www/` (on GitHub)

### Backup Strategies

**1. Database Only (Daily):**
```bash
#!/bin/bash
# Save as: /home/pi/scripts/backup_db.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/home/pi/backups"

mkdir -p $BACKUP_DIR

# Backup database
cp /home/pi/sec_cam/events.db $BACKUP_DIR/events_$DATE.db

# Keep only last 7 days
find $BACKUP_DIR -name "events_*.db" -mtime +7 -delete

echo "Database backed up to: $BACKUP_DIR/events_$DATE.db"
```

Run daily via cron:
```bash
crontab -e

# Add line:
0 3 * * * /home/pi/scripts/backup_db.sh
```

**2. Full Backup (Weekly):**
```bash
#!/bin/bash
# Save as: /home/pi/scripts/backup_full.sh

DATE=$(date +%Y%m%d)
BACKUP_DIR="/media/usb_backup"  # External drive
SOURCE="/home/pi/sec_cam"

# Create backup directory
mkdir -p $BACKUP_DIR

# Sync (excludes videos older than 7 days)
rsync -av \
    --exclude='videos/' \
    --exclude='logs/' \
    --exclude='tmp/' \
    --exclude='__pycache__/' \
    $SOURCE/ $BACKUP_DIR/sec_cam_$DATE/

# Backup recent videos only (last 7 days)
find $SOURCE/videos/ -name "*.mp4" -mtime -7 \
    -exec cp {} $BACKUP_DIR/sec_cam_$DATE/videos/ \;

echo "Full backup completed: $BACKUP_DIR/sec_cam_$DATE/"
```

**3. Cloud Backup (Optional):**
```bash
# Using rclone to sync to cloud storage
# Install: sudo apt install rclone

# Configure cloud storage
rclone config

# Sync database to cloud
rclone copy /home/pi/sec_cam/events.db remote:sec-cam-backups/
```

### Restore Procedures

**Restore Database:**
```bash
# Stop service
sudo systemctl stop sec-cam

# Backup current database (just in case)
mv events.db events.db.old

# Restore from backup
cp /path/to/backup/events_20251021.db events.db

# Set permissions
chmod 664 events.db
chown pi:pi events.db

# Restart service
sudo systemctl start sec-cam
```

**Restore Full System:**
```bash
# On new Pi, after cloning repo:
cd /home/pi/sec_cam

# Stop service if running
sudo systemctl stop sec-cam

# Restore database
cp /path/to/backup/events.db ./

# Restore videos (if backed up)
rsync -av /path/to/backup/videos/ ./videos/

# Restore pictures (if backed up)
rsync -av /path/to/backup/pictures/ ./pictures/

# Set permissions
chmod 664 events.db
chmod 755 videos pictures thumbs

# Restart
sudo systemctl start sec-cam
```

---

## Performance Monitoring

### System Resources

**Memory Usage:**
```bash
# Overall system memory
free -h

# Camera process memory
ps aux | grep python3 | grep sec_cam_main

# Detailed memory breakdown
sudo pmap $(pgrep -f sec_cam_main.py) | tail -1

# Memory over time (watch)
watch -n 5 'free -h; echo "---"; ps aux | grep python | head -3'
```

**CPU Usage:**
```bash
# Overall CPU
top

# Camera process CPU
top -p $(pgrep -f sec_cam_main.py)

# CPU temperature
vcgencmd measure_temp

# Throttling check (should be 0x0)
vcgencmd get_throttled
```

**Disk Usage:**
```bash
# Overall disk space
df -h

# Database size
du -h events.db

# Media file sizes
du -sh videos/ pictures/ thumbs/

# Largest files
du -ah videos/ | sort -rh | head -20
```

**Network (Streaming):**
```bash
# Active connections
ss -tuln | grep 8080

# nginx connections
ss -tuln | grep :80

# Bandwidth usage (if iftop installed)
sudo iftop -i wlan0
```

### Performance Metrics

**Normal Operation (Idle):**
- CPU: 15-25%
- RAM: ~260MB
- Temp: <60°C
- Disk I/O: Minimal

**During Motion Event:**
- CPU: 40-60% (spike during processing)
- RAM: ~280MB
- Disk I/O: High (writing video)

**During Streaming:**
- CPU: 30-40%
- RAM: ~280MB
- Network: ~1-2 Mbps (10fps MJPEG)

### Performance Alerts

**High CPU (>80% sustained):**
- Check for motion detection loop
- Verify no stuck processes
- Review watchdog logs

**High Memory (>400MB):**
- Possible memory leak
- Stop streaming
- Restart service
- Review logs for errors

**High Temperature (>75°C):**
- Improve cooling
- Reduce video bitrate
- Lower motion detection frequency

---

## Security Considerations

### Network Security

**Current Setup:**
- ✅ Local network only (no internet exposure)
- ✅ No authentication (acceptable for trusted network)
- ❌ HTTP only (no HTTPS)

**Recommendations:**

1. **Network Isolation:**
```bash
   # Configure router to isolate camera on VLAN
   # Prevent access from untrusted devices
```

2. **Firewall Rules:**
```bash
   # Allow only necessary ports
   sudo ufw enable
   sudo ufw allow from 192.168.1.0/24 to any port 80
   sudo ufw allow from 192.168.1.0/24 to any port 8080
```

3. **For Remote Access (use VPN, not port forwarding):**
```bash
   # Install WireGuard or OpenVPN
   # Access camera through secure VPN tunnel
   # NEVER expose directly to internet
```

### Application Security

**SQL Injection Prevention:**
- ✅ All queries use PDO prepared statements
- ✅ Event IDs validated as integers
- ✅ Log filters sanitized

**XSS Prevention:**
- ✅ All user output escaped with `htmlspecialchars()`
- ✅ Database content sanitized before display

**Path Traversal Prevention:**
- ✅ File paths validated
- ✅ No user-supplied paths in media URLs
- ✅ nginx restricts access to project directory

**Resource Limits:**
- ✅ Pagination limits enforced
- ✅ Log query limits
- ✅ 15-minute streaming timeout

### Physical Security

- Secure microSD card (prevent theft)
- Protect camera from tampering
- Consider case with tamper detection

---

## Advanced Configuration

### config.py Tuning

**Motion Detection Sensitivity:**
```python
# More sensitive (more events)
MOTION_THRESHOLD = 40      # Default: 60
MOTION_SENSITIVITY = 30    # Default: 50

# Less sensitive (fewer events)
MOTION_THRESHOLD = 80
MOTION_SENSITIVITY = 70
```

**Video Quality:**
```python
# Higher quality (larger files)
VIDEO_BITRATE = 5000000    # Default: 3000000
VIDEO_RESOLUTION = (1920, 1080)  # Default: (1280, 720)

# Lower quality (smaller files, better performance)
VIDEO_BITRATE = 2000000
VIDEO_RESOLUTION = (1280, 720)
```

**Buffer Size:**
```python
# More pre-motion footage
CIRCULAR_BUFFER_MAX_CHUNKS = 1500  # Default: 1000

# Less pre-motion footage (save memory)
CIRCULAR_BUFFER_MAX_CHUNKS = 600
```

**Cooldown Period:**
```python
# Less frequent events
MOTION_COOLDOWN_SECONDS = 90  # Default: 65

# More frequent events (careful!)
MOTION_COOLDOWN_SECONDS = 45
```

### nginx Optimization

Add to `/etc/nginx/sites-available/sec-cam`:
```nginx
# Enable gzip compression
gzip on;
gzip_types text/css application/javascript application/json;

# Browser caching
location ~* \.(jpg|jpeg|png|css|js)$ {
    expires 7d;
    add_header Cache-Control "public";
}

# Rate limiting (prevent abuse)
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
location /api/ {
    limit_req zone=api burst=20;
}
```

### PHP Optimization

Edit `/etc/php/8.4/fpm/php.ini`:
```ini
# Enable OPcache
opcache.enable=1
opcache.memory_consumption=64
opcache.max_accelerated_files=4000

# Error logging
display_errors = Off
log_errors = On
error_log = /var/log/php_errors.log
```

Restart PHP-FPM:
```bash
sudo systemctl restart php8.4-fpm
```

---

## Troubleshooting Guide

### Diagnostic Commands

**Full System Check:**
```bash
#!/bin/bash
# Save as: /home/pi/scripts/system_check.sh

echo "=== System Check ==="
echo ""

echo "1. Service Status:"
sudo systemctl status sec-cam --no-pager | head -5
echo ""

echo "2. Camera Detection:"
vcgencmd get_camera
echo ""

echo "3. Memory Usage:"
free -h | grep Mem
echo ""

echo "4. Disk Space:"
df -h | grep /dev/root
echo ""

echo "5. CPU Temperature:"
vcgencmd measure_temp
echo ""

echo "6. Database Status:"
ls -lh /home/pi/sec_cam/events.db
sqlite3 /home/pi/sec_cam/events.db "SELECT COUNT(*) FROM events;" 2>&1 | head -1
echo ""

echo "7. Recent Errors:"
sudo journalctl -u sec-cam -p err --since "1 hour ago" --no-pager | tail -5
echo ""

echo "8. Web Server:"
curl -I http://localhost/ 2>&1 | head -1
echo ""

echo "=== Check Complete ==="
```

### Common Issues & Solutions

**Issue: "Camera is not detected"**

Solution:
```bash
# Enable camera
sudo raspi-config
# Interface Options → Camera → Enable
sudo reboot

# Verify
vcgencmd get_camera
# Should show: supported=1 detected=1
```

**Issue: "Database locked"**

Solution:
```bash
# Check what's accessing database
lsof /home/pi/sec_cam/events.db

# Restart services
sudo systemctl restart sec-cam
sudo systemctl restart nginx
```

**Issue: "Motion detection not triggering"**

Diagnosis:
```bash
# Watch for motion debug logs
sudo journalctl -u sec-cam -f | grep -i motion

# Check current settings
grep MOTION_ /home/pi/sec_cam/config.py

# Check streaming flag (motion pauses during stream)
sqlite3 /home/pi/sec_cam/events.db "SELECT * FROM system_control;"
```

Solution:
```python
# Edit config.py - make more sensitive
MOTION_SENSITIVITY = 30  # Lower = more sensitive
MOTION_THRESHOLD = 40
```

**Issue: "Out of memory"**

Solution:
```bash
# Check memory usage
free -h
ps aux | grep python

# Stop streaming
# Go to Live View → Stop Stream

# Reduce buffer size
nano /home/pi/sec_cam/config.py
# Set: CIRCULAR_BUFFER_MAX_CHUNKS = 600

sudo systemctl restart sec-cam
```

**Issue: "Video won't play in browser"**

Check:
```bash
# Verify MP4 file exists and is valid
ls -lh /home/pi/sec_cam/videos/
file /home/pi/sec_cam/videos/[filename].mp4

# Check nginx can serve it
curl -I http://localhost/videos/[filename].mp4
```

**Issue: "Stream stuck on 'Starting...'"**

Diagnosis:
```bash
# Check MJPEG server
sudo journalctl -u sec-cam -f | grep -i mjpeg

# Test stream directly
curl -I http://localhost:8080/stream.mjpg

# Check streaming flag
sqlite3 /home/pi/sec_cam/events.db "SELECT * FROM system_control;"
```

Solution:
```bash
# Reset streaming flag
sqlite3 /home/pi/sec_cam/events.db \
  "UPDATE system_control SET streaming=0 WHERE id=1;"

# Restart service
sudo systemctl restart sec-cam

# Try stream again
```

---

## System Recovery

### Soft Recovery (Restart Service)
```bash
sudo systemctl restart sec-cam
```

### Hard Recovery (Kill All Python)
```bash
# Stop service
sudo systemctl stop sec-cam

# Kill all Python processes
sudo /home/pi/sec_cam/killpython.sh

# Wait 5 seconds
sleep 5

# Start service
sudo systemctl start sec-cam
```

### Database Recovery

**If database corrupted:**
```bash
# Stop service
sudo systemctl stop sec-cam

# Attempt to recover
sqlite3 events.db ".recover" > recovered.sql

# Create new database
mv events.db events.db.corrupted
sqlite3 events.db < recovered.sql

# Restart
sudo systemctl start sec-cam
```

**If recovery fails, restore from backup:**
```bash
sudo systemctl stop sec-cam
cp /path/to/backup/events.db ./events.db
chmod 664 events.db
sudo systemctl start sec-cam
```

### Complete System Reinstall

**Preserve data:**
```bash
# Backup critical files
cp events.db ~/events.db.backup
cp config.py ~/config.py.backup
tar -czf ~/videos_backup.tar.gz videos/
```

**Reinstall:**
```bash
cd /home/pi
rm -rf sec_cam
git clone https://github.com/kklasmeier/security-camera.git sec_cam
cd sec_cam
chmod +x setup.sh
./setup.sh
```

**Restore data:**
```bash
sudo systemctl stop sec-cam
cp ~/events.db.backup events.db
cp ~/config.py.backup config.py
tar -xzf ~/videos_backup.tar.gz
sudo systemctl start sec-cam
```

---

## Appendix

### File Permissions Reference
```bash
# Correct permissions
chmod 755 /home/pi/sec_cam
chmod 755 videos pictures thumbs www
chmod 664 events.db
chmod 644 www/*.php www/includes/*.php www/assets/*
chmod 755 www/api
chmod 644 www/api/*.php
```

### Port Reference

- **80** - nginx (web interface)
- **8080** - MJPEG streaming server
- **9000** - PHP-FPM (internal only)

### Resource Limits

**Pi Zero 2 W (512MB RAM):**
- System: ~100MB
- Camera: ~260MB normal, ~280MB streaming
- Free: ~150MB (minimum safe)

**Storage:**
- Event: ~2-3MB (30s video + images)
- Daily: ~50-100MB (varies by activity)
- Monthly: ~1.5-3GB

### Useful Scripts Location
```bash
# All scripts in project directory
cd /home/pi/sec_cam

./setup.sh           # Deployment
./gitsync.sh         # Git helper
./run.sh             # Manual run
./killpython.sh      # Emergency stop
./convert_pending.sh # Video conversion
```

---

## Contact & Support

For issues or questions:
1. Review this admin guide
2. Check logs: `sudo journalctl -u sec-cam -n 100`
3. Review [DEPLOYMENT.md](DEPLOYMENT.md) for setup issues
4. Check GitHub: https://github.com/kklasmeier/security-camera/issues

---

**Last Updated:** October 2025  
**Version:** 1.0  
**Maintainer:** Kevin Klasmeier
