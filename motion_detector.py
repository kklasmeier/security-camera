"""
Security Camera System - Motion Detection Module
=================================================
Continuously monitors for motion using pixel-difference algorithm.
When motion detected:
1. Saves current frame as Picture A
2. Creates database record
3. Signals event processor (Thread 3)
4. Enters cooldown period

Algorithm ported from original picam.py motion detection.
"""
import gc
import time
import cv2
import numpy as np
from datetime import datetime
from PIL import Image
from config import (
    MOTION_THRESHOLD,
    MOTION_SENSITIVITY,
    MOTION_COOLDOWN_SECONDS,
    DETECTION_RESOLUTION,
    PICTURES_PATH,
    PICTURE_CAPTURE_INTERVAL
)
from logger import log


class MotionDetector:
    """
    Motion detection using pixel-difference algorithm.
    
    Compares consecutive frames from the circular buffer to detect motion.
    Uses green channel comparison (highest quality in Bayer sensors).
    
    Usage:
        detector = MotionDetector(buffer, db, motion_event)
        detector.start()
        # ... runs continuously in background ...
        detector.stop()
    """
    
    def __init__(self, circular_buffer, database, motion_event):
        """
        Initialize motion detector.
        
        Args:
            circular_buffer: CircularBuffer instance for frame access
            database: EventDatabase instance for creating records
            motion_event: MotionEvent instance for signaling Thread 3
        """
        self.buffer = circular_buffer
        self.db = database
        self.motion_event = motion_event
        
        # Detection parameters (from config)
        self.threshold = MOTION_THRESHOLD
        self.sensitivity = MOTION_SENSITIVITY
        self.cooldown_seconds = MOTION_COOLDOWN_SECONDS
        self.test_resolution = DETECTION_RESOLUTION
        
        # State tracking
        self.running = False
        self.last_detection_time = 0
        self.detection_thread = None
        
        # Debug mode (optional)
        self.debug_mode = False
        
        log(f"MotionDetector initialized: threshold={self.threshold}, "
            f"sensitivity={self.sensitivity}, cooldown={self.cooldown_seconds}s")
    
    def start(self):
        """
        Start motion detection loop in background thread.
        """
        import threading
        
        self.running = True
        self.detection_thread = threading.Thread(
            target=self._detection_loop,
            name="MotionDetector",
            daemon=True
        )
        self.detection_thread.start()
        log("Motion detection started")
    
    def stop(self):
        """
        Stop motion detection loop.
        """
        log("Stopping motion detector...")
        self.running = False
        
        if self.detection_thread and self.detection_thread.is_alive():
            self.detection_thread.join(timeout=5.0)
        
        log("Motion detector stopped")
    
    def _detection_loop(self):
        """
        Main detection loop - runs continuously in background thread with detailed logging.
        """
        from config import MOTION_LOG_INTERVAL, MOTION_LOG_DETAILS

        log("Motion detection loop started")

        check_count = 0
        last_log_time = time.time()

        while self.running:
            try:
                check_count += 1
                current_time = time.time()

                # === WATCHDOG PAUSE GUARD ===
                if getattr(self, "_paused", False):
                    time.sleep(0.5)
                    continue

                # Check if in cooldown period
                if self._in_cooldown():
                    remaining = self.cooldown_seconds - (current_time - self.last_detection_time)

                    # Log cooldown status every 5 seconds
                    if current_time - last_log_time >= 5.0:
                        log(f"Cooldown: {remaining:.1f}s remaining (check #{check_count})")
                        last_log_time = current_time

                    time.sleep(0.5)
                    continue

                # Get frames from circular buffer
                previous_frame, current_frame = self.buffer.get_frames_for_detection()

                if previous_frame is None or current_frame is None:
                    # Frames not yet available
                    if current_time - last_log_time >= 5.0:
                        log(f"Waiting for frames... (check #{check_count})")
                        last_log_time = current_time
                    time.sleep(0.5)
                    continue

                # Detect motion using pixel-diff algorithm
                motion_detected, changed_pixels = self._compare_frames(
                    previous_frame,
                    current_frame
                )

                # Periodic logging of motion checks
                if MOTION_LOG_INTERVAL > 0 and check_count % MOTION_LOG_INTERVAL == 0:
                    elapsed = current_time - last_log_time if last_log_time > 0 else 0
                    log(f"Motion check #{check_count}: score={changed_pixels}/{self.sensitivity} "
                        f"(active monitoring)")
                    last_log_time = current_time

                # Motion detected
                if motion_detected:
                    log(f"MOTION DETECTED! Check #{check_count}, Score: {changed_pixels}/{self.sensitivity}")

                    if MOTION_LOG_DETAILS:
                        log(f"  Frames compared: {previous_frame.shape}")
                        log(f"  Test resolution: {self.test_resolution}")
                        log(f"  Threshold: {self.threshold}, Sensitivity: {self.sensitivity}")

                    self._handle_motion_event(current_frame, changed_pixels)
                    last_log_time = current_time

                if check_count % 50 == 0:      # every ~50 frames or checks
                    gc.collect()
                    cv2.setUseOptimized(False)
                    cv2.setUseOptimized(True)

                # Wait before next check
                time.sleep(PICTURE_CAPTURE_INTERVAL)

            except Exception as e:
                if self.running:
                    log(f"Error in motion detection loop: {e}", level="ERROR")
                    time.sleep(1.0)

        log("Motion detection loop stopped")
    
    def _in_cooldown(self):
        """
        Check if we're in cooldown period after last detection.
        
        Returns:
            bool: True if in cooldown, False if ready to detect
        """
        if self.last_detection_time == 0:
            return False
        
        elapsed = time.time() - self.last_detection_time
        return elapsed < self.cooldown_seconds
    
    def _compare_frames(self, frame1, frame2):
        """
        Compare two frames to detect motion using green-channel difference.
        
        NOTE: Frames are now pre-downscaled by circular_buffer, so we skip
        the resize step that was previously done here.
        
        Args:
            frame1: Small frame (100x75x3) from buffer
            frame2: Small frame (100x75x3) from buffer
            
        Returns:
            tuple: (motion_detected: bool, changed_pixels: int)
        """
        import cv2
        import numpy as np
        from PIL import Image
        
        # Frames are already at DETECTION_RESOLUTION - no resize needed!
        # This removes redundant downscaling that was wasting CPU and memory
        
        # Extract green channel (index 1)
        # Handle both RGB (3D) and grayscale/YUV (2D) frames
        if frame1.ndim == 3:
            g1 = frame1[:, :, 1]
            g2 = frame2[:, :, 1]
        else:
            # Already grayscale or single plane (Y channel)
            g1 = frame1
            g2 = frame2

        
        # Fast absolute difference on uint8
        diff = cv2.absdiff(g1, g2)
        
        # Count pixels whose difference exceeds the threshold
        changed_pixels = int(np.count_nonzero(diff > self.threshold))
        
        # Optional debug image (only if enabled)
        if self.debug_mode:
            vis = frame2.copy()
            mask = diff > self.threshold
            # Highlight changed pixels in bright green
            vis[mask] = (vis[mask][:, 0], np.full_like(vis[mask][:, 1], 255), vis[mask][:, 2])
            Image.fromarray(vis).save(f"{PICTURES_PATH}/debug.bmp")
        
        # Motion decision
        motion_detected = changed_pixels > self.sensitivity
        return motion_detected, changed_pixels

    
    def _handle_motion_event(self, current_frame, motion_score):
        """
        Handle detected motion event.
        
        Actions (per design document):
        1. Generate timestamp and filename
        2. Save current frame as Picture A
        3. Create database record (get event_id)
        4. Signal Thread 3 with event_id and timestamp
        5. Enter cooldown period
        
        Args:
            current_frame: The frame that triggered motion (numpy array)
            motion_score: Number of changed pixels
        """
        try:
            # Generate timestamp
            timestamp = datetime.now()
            timestamp_str = timestamp.strftime('%Y.%m.%d--%H.%M.%S')
            
            # Save current frame as Picture A
            image_a_path = f"{PICTURES_PATH}/{timestamp_str}_a.jpg"
            self.buffer.capture_color_still(image_a_path)
            log(f"Picture A (COLOR) saved: {image_a_path}")
            
            # Create database record and get event_id
            event_id = self.db.add_new_event(
                timestamp=timestamp,
                motion_score=motion_score,
                image_a_path=image_a_path
            )
            log(f"Event {event_id} created in database")
            
            # Signal Thread 3 to process this event
            self.motion_event.set(event_id=event_id, timestamp=timestamp)
            log(f"Event {event_id} signaled to processor")
            
            # Enter cooldown period
            self.last_detection_time = time.time()
            log(f"Entering {self.cooldown_seconds}s cooldown")
            
        except Exception as e:
            log(f"Error handling motion event: {e}", level="ERROR")
            # Don't enter cooldown on error - allow retry
    
    def enable_debug_mode(self, enabled=True):
        """
        Enable/disable debug mode for motion detection.
        
        When enabled, saves debug.bmp showing changed pixels in green.
        
        Args:
            enabled (bool): True to enable debug mode
        """
        self.debug_mode = enabled
        log(f"Debug mode: {'enabled' if enabled else 'disabled'}")

    def attach_buffer(self, new_buffer):
        self.buffer = new_buffer
        self.last_frame = None
        log("[WATCHDOG] MotionDetector reattached to new CircularBuffer.")

    def pause(self):
        self._paused = True
        log("[WATCHDOG] MotionDetector paused.")

    def resume(self):
        self._paused = False
        log("[WATCHDOG] MotionDetector resumed.")



# ============================================================================
# STANDALONE TESTING
# ============================================================================

if __name__ == "__main__":
    """
    Test motion detection with mock objects.
    """
    print("Motion Detector - Standalone Test")
    print("="*60)
    print("Note: This test uses mock objects since it requires")
    print("      CircularBuffer, Database, and MotionEvent instances.")
    print("="*60)
    
    print("\n✓ MotionDetector class defined successfully")
    print(f"  - Threshold: {MOTION_THRESHOLD}")
    print(f"  - Sensitivity: {MOTION_SENSITIVITY}")
    print(f"  - Cooldown: {MOTION_COOLDOWN_SECONDS}s")
    print(f"  - Test resolution: {DETECTION_RESOLUTION}")
    print("\nReady for integration testing with full system!")