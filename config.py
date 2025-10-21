"""
Security Camera System - Configuration File
============================================
All system configuration parameters in one place.
Modify these values to tune system behavior.
"""

import os

# ============================================================================
# FILE PATHS
# ============================================================================

BASE_PATH = "/home/pi/sec_cam"

DATABASE_PATH = os.path.join(BASE_PATH, "events.db")
VIDEO_PATH = os.path.join(BASE_PATH, "videos")
PICTURES_PATH = os.path.join(BASE_PATH, "pictures")
THUMBS_PATH = os.path.join(BASE_PATH, "thumbs")
TMP_PATH = os.path.join(BASE_PATH, "tmp")

# ============================================================================
# CIRCULAR BUFFER SETTINGS
# ============================================================================

# Circular buffer maintains ~17 seconds of pre-motion footage
# When motion detected, continue recording for POST_MOTION_SECONDS
# Total event duration: ~17s (buffer) + POST_MOTION_SECONDS

CIRCULAR_BUFFER_SECONDS = 20   # Target duration (approximate)
POST_MOTION_SECONDS = 12       # Continue recording after motion for this long

# Total event duration is now variable (capacity-driven buffer + continuation)
# Actual pre-motion duration depends on buffer capacity and scene complexity
# Typical total: 15-25s (buffer) + 12s (continuation) = 27-37s
TOTAL_EVENT_DURATION = 30      # Target total: ~17 + 13 = 30 seconds

# ============================================================================
# VIDEO BUFFER SETTINGS (Capacity-Driven)
# ============================================================================

# Circular buffer capacity (chunks, not time-based)
# This determines how much pre-motion footage is captured.
# Actual duration will vary based on scene complexity and motion.
# 
# Tuning guide:
# - Start with 1000 chunks (typically 15-25 seconds)
# - Monitor logs to see actual durations
# - Increase if videos too short, decrease if too long
# 
# At ~12KB per chunk average:
#   600 chunks  ≈ 7 MB  ≈ 15-20 seconds
#   1000 chunks ≈ 12 MB ≈ 20-30 seconds  (RECOMMENDED)
#   1500 chunks ≈ 18 MB ≈ 30-40 seconds
CIRCULAR_BUFFER_MAX_CHUNKS = 1000

# Maximum memory for circular buffer (bytes)
# Safety limit to prevent runaway memory usage
CIRCULAR_BUFFER_MAX_BYTES = 50 * 1024 * 1024  # 50 MB

# NOTE: BUFFER_DURATION_SECONDS removed - now capacity-driven
# The actual duration will be logged during operation

# Video resolution (width, height)
VIDEO_RESOLUTION = (1280, 720)

# Video framerate (fps)
VIDEO_FRAMERATE = 15

# H.264 bitrate (bits per second)
# 10Mbps provides good quality at 1080p
VIDEO_BITRATE = 3000000

# ============================================================================
# PICTURE CAPTURE SETTINGS
# ============================================================================

# How often to capture full-resolution frames for motion detection (seconds)
# These frames are used for both motion comparison AND saving as Picture A/B
PICTURE_CAPTURE_INTERVAL = 0.5

# JPEG quality for saved images (1-100)
JPEG_QUALITY = 80

# Thumbnail size (width, height)
THUMBNAIL_SIZE = (240, 180)

# ============================================================================
# VIDEO FORMAT SETTINGS
# ============================================================================

# Video file format
# Options: 'h264' (raw) or 'mp4' (browser-compatible)
VIDEO_OUTPUT_FORMAT = 'mp4'

# ffmpeg timeout for conversion (seconds)
FFMPEG_TIMEOUT = 10

# ============================================================================
# MOTION DETECTION SETTINGS
# ============================================================================

# Motion detection logging
MOTION_LOG_INTERVAL = 100  # Log motion check stats every N checks (0 = disable)
MOTION_LOG_DETAILS = True  # Log detailed comparison info when motion detected

# Resolution for motion detection comparison (downscaled for efficiency)
# Original frames are 1920x1080, downscaled to 100x75 for comparison
DETECTION_RESOLUTION = (100, 75)

# Threshold: how much a single pixel must change to be considered "changed"
# Range: 0-255 (higher = less sensitive to small changes)
MOTION_THRESHOLD = 60

# Sensitivity: how many pixels must change to trigger motion detection
# This is the count of changed pixels in the detection resolution frame
MOTION_SENSITIVITY = 50

# Cooldown period between motion events (seconds)
# Must be longer than Thread 3 processing time (~17s) to prevent overlaps
MOTION_COOLDOWN_SECONDS = 65

# ============================================================================
# WEB/STREAMING SETTINGS
# ============================================================================

# Port for MJPEG livestream server
LIVESTREAM_PORT = 8080

# Picture capture interval during livestream (faster for smooth stream)
# Normal operation: 0.5s (2fps), Streaming: 0.1s (10fps)
LIVESTREAM_CAPTURE_INTERVAL = 0.1

# Livestream framerate (fps)
# Lower than video recording to reduce CPU load
LIVESTREAM_FRAMERATE = 10

# JPEG quality for saved images (1-100)
# Using existing JPEG_QUALITY from PICTURE_CAPTURE_SETTINGS

# MJPEG stream quality (lower than saved images to reduce bandwidth)
LIVESTREAM_JPEG_QUALITY = 65

# ============================================================================
# LOGGING SETTINGS
# ============================================================================

# How often to flush logs to database (seconds)
# Batching reduces SD card writes
LOG_BATCH_INTERVAL = 10

# ============================================================================
# SYSTEM SETTINGS
# ============================================================================

# Camera warmup time (seconds)
# Time to allow camera to adjust exposure/white balance on startup
CAMERA_WARMUP_SECONDS = 2

# Graceful shutdown timeout (seconds)
# Maximum time to wait for threads to stop cleanly
SHUTDOWN_TIMEOUT_SECONDS = 10

# ============================================================================
# DIRECTORY CREATION
# ============================================================================

def ensure_directories():
    """
    Create all required directories if they don't exist.
    Should be called during system initialization.
    """
    directories = [
        VIDEO_PATH,
        PICTURES_PATH,
        THUMBS_PATH,
        TMP_PATH
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"Directory verified: {directory}")

# ============================================================================
# CONFIGURATION VALIDATION
# ============================================================================

def validate_config():
    """
    Validate configuration parameters for common issues.
    Raises ValueError if configuration is invalid.
    """
    # Check cooldown vs processing time
    if MOTION_COOLDOWN_SECONDS < 17:
        raise ValueError(
            f"MOTION_COOLDOWN_SECONDS ({MOTION_COOLDOWN_SECONDS}) should be >= 17 "
            "to prevent overlap with Thread 3 processing time"
        )
    
    # Check resolution
    if VIDEO_RESOLUTION not in [(1920, 1080), (1280, 720), (640, 480)]:
        print(f"Warning: Non-standard resolution {VIDEO_RESOLUTION}")
    
    # Check framerate
    if VIDEO_FRAMERATE > 30:
        print(f"Warning: High framerate {VIDEO_FRAMERATE} may strain Pi Zero 2 W")
    
    # Check buffer capacity (capacity-driven)
    if CIRCULAR_BUFFER_MAX_CHUNKS < 300:
        print(f"Warning: Low buffer capacity {CIRCULAR_BUFFER_MAX_CHUNKS} chunks "
              f"(may result in very short pre-motion footage)")
    
    if CIRCULAR_BUFFER_MAX_CHUNKS > 3000:
        print(f"Warning: High buffer capacity {CIRCULAR_BUFFER_MAX_CHUNKS} chunks "
              f"(may use excessive memory)")
    
    if CIRCULAR_BUFFER_MAX_BYTES > 100 * 1024 * 1024:
        print(f"Warning: Buffer memory limit very high "
              f"({CIRCULAR_BUFFER_MAX_BYTES/(1024*1024):.0f} MB)")
    
    print("Configuration validation complete")

# ============================================================================
# DISPLAY CONFIGURATION
# ============================================================================

def print_config():
    """
    Print current configuration for verification.
    Useful during startup and debugging.
    """
    print("\n" + "="*60)
    print("Security Camera System - Configuration")
    print("="*60)
    print(f"\nPaths:")
    print(f"  Database:   {DATABASE_PATH}")
    print(f"  Videos:     {VIDEO_PATH}")
    print(f"  Pictures:   {PICTURES_PATH}")
    print(f"  Thumbnails: {THUMBS_PATH}")
    
    print(f"\nVideo Settings:")
    print(f"  Resolution: {VIDEO_RESOLUTION[0]}x{VIDEO_RESOLUTION[1]}")
    print(f"  Framerate:  {VIDEO_FRAMERATE} fps")
    print(f"  Bitrate:    {VIDEO_BITRATE/1000000:.1f} Mbps")
    print(f"\nCircular Buffer (Capacity-Driven):")
    print(f"  Max chunks: {CIRCULAR_BUFFER_MAX_CHUNKS}")
    print(f"  Max memory: {CIRCULAR_BUFFER_MAX_BYTES/(1024*1024):.1f} MB")
    print(f"  Target:     ~{CIRCULAR_BUFFER_SECONDS}s (actual varies)")
    
    print(f"\nMotion Detection:")
    print(f"  Threshold:   {MOTION_THRESHOLD}")
    print(f"  Sensitivity: {MOTION_SENSITIVITY} pixels")
    print(f"  Cooldown:    {MOTION_COOLDOWN_SECONDS} seconds")
    print(f"  Check every: {PICTURE_CAPTURE_INTERVAL} seconds")
    
    print(f"\nStreaming:")
    print(f"  Port:        {LIVESTREAM_PORT}")
    print(f"  Framerate:   {LIVESTREAM_FRAMERATE} fps")
    
    print(f"\nLogging:")
    print(f"  Batch every: {LOG_BATCH_INTERVAL} seconds")
    
    print("="*60 + "\n")

# ============================================================================
# USAGE EXAMPLE
# ============================================================================

if __name__ == "__main__":
    """
    Run this file directly to validate and display configuration.
    """
    print("Security Camera System - Configuration Module")
    print_config()
    
    try:
        validate_config()
        print("\n✓ Configuration is valid")
    except ValueError as e:
        print(f"\n✗ Configuration error: {e}")
        exit(1)
    
    print("\nCreating directories...")
    ensure_directories()
    print("\n✓ All directories verified")