#!/bin/bash
# convert_pending.sh — safely converts .h264 files (with .pending marker) into .mp4
# Adds a lock mechanism to prevent overlapping runs.
# Logs CMA and RAM usage even if conversion is skipped.

VIDEOS_DIR="/home/pi/sec_cam/videos"
LOGFILE="/home/pi/sec_cam/logs/convert_pending.log"
LOCKFILE="/tmp/convert_pending.lock"
PATH="/usr/local/bin:/usr/bin:/bin"

# --- Try to acquire lock ---
exec 200>"$LOCKFILE"
if ! flock -n 200; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Another conversion is still running — skipping this cycle." >> "$LOGFILE"

    # Even if skipping, log memory snapshot for diagnostics
    CMA_TOTAL_KB=$(grep CmaTotal /proc/meminfo | awk '{print $2}')
    CMA_FREE_KB=$(grep CmaFree /proc/meminfo | awk '{print $2}')
    CMA_TOTAL_MB=$(awk -v kb="$CMA_TOTAL_KB" 'BEGIN {printf "%.2f", kb/1024}')
    CMA_FREE_MB=$(awk -v kb="$CMA_FREE_KB" 'BEGIN {printf "%.2f", kb/1024}')
    RAM_FREE=$(awk '/MemAvailable/ {print int($2/1024)}' /proc/meminfo)
    SWAP_USED=$(free -m | awk '/Swap:/ {print $3}')

    echo "[$(date '+%Y-%m-%d %H:%M:%S')] CMA Free=${CMA_FREE_MB}MB / Total=${CMA_TOTAL_MB}MB | RAM Free=${RAM_FREE}MB | Swap Used=${SWAP_USED}MB" >> "$LOGFILE"
    exit 0
fi

# --- Log CMA + memory snapshot (in MB) ---
CMA_TOTAL_KB=$(grep CmaTotal /proc/meminfo | awk '{print $2}')
CMA_FREE_KB=$(grep CmaFree /proc/meminfo | awk '{print $2}')
CMA_TOTAL_MB=$(awk -v kb="$CMA_TOTAL_KB" 'BEGIN {printf "%.2f", kb/1024}')
CMA_FREE_MB=$(awk -v kb="$CMA_FREE_KB" 'BEGIN {printf "%.2f", kb/1024}')
RAM_FREE=$(awk '/MemAvailable/ {print int($2/1024)}' /proc/meminfo)
SWAP_USED=$(free -m | awk '/Swap:/ {print $3}')

echo "[$(date '+%Y-%m-%d %H:%M:%S')] CMA Free=${CMA_FREE_MB}MB / Total=${CMA_TOTAL_MB}MB | RAM Free=${RAM_FREE}MB | Swap Used=${SWAP_USED}MB" >> "$LOGFILE"

# --- Memory safety: skip if low RAM ---
if [ "$RAM_FREE" -lt 175 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Skipping conversion (only ${RAM_FREE} MB free)" >> "$LOGFILE"
    exit 0
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] === Conversion job started (Free: ${RAM_FREE} MB) ===" >> "$LOGFILE"

cd "$VIDEOS_DIR" || {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: Cannot access $VIDEOS_DIR" >> "$LOGFILE"
    exit 1
}

# --- Loop through all pending marker files ---
for pending in *.h264.pending; do
    [ -e "$pending" ] || continue  # skip if none

    base="${pending%.pending}"
    h264="$base"
    mp4="${base%.h264}.mp4"

    # Skip if MP4 already exists
    if [ -f "$mp4" ]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Skipping $base (already converted)" >> "$LOGFILE"
        rm -f "$pending"
        continue
    fi

    # Skip if file still being written (<15s old)
    age=$(( $(date +%s) - $(stat -c %Y "$h264") ))
    if [ "$age" -lt 15 ]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Skipping $base (too new: ${age}s old)" >> "$LOGFILE"
        continue
    fi

    # --- Convert with minimal system impact ---
    (
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Converting $h264 → $mp4"

    /usr/local/bin/ffmpeg-lowmem -hide_banner -loglevel error -threads 1 -filter_threads 1 -thread_queue_size 4 \
        -i "$h264" -c copy -movflags faststart -y "$mp4"

    rc=$?

    if [ $rc -eq 0 ]; then
        # Get exact duration from MP4 using ffprobe
        duration=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$mp4" 2>/dev/null)
        
        if [ -n "$duration" ]; then
            # Round to nearest integer for cleaner display
            duration_int=$(printf "%.0f" "$duration")
            
            # Update database with exact duration
            # Use the full MP4 path to match the video_path in database
            sqlite3 /home/pi/sec_cam/events.db \
                "UPDATE events SET duration_seconds = $duration_int WHERE video_path = '$mp4'" 2>/dev/null
            
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✅ Converted $base (duration: ${duration_int}s)"
        else
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✅ Converted $base (duration unavailable)"
        fi
        
        # Clean up H.264 and pending marker
        rm -f "$h264" "$pending"
    else
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] ❌ Failed converting $base (rc=$rc)"
    fi
    ) >> "$LOGFILE" 2>&1

done

# --- Trim log to last 24 hours ---
TMP_FILE=$(mktemp)
awk -v cutoff="$(date -d '-24 hour' '+%Y-%m-%d %H:%M:%S')" \
    -F'|' '$0 ~ /^\[/ && substr($0,2,19) > cutoff {print $0}' "$LOGFILE" > "$TMP_FILE" && mv "$TMP_FILE" "$LOGFILE"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] === Conversion job finished ===" >> "$LOGFILE"

# --- Release lock automatically on exit ---
exit 0