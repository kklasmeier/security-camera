"""
Security Camera System - MJPEG Streaming Server
================================================
Thread 4: Monitors database streaming flag and serves MJPEG stream.

When streaming=1:
- Starts HTTP server on port 8080
- Grabs frames from circular buffer at 10fps
- Serves MJPEG stream to browsers
- Pauses motion detection (via buffer.start_streaming())

When streaming=0:
- Stops HTTP server
- Resumes normal operation (via buffer.stop_streaming())
"""

import time
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from io import BytesIO
from PIL import Image
from logger import log
from config import LIVESTREAM_PORT, LIVESTREAM_JPEG_QUALITY, LIVESTREAM_FRAMERATE


class MJPEGHandler(BaseHTTPRequestHandler):
    """
    HTTP request handler for MJPEG stream.
    
    Serves a single endpoint: /stream.mjpg
    """
    
    def do_GET(self):
        """Handle HTTP GET requests."""
        # Strip query string for path matching (e.g., /stream.mjpg?t=123456)
        path = self.path.split('?')[0]
        
        if path == '/stream.mjpg':
            self.serve_mjpeg_stream()
        else:
            self.send_error(404, "Stream not found. Try /stream.mjpg")
    
    def serve_mjpeg_stream(self):
        """
        Serve MJPEG stream to client.
        
        MJPEG format:
        - HTTP response with multipart/x-mixed-replace content type
        - Each frame is a JPEG image with boundary marker
        - Browsers display as continuous video
        """
        # Notify server of new client
        self.server.mjpeg_server.client_connected()
        
        try:
            # Send HTTP headers
            self.send_response(200)
            self.send_header('Age', '0')
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
            self.end_headers()
            
            log(f"Client connected to MJPEG stream: {self.client_address[0]}")
            
            # Stream frames until client disconnects
            frame_delay = 1.0 / LIVESTREAM_FRAMERATE
            frame_count = 0
            
            while True:
                # Get latest frame from circular buffer
                frame = self.server.circular_buffer.get_latest_frame_for_livestream()
                
                if frame is None:
                    log(f"[STREAM DEBUG] Frame is None, waiting...", level="WARNING")
                    time.sleep(0.1)
                    continue
                
                # Convert frame to JPEG
                try:
                    img = Image.fromarray(frame)
                    buffer = BytesIO()
                    img.save(buffer, format='JPEG', quality=LIVESTREAM_JPEG_QUALITY)
                    jpeg_bytes = buffer.getvalue()
                    buffer.close()
                except Exception as e:
                    log(f"[STREAM DEBUG] Error encoding JPEG: {e}", level="ERROR")
                    time.sleep(0.1)
                    continue
                
                try:
                    # Send frame in browser-compatible format
                    self.wfile.write(b'--FRAME\r\n')
                    self.wfile.write(b'Content-Type: image/jpeg\r\n')
                    self.wfile.write(b'Content-Length: ' + str(len(jpeg_bytes)).encode() + b'\r\n')
                    self.wfile.write(b'\r\n')
                    self.wfile.write(jpeg_bytes)
                    self.wfile.write(b'\r\n')
                    
                    frame_count += 1
                    
                    # Log every 100 frames
                    if frame_count % 100 == 0:
                        log(f"[STREAM DEBUG] Sent {frame_count} frames to {self.client_address[0]}")
                    
                except (BrokenPipeError, ConnectionResetError, OSError) as e:
                    log(f"[STREAM DEBUG] Connection error after {frame_count} frames: {type(e).__name__}")
                    break
                except Exception as e:
                    log(f"[STREAM DEBUG] Unexpected error sending frame {frame_count}: {e}", level="ERROR")
                    break
                
                # Rate limiting
                time.sleep(frame_delay)
                
        except (BrokenPipeError, ConnectionResetError, OSError):
            log(f"Client disconnected from MJPEG stream: {self.client_address[0]}")
        except Exception as e:
            log(f"Error serving MJPEG stream: {e}", level="ERROR")
            import traceback
            log(f"Traceback: {traceback.format_exc()}", level="ERROR")
        finally:
            # CRITICAL: Always notify server when client disconnects
            self.server.mjpeg_server.client_disconnected()
    
    def log_message(self, format, *args):
        """Suppress default HTTP logging (too verbose)."""
        pass


class MJPEGServer:
    """
    MJPEG streaming server with database flag monitoring.
    
    Monitors system_control.streaming flag every 1 second.
    Starts/stops HTTP server based on flag state.
    Automatically stops streaming when all clients disconnect.
    """
    
    def __init__(self, circular_buffer, database):
        """
        Initialize MJPEG server.
        
        Args:
            circular_buffer: CircularBuffer instance for frame access
            database: EventDatabase instance for flag monitoring
        """
        self.buffer = circular_buffer
        self.db = database
        self.running = False
        self.server = None
        self.server_thread = None
        self.monitor_thread = None
        self.active_clients = 0  # Track number of connected clients
        self.client_lock = threading.Lock()  # Thread-safe client counting
        
        log("MJPEGServer initialized")
    
    def client_connected(self):
        """Called when a client connects to the stream."""
        with self.client_lock:
            self.active_clients += 1
            log(f"Client connected (total clients: {self.active_clients})")
    
    def client_disconnected(self):
        """Called when a client disconnects from the stream."""
        with self.client_lock:
            self.active_clients -= 1
            log(f"Client disconnected (total clients: {self.active_clients})")
            
            # If no clients left, stop streaming after a short delay
            if self.active_clients == 0:
                log("No clients connected - stopping streaming in 5 seconds...")
                # Use a timer to avoid immediate shutdown (allows reconnects)
                threading.Timer(5.0, self._check_and_stop_streaming).start()
    
    def _check_and_stop_streaming(self):
        """Check if still no clients and stop streaming if so."""
        with self.client_lock:
            if self.active_clients == 0:
                log("No clients for 5 seconds - auto-stopping streaming")
                try:
                    self.db.set_streaming_flag(0)
                except Exception as e:
                    log(f"Error setting streaming flag to 0: {e}", level="ERROR")
            else:
                log(f"Client reconnected - keeping streaming active ({self.active_clients} clients)")
    
    def start(self):
        """Start monitoring thread."""
        self.running = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_streaming_flag,
            name="MJPEGMonitor",
            daemon=True
        )
        self.monitor_thread.start()
        log("MJPEG server monitor started")
    
    def stop(self):
        """Stop monitoring and server."""
        log("Stopping MJPEG server...")
        self.running = False
        
        # Stop HTTP server if running
        if self.server:
            self._stop_http_server()
        
        # Wait for monitor thread
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2.0)
        
        log("MJPEG server stopped")
    
    def _monitor_streaming_flag(self):
        """
        Monitor database streaming flag and start/stop server accordingly.
        
        Polls database every 1 second for flag changes.
        Includes 15-minute timeout for safety.
        """
        server_active = False
        streaming_start_time = None
        STREAMING_TIMEOUT = 15 * 60  # 15 minutes in seconds
        
        log("MJPEG monitor: Polling database flag every 1 second")
        
        while self.running:
            try:
                # Check database flag
                streaming = self.db.get_streaming_flag()
                
                if streaming == 1 and not server_active:
                    # Start streaming
                    log("MJPEG monitor: Streaming flag = 1, starting server")
                    self.buffer.start_streaming()
                    self._start_http_server()
                    server_active = True
                    streaming_start_time = time.time()  # Track when streaming started
                    log(f"Streaming started - will auto-stop after {STREAMING_TIMEOUT/60:.0f} minutes")
                
                elif streaming == 0 and server_active:
                    # Stop streaming (flag manually set to 0)
                    log("MJPEG monitor: Streaming flag = 0, stopping server")
                    try:
                        self._stop_http_server()
                    finally:
                        # Always call stop_streaming, even if HTTP shutdown fails
                        self.buffer.stop_streaming()
                        server_active = False
                        streaming_start_time = None
                
                elif streaming == 1 and server_active:
                    # Check timeout while streaming is active
                    if streaming_start_time:
                        elapsed = time.time() - streaming_start_time
                        if elapsed >= STREAMING_TIMEOUT:
                            log(f"MJPEG monitor: Streaming timeout reached ({STREAMING_TIMEOUT/60:.0f} minutes), stopping server", level="WARNING")
                            # Set flag to 0 in database
                            try:
                                self.db.set_streaming_flag(0)
                            except Exception as e:
                                log(f"Error setting streaming flag to 0: {e}", level="ERROR")
                            
                            # Stop streaming
                            try:
                                self._stop_http_server()
                            finally:
                                self.buffer.stop_streaming()
                                server_active = False
                                streaming_start_time = None
                
                # Poll interval
                time.sleep(1.0)
                
            except Exception as e:
                log(f"MJPEG monitor error: {e}", level="ERROR")
                time.sleep(1.0)
    
    def _start_http_server(self):
        """Start HTTP server on LIVESTREAM_PORT."""
        try:
            # Create server
            self.server = HTTPServer(('0.0.0.0', LIVESTREAM_PORT), MJPEGHandler)
            self.server.circular_buffer = self.buffer
            self.server.mjpeg_server = self  # Pass reference to self
            
            # Start server in background thread
            self.server_thread = threading.Thread(
                target=self.server.serve_forever,
                name="MJPEGServerHTTP",
                daemon=True
            )
            self.server_thread.start()
            
            log(f"MJPEG HTTP server started on port {LIVESTREAM_PORT}")
            
        except Exception as e:
            log(f"Failed to start MJPEG HTTP server: {e}", level="ERROR")
            self.server = None
    
    def _stop_http_server(self):
        """Stop HTTP server."""
        if self.server:
            try:
                # Shutdown in separate thread to avoid blocking
                def shutdown_server():
                    try:
                        self.server.shutdown()
                        self.server.server_close()
                    except Exception as e:
                        log(f"Error in server shutdown: {e}", level="ERROR")
                
                shutdown_thread = threading.Thread(target=shutdown_server, daemon=True)
                shutdown_thread.start()
                shutdown_thread.join(timeout=3.0)  # Wait max 3 seconds
                
                log("MJPEG HTTP server stopped")
            except Exception as e:
                log(f"Error stopping MJPEG HTTP server: {e}", level="ERROR")
            finally:
                self.server = None
                self.server_thread = None


# ============================================================================
# STANDALONE TESTING
# ============================================================================

if __name__ == "__main__":
    """
    Test MJPEG server with mock objects.
    """
    print("MJPEG Server - Standalone Test")
    print("="*60)
    print("Note: This test requires CircularBuffer and Database instances.")
    print("Run full system test via sec_cam_main.py instead.")
    print("="*60)
    
    print("\n✓ MJPEGServer class defined successfully")
    print("\nServer will:")
    print("  - Poll database streaming flag every 1 second")
    print("  - Start HTTP server on port", LIVESTREAM_PORT, "when flag=1")
    print("  - Serve MJPEG stream at /stream.mjpg")
    print("  - Stop server when flag=0")
    print("\nReady for integration testing!")