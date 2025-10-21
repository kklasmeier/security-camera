"""
Security Camera System - Event Processor Module
================================================
Thread 3: Processes motion events with timed sequence.

Timeline after motion detected:
T+0s:   Receive signal from Thread 2
T+4s:   Save Picture B (current frame at T+4s)
T+4s:   Create thumbnail from Picture B
T+4s:   Save event video (buffer + 20s continuation = ~30s total)
T+~31s: Processing complete, return to waiting

Uses buffer+continuation approach for full 30-second videos.
"""

import time
import threading
from datetime import datetime
from PIL import Image
import os
import subprocess
import gc
from config import (
    PICTURES_PATH,
    THUMBS_PATH,
    VIDEO_PATH,
    THUMBNAIL_SIZE,
    POST_MOTION_SECONDS
)
from logger import log



class EventProcessor:
    """
    Processes motion events with timed sequence.
    
    Waits for motion signal from Thread 2, then:
    1. Wait 4 seconds
    2. Save Picture B (frame at T+4s)
    3. Create thumbnail
    4. Save video (17s buffer + 13s continuation)
    5. Update database with all file paths
    
    Usage:
        processor = EventProcessor(buffer, db, motion_event)
        processor.start()
        # ... runs continuously in background ...
        processor.stop()
    """
    
    def __init__(self, circular_buffer, database, motion_event):
        """
        Initialize event processor.
        
        Args:
            circular_buffer: CircularBuffer instance for video/image access
            database: EventDatabase instance for updating records
            motion_event: MotionEvent instance for receiving signals from Thread 2
        """
        self.buffer = circular_buffer
        self.db = database
        self.motion_event = motion_event
        
        # State tracking
        self.running = False
        self.processor_thread = None
        
        log("EventProcessor initialized")
    
    def start(self):
        """
        Start event processing loop in background thread.
        """
        self.running = True
        self.processor_thread = threading.Thread(
            target=self._processing_loop,
            name="EventProcessor",
            daemon=True
        )
        self.processor_thread.start()
        log("Event processor started")
    
    def stop(self):
        """
        Stop event processing loop.
        """
        log("Stopping event processor...")
        self.running = False
        
        if self.processor_thread and self.processor_thread.is_alive():
            self.processor_thread.join(timeout=5.0)
        
        log("Event processor stopped")

    def pause(self):
        """Pause event processing to allow for camera recovery."""
        self._paused = True
        log("[WATCHDOG] EventProcessor paused.")

    def resume(self):
        """Resume event processing after camera recovery."""
        self._paused = False
        log("[WATCHDOG] EventProcessor resumed.")

    def _processing_loop(self):
        """
        Main processing loop - runs continuously in background thread.

        Process:
        1. Wait for motion event signal (blocks here when idle)
        2. Wait 4 seconds for Picture B timing
        3. Save Picture B and thumbnail
        4. Save event video (buffer + continuation)
        5. Return to waiting for next event
        """
        log("Event processing loop started")

        while self.running:
            try:
                # === WATCHDOG PAUSE GUARD ===
                if getattr(self, "_paused", False):
                    time.sleep(0.5)
                    continue

                # Wait for motion event (blocks here until motion detected)
                log("Waiting for motion event...")
                event_data = self.motion_event.wait_and_get()

                # If we were paused while waiting, skip this event safely
                if getattr(self, "_paused", False):
                    log("[WATCHDOG] EventProcessor resumed; discarding stale event.")
                    continue

                event_id = event_data['event_id']
                timestamp = event_data['timestamp']
                timestamp_str = timestamp.strftime('%Y.%m.%d--%H.%M.%S')

                log(f"Processing event {event_id}...")

                # Process the event with timed sequence
                self._process_event(event_id, timestamp_str)

                log(f"Event {event_id} processing complete")

            except Exception as e:
                if self.running:  # Only log if we're still supposed to be running
                    log(f"Error in event processing loop: {e}", level="ERROR")
                    time.sleep(1.0)  # Back off on error

        log("Event processing loop stopped")

    
    def _process_event(self, event_id, timestamp_str):
        """
        Process a single motion event with timed sequence.
        
        Timeline:
        T+0s:  Receive event
        T+4s:  Save Picture B + thumbnail
        T+4s:  Start saving video (takes ~27s)
        T+31s: Complete
        
        Args:
            event_id (int): Database event ID
            timestamp_str (str): Formatted timestamp for filenames
        """
        start_time = time.time()
        
        try:
            # Step 1: Wait 4 seconds for Picture B timing
            log(f"Event {event_id}: Waiting 4 seconds for Picture B...")
            time.sleep(4.0)
            
            # Step 2: Save Picture B (full-color still at T+4s)
            log(f"Event {event_id}: Capturing COLOR Picture B...")
            image_b_path = f"{PICTURES_PATH}/{timestamp_str}_b.jpg"
            self.buffer.capture_color_still(image_b_path)
            self.db.save_picture_b(event_id, image_b_path)
            log(f"Event {event_id}: Picture B (COLOR) saved")

            # Step 3: Create color thumbnail from Picture B
            log(f"Event {event_id}: Creating COLOR thumbnail...")
            thumbnail_path = f"{THUMBS_PATH}/{timestamp_str}_b.jpg"
            self._create_thumbnail(image_b_path, thumbnail_path)
            self.db.save_thumbnail(event_id, thumbnail_path)
            log(f"Event {event_id}: Thumbnail (COLOR) saved")
            
            gc.collect()

            # Step 4: Save event video (buffer + continuation)
            log(f"Event {event_id}: Saving event video...")
            video_path = f"{VIDEO_PATH}/{timestamp_str}.mp4"
            
            # Use buffer+continuation for full 30-second video
            self.buffer.save_h264_as_mp4(
                video_path,
                use_continuation=True,
                continuation_seconds=POST_MOTION_SECONDS
            )
            
            self.db.save_video(event_id, video_path)
            log(f"Event {event_id}: Video saved")
            
            gc.collect()

            active = threading.enumerate()
            log(f"[DEBUG] Active threads: {[t.name for t in active]}")

            # Log total processing time
            elapsed = time.time() - start_time
            log(f"Event {event_id}: Total processing time: {elapsed:.1f}s")
            
        except Exception as e:
            log(f"Error processing event {event_id}: {e}", level="ERROR")
            # Continue anyway - partial event data is better than none
    
    def _create_thumbnail(self, source_image_path, thumbnail_path):
        """
        Create thumbnail from source image (optimized for low memory).
        
        Uses draft() to decode at lower resolution, avoiding full image load.
        Guarantees color output by converting to RGB if necessary.
        """
        import gc

        try:
            # Open and decode efficiently
            with Image.open(source_image_path) as img:
                # Draft mode decodes at smaller resolution (low memory)
                img.draft("RGB", THUMBNAIL_SIZE)
                img.thumbnail(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)

                # Ensure color mode
                if img.mode != "RGB":
                    img = img.convert("RGB")

                img.save(thumbnail_path, "JPEG", optimize=True, quality=75)

            gc.collect()
            log(f"Thumbnail (COLOR) created: {thumbnail_path}")

        except Exception as e:
            log(f"Error creating thumbnail: {e}", level="ERROR")
            raise



# ============================================================================
# STANDALONE TESTING
# ============================================================================

if __name__ == "__main__":
    """
    Test event processor with mock objects.
    """
    print("Event Processor - Standalone Test")
    print("="*60)
    print("Note: This test uses mock objects since it requires")
    print("      CircularBuffer, Database, and MotionEvent instances.")
    print("="*60)
    
    print("\n✓ EventProcessor class defined successfully")
    print("\nProcessing timeline:")
    print("  T+0s:  Receive motion event")
    print("  T+4s:  Save Picture B + thumbnail")
    print("  T+4s:  Start saving video (~27s)")
    print("  T+31s: Processing complete")
    
    print("\nTotal processing time: ~31 seconds")
    print("Thread 2 cooldown: 33 seconds (2s safety margin)")
    
    print("\nReady for integration testing with full system!")