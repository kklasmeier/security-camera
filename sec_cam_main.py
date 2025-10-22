#!/usr/bin/env python3
"""
Security Camera System - Main Orchestrator
===========================================
Initializes and coordinates all system components.

Architecture:
- Main Thread:  Orchestrator (this file)
- Thread 1:     Camera and Circular Buffer
- Thread 2:     Motion Detection
- Thread 3:     Event Processing
- Thread 4:     Web Server (future)

Usage:
    python3 sec_cam_main.py
    
    or as systemd service:
    sudo systemctl start sec-cam
"""

import sys
import signal
import time
import subprocess  # Add this line
from config import (
    DATABASE_PATH,
    ensure_directories,
    validate_config,
    print_config
)
from database import EventDatabase
from logger import log, stop_logger
from circular_buffer import CircularBuffer
from motion_event import MotionEvent
from motion_detector import MotionDetector
from event_processor import EventProcessor
from mjpeg_server import MJPEGServer

class SecurityCameraSystem:
    """
    Main orchestrator for security camera system.
    
    Manages initialization, startup, and graceful shutdown of all components.
    """
    
    def __init__(self):
        """
        Initialize system components.
        """
        print("\n" + "="*60)
        print("Security Camera System - Starting")
        print("="*60 + "\n")
        
        # Component references
        self.db = None
        self.circular_buffer = None
        self.motion_event = None
        self.motion_detector = None
        self.event_processor = None
        self.mjpeg_server = None

        # System state
        self.running = False
        
        log("System initializing...")
    
    def initialize(self):
        """
        Initialize all system components in proper order.
        
        Order is critical:
        1. Validate configuration
        2. Create directories
        3. Initialize database
        4. Create coordination objects
        5. Initialize components (don't start yet)
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            # Step 1: Validate configuration
            log("Validating configuration...")
            print_config()
            validate_config()
            
            # Step 2: Ensure directories exist
            log("Creating directories...")
            ensure_directories()
            
            # Step 3: Initialize database
            log("Initializing database...")
            self.db = EventDatabase(DATABASE_PATH)

            # Step 3.5: Reset streaming flag on startup (prevent auto-streaming)
            log("Resetting streaming flag...")
            try:
                self.db.set_streaming_flag(0)
                log("Streaming flag reset to 0")
            except Exception as e:
                log(f"Warning: Could not reset streaming flag: {e}", level="WARNING")

            # Step 4: Create motion event coordinator
            log("Creating motion event coordinator...")
            self.motion_event = MotionEvent()
            
            # Step 5: Initialize circular buffer (Thread 1)
            log("Initializing circular buffer...")
            self.circular_buffer = CircularBuffer()
            
            # Step 6: Initialize motion detector (Thread 2)
            log("Initializing motion detector...")
            self.motion_detector = MotionDetector(
                self.circular_buffer,
                self.db,
                self.motion_event
            )
            
            # Step 7: Initialize event processor (Thread 3)
            log("Initializing event processor...")
            self.event_processor = EventProcessor(
                self.circular_buffer,
                self.db,
                self.motion_event
            )

            # Step 8: Initialize MJPEG server (Thread 4) - ADD THIS
            log("Initializing MJPEG server...")
            self.mjpeg_server = MJPEGServer(
                self.circular_buffer,
                self.db
            )

            log("All components initialized successfully")
            return True
            
        except Exception as e:
            log(f"Initialization failed: {e}", level="ERROR")
            print(f"\n✗ Initialization failed: {e}\n")
            return False

    def start_camera_watchdog(self):
        """Enhanced watchdog with power monitoring and buffer health checks."""
        import threading, time
        from logger import log
        
        def watchdog_loop():
            log("[WATCHDOG] Camera watchdog started with power and buffer monitoring.")
            last_restart_time = 0
            timeout_count = 0
            check_count = 0
            
            while True:
                try:
                    check_count += 1
                    
                    # Check thermal throttling
                    try:
                        with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                            temp = int(f.read()) / 1000
                            if temp > 70:
                                log(f"[WATCHDOG] High temperature: {temp}°C", level="WARNING")
                    except:
                        pass
                    
                    cb = self.circular_buffer
                    now = time.time()
                    frame_age = now - getattr(cb, "last_frame_time", 0)
                    thread_alive = cb.capture_thread and cb.capture_thread.is_alive()

                    # Check buffer health every 10 cycles (50 seconds)
                    if check_count % 10 == 0:
                        health = cb.get_buffer_health()
                        if health:
                            current = health['current_chunks']
                            maximum = health['max_chunks']
                            utilization = health['utilization_pct']
                            status = health['status']
                            evictions = health['eviction_count']
                            
                            # Capacity-driven health assessment
                            if status == "critically_low":
                                # Buffer suspiciously empty - encoder might have problems
                                log(f"[WATCHDOG] Buffer critically low: {current}/{maximum} "
                                    f"chunks ({utilization:.1f}% full) - encoder may have stalled!", 
                                    level="ERROR")
                            
                            elif status == "low":
                                # Buffer below ideal but not critical
                                log(f"[WATCHDOG] Buffer low: {current}/{maximum} "
                                    f"chunks ({utilization:.1f}% full) - still filling or recovering", 
                                    level="WARNING")
                            
                            elif status == "filling":
                                # Buffer filling normally
                                log(f"[WATCHDOG] Buffer filling: {current}/{maximum} "
                                    f"chunks ({utilization:.1f}% full)")
                            
                            elif status == "optimal":
                                # This is what we want! Only log periodically (every 5th check = 4+ minutes)
                                if check_count % 200 == 0:
                                    log(f"[WATCHDOG] Buffer optimal: {current}/{maximum} "
                                        f"chunks ({utilization:.1f}% full), {evictions} total evictions")
                            
                            # Warn if excessive evictions (might mean max_chunks too low)
                            # Only check after system has been running a while
                            if check_count > 50 and evictions > (maximum * 50):
                                # More than 50x the buffer size has been evicted
                                # This means we've cycled through the entire buffer 50+ times
                                avg_evictions_per_min = evictions / ((check_count * 5) / 60)
                                log(f"[WATCHDOG] High eviction rate: {evictions} total evictions "
                                    f"({avg_evictions_per_min:.1f}/min). Consider increasing "
                                    f"CIRCULAR_BUFFER_MAX_CHUNKS in config.py", 
                                    level="WARNING")
                    
                    # Check for camera stall
                    if (frame_age > 10) or not thread_alive:
                        timeout_count += 1
                        reason = "no new frames" if frame_age > 10 else "capture thread died"
                        log(f"[WATCHDOG] {reason} (timeout #{timeout_count}) → recovery", "WARNING")
                        
                        # Prevent restart storm
                        if now - last_restart_time < 60:
                            log("[WATCHDOG] Restart suppressed (< 60s since last)")
                            time.sleep(5)
                            continue
                        
                        last_restart_time = now
                        self._perform_full_recovery()
                        
                        # If timeouts are frequent, something is seriously wrong
                        if timeout_count > 10:
                            log("[WATCHDOG] Too many timeouts (10+) - possible hardware issue", level="ERROR")
                            timeout_count = 0  # Reset but keep monitoring
                    else:
                        # Reset timeout counter on successful frame
                        if timeout_count > 0 and frame_age < 2:
                            log(f"[WATCHDOG] Camera recovered after {timeout_count} timeouts")
                            timeout_count = 0
                    
                    time.sleep(5)
                    
                except Exception as e:
                    log(f"[WATCHDOG] Error: {e}", level="ERROR")
                    time.sleep(5)
        
        threading.Thread(target=watchdog_loop, name="CameraWatchdog", daemon=True).start()

    def _perform_full_recovery(self):
        """
        Enhanced camera recovery with aggressive cleanup.
        """
        from logger import log
        import time, gc, subprocess
        
        try:
            log("[WATCHDOG] === CAMERA RECOVERY INITIATED ===")
            
            # Pause dependent threads
            if hasattr(self.motion_detector, "pause"):
                self.motion_detector.pause()
            if hasattr(self.event_processor, "pause"):
                self.event_processor.pause()
            
            # Stop and cleanup buffer
            log("[WATCHDOG] Stopping circular buffer...")
            self.circular_buffer.stop()
            time.sleep(2.0)
            
            # Aggressive cleanup
            log("[WATCHDOG] Forcing aggressive memory cleanup...")
            self.circular_buffer = None
            gc.collect()
            time.sleep(2.0)
            
            # Force kernel to drop caches (helps with CMA)
            try:
                subprocess.run(['sudo', 'sh', '-c', 'echo 1 > /proc/sys/vm/drop_caches'], 
                            timeout=5, check=False)
            except:
                pass
            
            time.sleep(1.0)
            
            # Recreate buffer
            log("[WATCHDOG] Recreating circular buffer...")
            from circular_buffer import CircularBuffer
            self.circular_buffer = CircularBuffer()
            
            # Restart buffer (picamera2 re-init happens here)
            log("[WATCHDOG] Restarting circular buffer...")
            self.circular_buffer.start()
            
            # Link motion detector to new buffer (for streaming control)
            log("[WATCHDOG] Linking motion detector to new buffer...")
            self.circular_buffer.set_motion_detector(self.motion_detector)
            
            # Update MJPEG server's buffer reference - CRITICAL FIX
            if self.mjpeg_server:
                log("[WATCHDOG] Updating MJPEG server buffer reference...")
                self.mjpeg_server.buffer = self.circular_buffer
            
            # Reattach to motion detector
            if hasattr(self.motion_detector, "attach_buffer"):
                self.motion_detector.attach_buffer(self.circular_buffer)
            
            # Reattach to event processor
            if hasattr(self.event_processor, "buffer"):
                self.event_processor.buffer = self.circular_buffer
            
            # Resume threads
            if hasattr(self.motion_detector, "resume"):
                self.motion_detector.resume()
            if hasattr(self.event_processor, "resume"):
                self.event_processor.resume()
            
            log("[WATCHDOG] === CAMERA RECOVERY COMPLETE ===")
            
        except Exception as e:
            log(f"[WATCHDOG] Recovery failed: {e}", level="ERROR")
            log("[WATCHDOG] System requires restart - attempting reboot...", level="ERROR")
            try:
                subprocess.Popen(["sudo", "reboot"])
            except:
                log("[WATCHDOG] Reboot failed - manual intervention required", level="ERROR")
            
    def start(self):
        """
        Start all system components in proper order.
        
        Startup sequence:
        1. Start circular buffer (camera)
        2. Link motion detector to buffer (for streaming control)
        3. Start event processor (waits for motion)
        4. Start motion detector (begins detecting)
        5. Start camera watchdog
        6. Start MJPEG server (monitors streaming flag)
        
        Returns:
            bool: True if startup successful, False otherwise
        """
        try:
            log("Starting system components...")
            
            # Step 1: Start circular buffer (camera and recording)
            log("Starting circular buffer...")
            self.circular_buffer.start()
            
            # Step 2: Link motion detector to circular buffer (for streaming control)
            log("Linking motion detector to circular buffer...")
            self.circular_buffer.set_motion_detector(self.motion_detector)
            
            # Step 3: Start event processor (Thread 3)
            # Must start before motion detector so it's ready to receive events
            log("Starting event processor...")
            self.event_processor.start()
            
            # Step 4: Start motion detector (Thread 2)
            log("Starting motion detector...")
            self.motion_detector.start()
            
            # Step 5: Start watchdog thread to monitor camera health and restart if needed
            self.start_camera_watchdog()
            
            # Step 6: Start MJPEG server (Thread 4) - ADD THIS
            log("Starting MJPEG server...")
            self.mjpeg_server.start()
            
            # System is now running
            self.running = True
            
            log("System started successfully")
            print("\n" + "="*60)
            print("✓ Security Camera System Running")
            print("="*60)
            print("Press Ctrl+C to stop")
            print("="*60 + "\n")
            
            return True
            
        except Exception as e:
            log(f"Startup failed: {e}", level="ERROR")
            print(f"\n✗ Startup failed: {e}\n")
            return False
    
    def stop(self):
        """
        Stop all system components gracefully.
        
        Shutdown sequence (reverse of startup):
        1. Stop motion detector
        2. Stop event processor
        3. Stop MJPEG server
        4. Stop circular buffer
        5. Flush logs
        """
        if not self.running:
            return
        
        log("System shutdown initiated...")
        print("\n" + "="*60)
        print("Security Camera System - Shutting Down")
        print("="*60)
        
        self.running = False
        
        try:
            # Step 1: Stop motion detector (Thread 2)
            if self.motion_detector:
                log("Stopping motion detector...")
                self.motion_detector.stop()
            
            # Step 2: Stop event processor (Thread 3)
            if self.event_processor:
                log("Stopping event processor...")
                self.event_processor.stop()
            
            # Step 3: Stop MJPEG server (Thread 4) - ADD THIS
            if self.mjpeg_server:
                log("Stopping MJPEG server...")
                self.mjpeg_server.stop()
            
            # Step 4: Stop circular buffer (camera)
            if self.circular_buffer:
                log("Stopping circular buffer...")
                self.circular_buffer.stop()
            
            # Step 5: Flush logs
            log("System shutdown complete")
            stop_logger()
            
            print("✓ System stopped successfully\n")
            
        except Exception as e:
            print(f"Error during shutdown: {e}\n")
            log(f"Error during shutdown: {e}", level="ERROR")
    
    def run(self):
        """
        Main run loop - keeps system alive until interrupted.
        
        Returns:
            int: Exit code (0 for success, 1 for failure)
        """
        import psutil
        import os
        import gc
        
        # Initialize
        if not self.initialize():
            return 1
        
        # Start
        if not self.start():
            self.stop()
            return 1
        
        # Run until interrupted
        try:
            proc = psutil.Process(os.getpid())
            loop_counter = 0
            last_leak_check = time.time()
            mem_samples = []
            
            while self.running:
                time.sleep(1.0)
                loop_counter += 1
                
                # Regular memory logging every 50 seconds
                if loop_counter % 200 == 0:
                    rss_mb = proc.memory_info().rss / (1024 * 1024)
                    log(f"[MEMDEBUG] RSS={rss_mb:.1f} MB")
                
                # Leak detection every 30 seconds
                if time.time() - last_leak_check >= 30:
                    rss_mb = proc.memory_info().rss / (1024 * 1024)
                    mem_samples.append(rss_mb)
                    
                    # Keep last 10 samples (5 minutes of history)
                    if len(mem_samples) > 10:
                        mem_samples.pop(0)
                    
                    # Detect leak (memory growing consistently)
                    if len(mem_samples) >= 3:
                        trend = mem_samples[-1] - mem_samples[0]
                        
                        # Check if streaming is active (growth expected during streaming)
                        streaming_active = False
                        try:
                            streaming_active = self.db.get_streaming_flag() == 1
                        except:
                            pass
                        
                        # Only flag leak if NOT streaming and memory is growing
                        if trend > 20 and not streaming_active:  # Growing by 20+ MB
                            log(f"MEMORY LEAK DETECTED: {trend:.1f} MB growth over {len(mem_samples)*30}s", level="ERROR")
                            log(f"Current RSS: {rss_mb:.1f} MB", level="ERROR")
                            
                            # Force aggressive GC
                            gc.collect()
                            
                            new_rss = proc.memory_info().rss / (1024 * 1024)
                            freed = rss_mb - new_rss
                            if freed > 1:
                                log(f"Emergency GC freed {freed:.1f} MB", level="WARNING")
                    
                    last_leak_check = time.time()
        
        except KeyboardInterrupt:
            print("\n\nReceived keyboard interrupt (Ctrl+C)")
        
        # Shutdown
        self.stop()
        
        return 0


# ============================================================================
# SIGNAL HANDLERS
# ============================================================================

# Global reference for signal handlers
_system = None

def signal_handler(signum, frame):
    """
    Handle shutdown signals (SIGTERM, SIGINT).
    
    This allows graceful shutdown when:
    - User presses Ctrl+C (SIGINT)
    - systemctl stop is called (SIGTERM)
    """
    global _system
    
    signal_name = "SIGTERM" if signum == signal.SIGTERM else "SIGINT"
    print(f"\n\nReceived {signal_name} signal")
    log(f"Received {signal_name} signal")
    
    if _system:
        _system.stop()


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    """
    Main entry point for security camera system.
    """
    global _system
    
    # Create system instance
    _system = SecurityCameraSystem()
    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Run system
    exit_code = _system.run()
    
    # Exit with appropriate code
    sys.exit(exit_code)


if __name__ == "__main__":
    main()