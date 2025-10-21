# Security Camera System - Deployment Guide

Complete step-by-step instructions for deploying this system on a Raspberry Pi Zero 2 W.

---

## Table of Contents

1. [Hardware Requirements](#hardware-requirements)
2. [Software Prerequisites](#software-prerequisites)
3. [Initial Pi Setup](#initial-pi-setup)
4. [System Deployment](#system-deployment)
5. [Verification & Testing](#verification--testing)
6. [Troubleshooting](#troubleshooting)
7. [Updating Existing Installation](#updating-existing-installation)

---

## Hardware Requirements

### Required Components
- **Raspberry Pi Zero 2 W** (512MB RAM)
- **Camera Module** (v2 or v3 recommended)
- **MicroSD Card** (32GB+ recommended, Class 10 or better)
- **Power Supply** (5V 2.5A minimum)
- **Camera Cable** (15-pin for Pi Zero)

### Optional Components
- Case with camera mount
- Heatsink for Pi Zero 2 W
- LED indicator (system status)

---

## Software Prerequisites

### Raspberry Pi OS
- **OS Version:** Raspberry Pi OS Lite (64-bit) or Desktop
- **Kernel:** 6.1+ (for best picamera2 support)
- **Python:** 3.11+ (included in current OS)

### Check Current Version
```bash
cat /etc/os-release
uname -r
python3 --version
```

---

## Initial Pi Setup

### 1. Flash SD Card

Use [Raspberry Pi Imager](https://www.raspberrypi.com/software/):
1. Choose OS: "Raspberry Pi OS (64-bit)"
2. Configure settings (gear icon):
   - Set hostname: `piCameraFront2` (or your preference)
   - Enable SSH
   - Set username/password: `pi` / [your password]
   - Configure WiFi (if using wireless)
3. Write to SD card

### 2. First Boot
```bash
# SSH into Pi
ssh pi@piCameraFront2.local
# or
ssh pi@[IP-ADDRESS]

# Update system
sudo apt update && sudo apt upgrade -y

# Enable camera interface
sudo raspi-config
# Navigate to: Interface Options → Camera → Enable
# Reboot when prompted

# Verify camera detected
vcgencmd get_camera
# Should show: supported=1 detected=1
```

### 3. Set Timezone (Important!)
```bash
sudo raspi-config
# Navigate to: Localisation Options → Timezone
# Select your timezone (e.g., America/New_York)

# Verify
timedatectl
```

**Why this matters:** Timestamps in events and logs will be incorrect if timezone is wrong.

---

## System Deployment

### Step 1: Install Dependencies
```bash
# Update package list
sudo apt update

# Install required packages
sudo apt install -y \
    git \
    nginx \
    php-fpm \
    php-sqlite3 \
    python3-picamera2 \
    python3-opencv \
    python3-pil \
    sqlite3

# Verify installations
git --version          # Should show git 2.x
nginx -v               # Should show nginx 1.x
php --version          # Should show PHP 8.x
python3 --version      # Should show Python 3.11+
```

### Step 2: Clone Repository
```bash
# Navigate to home directory
cd /home/pi

# Clone from GitHub
git clone https://github.com/kklasmeier/security-camera.git sec_cam

# Enter project directory
cd sec_cam

# Verify files present
ls -la
# Should see: Python files, www/, setup.sh, etc.
```

### Step 3: Run Setup Script
```bash
# Make setup script executable
chmod +x setup.sh

# Run setup (creates directories, configures nginx, sets up service)
./setup.sh
```

**The setup script will:**
- ✅ Create required directories (`videos/`, `pictures/`, `thumbs/`, `logs/`)
- ✅ Set file permissions
- ✅ Configure nginx web server
- ✅ Install systemd service
- ✅ Enable auto-start on boot
- ✅ Verify all dependencies

**Expected output:**
```
================================================
Security Camera System - Setup
================================================

✓ Running as pi user
✓ In correct directory
✓ Directories created
✓ Permissions set
✓ nginx installed
✓ PHP installed
✓ nginx configured
✓ nginx restarted
✓ Systemd service installed and enabled

================================================
✓ Setup complete!
================================================
```

### Step 4: Start System
```bash
# Start camera system
sudo systemctl start sec-cam

# Check status
sudo systemctl status sec-cam
```

**Expected output:**
```
● sec-cam.service - Security Camera System
     Loaded: loaded (/etc/systemd/system/sec-cam.service; enabled)
     Active: active (running) since ...
```

### Step 5: View Logs (Optional)
```bash
# Watch logs in real-time
sudo journalctl -u sec-cam -f

# Press Ctrl+C to exit

# Expected log messages:
# - "System initializing..."
# - "Database schema initialized successfully"
# - "Camera and Circular Buffer initialized"
# - "Motion detection started"
# - "System started successfully"
```

---

## Verification & Testing

### Check Web Interface

1. **Find Pi's IP address:**
```bash
   hostname -I
```

2. **Open in browser:**
```
   http://[PI-IP-ADDRESS]/
```

3. **Verify all pages load:**
   - Events page (home) - should show "No events" initially
   - Event Detail - N/A until motion detected
   - Live View - should show camera feed
   - Logs - should show system logs

### Test Motion Detection

1. **Trigger motion in front of camera**
   - Wave hand, walk past, etc.

2. **Wait 30-60 seconds** for event processing

3. **Check Events page** - should show new event with thumbnail

4. **Click event** - should show video and images

### Test Live Streaming

1. **Go to Live View page**
2. Should auto-start stream
3. Verify real-time video at ~10fps
4. Click "Stop Stream" - should stop
5. Check logs: `sudo journalctl -u sec-cam -f | grep -i mjpeg`

### Verify Database
```bash
# Check database created
ls -lh /home/pi/sec_cam/events.db

# Query database
sqlite3 /home/pi/sec_cam/events.db

# At sqlite prompt:
sqlite> .tables
# Should show: events  logs  system_control

sqlite> SELECT COUNT(*) FROM events;
# Should show event count

sqlite> SELECT COUNT(*) FROM logs;
# Should show log count

sqlite> .quit
```

### Check System Resources
```bash
# Memory usage
free -h
# Camera system should use ~260MB

# Disk space
df -h
# Should have plenty of free space

# CPU temperature
vcgencmd measure_temp
# Should be under 70°C
```

---

## Troubleshooting

### Camera Won't Start

**Symptom:** Service fails to start or immediately stops

**Check logs:**
```bash
sudo journalctl -u sec-cam -n 50
```

**Common causes:**

1. **Camera not enabled:**
```bash
   sudo raspi-config
   # Interface Options → Camera → Enable
   # Reboot
```

2. **Camera not detected:**
```bash
   vcgencmd get_camera
   # Should show: supported=1 detected=1
   
   # If not detected, check cable connection
```

3. **Camera in use by another process:**
```bash
   sudo lsof | grep video
   
   # If something is using it, kill that process
   sudo pkill -9 [process-name]
```

4. **Permissions issue:**
```bash
   # Add pi user to video group
   sudo usermod -a -G video pi
   
   # Reboot
   sudo reboot
```

### Web Pages Not Loading

**Symptom:** Browser shows "Connection refused" or "404 Not Found"

**Check nginx:**
```bash
sudo systemctl status nginx

# If not running:
sudo systemctl start nginx

# Test configuration:
sudo nginx -t

# View error log:
sudo tail -f /var/log/nginx/sec-cam-error.log
```

**Check PHP-FPM:**
```bash
sudo systemctl status php8.4-fpm
# (or php7.4-fpm, php8.2-fpm - check your version)

# If not running:
sudo systemctl start php8.4-fpm
```

**Check file permissions:**
```bash
ls -la /home/pi/sec_cam/www/
# Files should be readable (644)
# Directories should be executable (755)

# If wrong:
chmod 755 /home/pi/sec_cam/www
chmod 644 /home/pi/sec_cam/www/*.php
```

### Motion Detection Not Working

**Symptom:** No events captured despite motion

**Check motion detection status:**
```bash
sudo journalctl -u sec-cam -f | grep -i motion
```

**Common causes:**

1. **Motion detection paused (streaming active):**
```bash
   # Check streaming flag
   sqlite3 /home/pi/sec_cam/events.db "SELECT * FROM system_control;"
   
   # If streaming=1, reset it:
   sqlite3 /home/pi/sec_cam/events.db "UPDATE system_control SET streaming=0 WHERE id=1;"
   
   # Restart service
   sudo systemctl restart sec-cam
```

2. **Sensitivity too low:**
```bash
   # Edit config
   nano /home/pi/sec_cam/config.py
   
   # Try lower MOTION_SENSITIVITY (e.g., 30 instead of 50)
   # Save and restart:
   sudo systemctl restart sec-cam
```

3. **Camera view obstructed:**
   - Check camera lens is clean
   - Verify camera has view of area with motion

### High Memory Usage

**Symptom:** System slow, or out-of-memory errors

**Check memory:**
```bash
free -h
ps aux | grep python | head -5
```

**Solutions:**

1. **Stop streaming if active:**
   - Go to Live View → Stop Stream

2. **Reduce buffer size:**
```bash
   nano /home/pi/sec_cam/config.py
   
   # Reduce CIRCULAR_BUFFER_MAX_CHUNKS
   # From 1000 to 600
   
   sudo systemctl restart sec-cam
```

3. **Lower video quality:**
```bash
   nano /home/pi/sec_cam/config.py
   
   # Reduce VIDEO_BITRATE
   # From 3000000 to 2000000
   
   sudo systemctl restart sec-cam
```

### Database Locked

**Symptom:** Web pages show database errors

**Check for locks:**
```bash
lsof /home/pi/sec_cam/events.db
```

**Solution:**
```bash
# Restart services
sudo systemctl restart sec-cam
sudo systemctl restart nginx
```

### Stream Won't Start

**Symptom:** Live view shows "Starting..." but never loads

**Check MJPEG server:**
```bash
sudo journalctl -u sec-cam -f | grep -i mjpeg

# Should see:
# "MJPEG server monitor started"
# "MJPEG monitor: Streaming flag = 1, starting server"
# "MJPEG HTTP server started on port 8080"
```

**Test stream directly:**
```bash
curl -I http://localhost:8080/stream.mjpg

# Should return:
# HTTP/1.0 200 OK
# Content-Type: multipart/x-mixed-replace; boundary=frame
```

**If port 8080 in use:**
```bash
# Check what's using it
sudo lsof -i :8080

# Kill that process or change port in config.py
```

---

## Updating Existing Installation

### Pull Latest Code from GitHub
```bash
cd /home/pi/sec_cam

# Pull updates
git pull

# Restart service to apply changes
sudo systemctl restart sec-cam

# Verify
sudo systemctl status sec-cam
```

### If Setup Files Changed
```bash
# Re-run setup script
./setup.sh

# This will update:
# - nginx configuration
# - systemd service file
# - File permissions
```

### Database Schema Updates

If database schema changed (rare), the system handles it automatically:
- New tables/columns created on startup
- Existing data preserved

**Manual schema update (if needed):**
```bash
# Backup first!
cp events.db events.db.backup

# Connect to database
sqlite3 events.db

# Run schema updates manually (if provided)
# ...

# Exit
.quit
```

---

## Performance Tuning

### For Better Performance

**Reduce motion detection frequency:**
```python
# config.py
PICTURE_CAPTURE_INTERVAL = 1.0  # From 0.5 (checks motion less often)
```

**Lower video quality:**
```python
# config.py
VIDEO_BITRATE = 2000000  # From 3000000 (smaller file sizes)
VIDEO_RESOLUTION = (1280, 720)  # From (1920, 1080) if needed
```

**Increase cooldown:**
```python
# config.py
MOTION_COOLDOWN_SECONDS = 90  # From 65 (fewer events, less processing)
```

### For Better Quality

**Higher sensitivity (more events):**
```python
# config.py
MOTION_SENSITIVITY = 30  # From 50 (more sensitive)
```

**Better video quality:**
```python
# config.py
VIDEO_BITRATE = 5000000  # From 3000000 (larger files, better quality)
```

---

## System Maintenance

### Daily Checks
```bash
# Check system is running
sudo systemctl status sec-cam

# Check memory usage
free -h

# Check disk space
df -h
```

### Weekly Tasks
```bash
# Review error logs
sudo journalctl -u sec-cam -p err --since "1 week ago"

# Check event count
sqlite3 /home/pi/sec_cam/events.db "SELECT COUNT(*) FROM events;"

# Check oldest video (for cleanup)
ls -lt /home/pi/sec_cam/videos/ | tail -5
```

### Monthly Tasks
```bash
# Backup database
cp /home/pi/sec_cam/events.db \
   /home/pi/sec_cam/events.db.backup.$(date +%Y%m%d)

# Vacuum database (optimize)
sqlite3 /home/pi/sec_cam/events.db "VACUUM;"

# Clean old videos (example: delete >30 days)
find /home/pi/sec_cam/videos/ -name "*.mp4" -mtime +30 -delete
find /home/pi/sec_cam/pictures/ -name "*.jpg" -mtime +30 -delete
find /home/pi/sec_cam/thumbs/ -name "*.jpg" -mtime +30 -delete
```

---

## Quick Reference Commands
```bash
# Start/Stop/Restart
sudo systemctl start sec-cam
sudo systemctl stop sec-cam
sudo systemctl restart sec-cam

# Status & Logs
sudo systemctl status sec-cam
sudo journalctl -u sec-cam -f
sudo journalctl -u sec-cam -n 100

# Database
sqlite3 /home/pi/sec_cam/events.db
sqlite3 /home/pi/sec_cam/events.db "SELECT COUNT(*) FROM events;"

# System Info
hostname -I          # Get IP address
vcgencmd measure_temp  # CPU temperature
free -h              # Memory usage
df -h                # Disk space

# Web Server
sudo systemctl restart nginx
sudo nginx -t        # Test config
sudo tail -f /var/log/nginx/sec-cam-error.log

# Updates
cd /home/pi/sec_cam
git pull
sudo systemctl restart sec-cam
```

---

## Additional Resources

- **Main README:** [README.md](README.md)
- **Admin Guide:** [ADMIN.md](ADMIN.md) (if created)
- **GitHub Repository:** https://github.com/kklasmeier/security-camera
- **Raspberry Pi Documentation:** https://www.raspberrypi.com/documentation/
- **picamera2 Documentation:** https://datasheets.raspberrypi.com/camera/picamera2-manual.pdf

---

## Support

For issues or questions:
1. Check this deployment guide
2. Review logs: `sudo journalctl -u sec-cam -n 100`
3. Check GitHub Issues: https://github.com/kklasmeier/security-camera/issues

---

**Last Updated:** October 2025  
**Version:** 1.0  
**Author:** Kevin Klasmeier`
