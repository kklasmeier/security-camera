
```markdown
# SECURITY CAMERA SYSTEM - MAINTENANCE/ENHANCEMENT SESSION

## Project Context

I'm working on a Raspberry Pi security camera system that I built with AI assistance over 8 sessions. The system is production-ready and deployed.

**System Overview:**
- **Hardware:** Raspberry Pi Zero 2 W (512MB RAM) + Camera Module
- **Backend:** Python with 4 threads (camera/buffer, motion detection, event processor, MJPEG streaming)
- **Frontend:** nginx + PHP 8.4 + JavaScript (responsive web interface)
- **Database:** SQLite with WAL mode
- **Storage:** Videos (MP4), pictures (JPEG), thumbnails
- **Repository:** https://github.com/kklasmeier/security-camera

**Key Features:**
- Motion detection with automatic 30-second video recording
- Web interface for browsing events, viewing logs, live streaming
- 4-page responsive web design (Events, Event Detail, Logs, Live View)
- Automatic database schema creation
- Multi-device deployment via setup script

**Architecture (4 Python Threads):**
- Thread 1: CircularBuffer (camera + H.264 recording, capacity-driven buffer)
- Thread 2: MotionDetector (pixel-difference algorithm, pauses during streaming)
- Thread 3: EventProcessor (saves pictures A/B, thumbnail, video)
- Thread 4: MJPEGServer (live streaming at 10fps, polls database flag)

**File Structure:**
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

## Important Technical Details

**Memory Constraints:**
- Pi Zero 2 W: Only 512MB RAM total
- Camera system uses ~260MB normally, ~280MB during streaming
- Must be memory-efficient (why PHP was chosen over Flask)

**State Management:**
- Database flag for streaming control (PHP writes, Python polls every 1 second)
- Method calls for Python thread coordination (no globals)
- Motion detection auto-pauses during streaming

**Known Quirks:**
- No emoji rendering on system - use symbols (●) or images
- Timezone must be set to `America/New_York` in functions.php
- Database timestamps in ISO format: `2025-10-19T20:43:04.186476`
- MJPEG server strips query strings from URLs (cache-busting support)
- Circular buffer is capacity-driven (chunks, not time-based)

**Database Schema:**
- `events` table: id, timestamp, motion_score, image paths, video_path, duration_seconds, AI fields (future), timestamps
- `logs` table: id, timestamp, level (INFO/WARNING/ERROR), message
- `system_control` table: id=1, streaming (0/1), updated_at

**Configuration (config.py):**
- Motion: THRESHOLD=60, SENSITIVITY=50, COOLDOWN=65s
- Video: 1280x720@15fps, 3Mbps bitrate
- Buffer: 1000 chunks max (capacity-driven, ~15-25s pre-motion)
- Streaming: Port 8080, 10fps, JPEG quality 65%

**Git Workflow:**
- Code synced to GitHub via `./gitsync.sh`
- `.gitignore` excludes database and media files
- SSH keys configured for authentication
- Deployed via: `git clone` → `./setup.sh` → `systemctl start sec-cam`

## Current Issue / Enhancement Request

[DESCRIBE YOUR ISSUE OR ENHANCEMENT HERE]

**What I want to accomplish:**
- [Be specific about the goal]

**Current behavior (if bug):**
- [What's happening now]

**Expected behavior:**
- [What should happen]

**Files likely involved:**
- [List any files you think are relevant, or say "not sure"]

**Error messages (if any):**
```
[Paste any error messages from logs]
```

**System status:**
- Service running: [yes/no]
- Recent changes: [any recent modifications]
- Logs checked: [yes/no - paste relevant logs if available]

## Request to AI

Please help me [fix this issue / implement this enhancement / troubleshoot this problem].

**Approach preference:**
- [ ] Provide complete working code (preferred - I'm a product owner, not a developer)
- [ ] Guide me step-by-step
- [ ] Explain the approach first, then code

**Testing:**
- [ ] I can test changes immediately
- [ ] I need testing instructions
- [ ] This is for a future deployment

**Constraints:**
- Must maintain memory efficiency (Pi Zero 2 W has only 512MB RAM)
- Must not break existing functionality
- Should follow existing code patterns
- Must preserve data (events, videos) during changes

**Additional context:**
[Any other relevant information]

---

## After Session: Update Documentation

If this change is significant, remind me to:
- [ ] Update README.md (if user-facing feature)
- [ ] Update DEPLOYMENT.md (if affects setup)
- [ ] Update ADMIN.md (if affects maintenance)
- [ ] Update CHANGELOG.md (if we create one)
- [ ] Commit and push to GitHub: `./gitsync.sh`
```

