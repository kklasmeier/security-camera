"""
Security Camera System - Database Module
=========================================
Centralized database operations for all threads.
Uses SQLite with WAL mode for better concurrent access.
Each method creates short-lived connections for thread safety.
"""

import sqlite3
import os
from datetime import datetime
from config import DATABASE_PATH


# ============================================================================
# DATETIME HANDLING (Python 3.12+ compatibility)
# ============================================================================

def adapt_datetime(dt):
    """
    Convert datetime to ISO format string for SQLite.
    Required for Python 3.12+ compatibility.
    
    Args:
        dt (datetime): Datetime object to convert
        
    Returns:
        str: ISO format string
    """
    return dt.isoformat() if dt else None


class EventDatabase:
    """
    Centralized database interface for all system components.
    
    Thread-safe through short-lived connections and SQLite's WAL mode.
    All threads use this class to interact with the database.
    
    Usage:
        db = EventDatabase()
        event_id = db.add_new_event(timestamp, score, image_path)
        db.save_video(event_id, video_path)
    """
    
    def __init__(self, db_path=None):
        """
        Initialize database connection and create schema if needed.
        
        Args:
            db_path (str, optional): Path to database file. 
                                    Defaults to DATABASE_PATH from config.
        """
        self.db_path = db_path or DATABASE_PATH
        
        # Ensure database directory exists
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
        
        # Initialize schema on first run
        self._init_schema()
        
        print(f"EventDatabase initialized: {self.db_path}")
    
    def get_connection(self):
        """
        Create a new database connection with WAL mode enabled.
        
        WAL (Write-Ahead Logging) mode benefits:
        - Readers don't block writers
        - Writers don't block readers  
        - Better concurrency for multi-threaded access
        
        Returns:
            sqlite3.Connection: Database connection
        """
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.execute("PRAGMA journal_mode=WAL")
        
        # Return rows as dictionaries for easier access
        conn.row_factory = sqlite3.Row
        
        return conn
    
    def _init_schema(self):
        """
        Create database tables if they don't exist.
        Safe to call multiple times (uses IF NOT EXISTS).
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Events table - main event storage
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    motion_score INTEGER,
                    
                    -- File paths (populated progressively)
                    image_a_path TEXT,
                    image_b_path TEXT,
                    thumbnail_path TEXT,
                    video_path TEXT,
                    duration_seconds INTEGER DEFAULT 30,
                    
                    -- AI fields (for future Project 2)
                    ai_processed BOOLEAN DEFAULT 0,
                    ai_processed_at DATETIME,
                    ai_objects TEXT,
                    ai_tags TEXT,
                    ai_description TEXT,
                    ai_confidence FLOAT,
                    ai_severity INTEGER,
                    
                    -- Metadata
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME
                )
            """)
            
            # Indexes for performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON events(timestamp)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_ai_processed 
                ON events(ai_processed)
            """)
            
            # System control table - single row for system state
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_control (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    streaming BOOLEAN DEFAULT 0,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Insert default system_control row if it doesn't exist
            cursor.execute("""
                INSERT OR IGNORE INTO system_control (id, streaming) 
                VALUES (1, 0)
            """)
            
            # Logs table - for batched logging
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    level TEXT,
                    message TEXT
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_log_timestamp 
                ON logs(timestamp)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_log_level 
                ON logs(level)
            """)
            
            conn.commit()
            print("Database schema initialized successfully")
            
        except sqlite3.Error as e:
            print(f"Error initializing database schema: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()
    
    # ========================================================================
    # EVENT OPERATIONS (Thread 2 and Thread 3)
    # ========================================================================
    
    def add_new_event(self, timestamp, motion_score, image_a_path):
        """
        Create new event record when motion detected (Thread 2, T+0s).
        
        This is called immediately by Thread 2 when motion is detected.
        Returns event_id for tracking subsequent updates.
        
        Args:
            timestamp (datetime): When motion occurred
            motion_score (int): Number of changed pixels
            image_a_path (str): Path to first captured image
            
        Returns:
            int: Event ID for tracking this event
            
        Example:
            event_id = db.add_new_event(
                datetime.now(), 
                125, 
                "/home/pi/sec_cam/pictures/2025.10.12--14.23.45_a.jpg"
            )
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            now = adapt_datetime(datetime.now())
            cursor.execute("""
                INSERT INTO events 
                (timestamp, motion_score, image_a_path, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """, (adapt_datetime(timestamp), motion_score, image_a_path, now, now))
            
            event_id = cursor.lastrowid
            conn.commit()
            
            print(f"Event {event_id} created: motion_score={motion_score}")
            return event_id
            
        except sqlite3.Error as e:
            print(f"Error creating event: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def save_picture_b(self, event_id, image_b_path):
        """
        Update event with second image path (Thread 3, T+4s).
        
        Args:
            event_id (int): Event ID from add_new_event()
            image_b_path (str): Path to second image
            
        Example:
            db.save_picture_b(42, "/home/pi/sec_cam/pictures/2025.10.12--14.23.45_b.jpg")
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE events 
                SET image_b_path = ?, updated_at = ?
                WHERE id = ?
            """, (image_b_path, adapt_datetime(datetime.now()), event_id))
            
            conn.commit()
            print(f"Event {event_id}: Picture B saved")
            
        except sqlite3.Error as e:
            print(f"Error saving Picture B for event {event_id}: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def save_thumbnail(self, event_id, thumbnail_path):
        """
        Update event with thumbnail path (Thread 3, T+4s).
        
        Args:
            event_id (int): Event ID
            thumbnail_path (str): Path to thumbnail image
            
        Example:
            db.save_thumbnail(42, "/home/pi/sec_cam/thumbs/2025.10.12--14.23.45_b.jpg")
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE events 
                SET thumbnail_path = ?, updated_at = ?
                WHERE id = ?
            """, (thumbnail_path, adapt_datetime(datetime.now()), event_id))
            
            conn.commit()
            print(f"Event {event_id}: Thumbnail saved")
            
        except sqlite3.Error as e:
            print(f"Error saving thumbnail for event {event_id}: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def save_video(self, event_id, video_path, duration_seconds=None):
        """
        Update event with video path and optional duration (Thread 3, T+17s).
        
        Args:
            event_id (int): Event ID
            video_path (str): Path to video file
            duration_seconds (float, optional): Video duration in seconds (estimated or exact)
            
        Example:
            db.save_video(42, "/home/pi/sec_cam/videos/2025.10.12--14.23.45.mp4", 33.5)
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # If duration provided, update it; otherwise just update video_path
            if duration_seconds is not None:
                # Round to nearest integer for cleaner display
                duration_int = round(duration_seconds)
                cursor.execute("""
                    UPDATE events 
                    SET video_path = ?, duration_seconds = ?, updated_at = ?
                    WHERE id = ?
                """, (video_path, duration_int, adapt_datetime(datetime.now()), event_id))
                print(f"Event {event_id}: Video saved - duration set to {duration_int}s")
            else:
                cursor.execute("""
                    UPDATE events 
                    SET video_path = ?, updated_at = ?
                    WHERE id = ?
                """, (video_path, adapt_datetime(datetime.now()), event_id))
            
            conn.commit()
            print(f"Event {event_id}: Video saved - processing complete")
            
        except sqlite3.Error as e:
            print(f"Error saving video for event {event_id}: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    # ========================================================================
    # STREAMING CONTROL (Thread 4 and PHP)
    # ========================================================================
    
    def get_streaming_flag(self):
        """
        Check if livestream is requested (Thread 4).
        
        Returns:
            int: 0 = normal operation, 1 = livestream active
            
        Example:
            if db.get_streaming_flag() == 1:
                start_livestream()
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT streaming FROM system_control WHERE id = 1")
            row = cursor.fetchone()
            
            if row:
                return row['streaming']
            else:
                # Should never happen, but return safe default
                return 0
                
        except sqlite3.Error as e:
            print(f"Error reading streaming flag: {e}")
            return 0
        finally:
            conn.close()
    
    def set_streaming_flag(self, streaming):
        """
        Set livestream state (Thread 4 or PHP).
        
        Args:
            streaming (int): 0 = stop streaming, 1 = start streaming
            
        Example:
            db.set_streaming_flag(1)  # Start streaming
            db.set_streaming_flag(0)  # Stop streaming
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE system_control 
                SET streaming = ?, updated_at = ?
                WHERE id = 1
            """, (streaming, adapt_datetime(datetime.now())))
            
            conn.commit()
            status = "active" if streaming else "inactive"
            print(f"Streaming flag set to: {status}")
            
        except sqlite3.Error as e:
            print(f"Error setting streaming flag: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    # ========================================================================
    # LOGGING OPERATIONS (Logger module)
    # ========================================================================
    
    def add_log_batch(self, log_entries):
        """
        Insert multiple log entries in a single transaction.
        Used by logger module for batched writes.
        
        Args:
            log_entries (list): List of tuples (timestamp, level, message)
            
        Example:
            logs = [
                (datetime.now(), "INFO", "System started"),
                (datetime.now(), "ERROR", "Connection failed")
            ]
            db.add_log_batch(logs)
        """
        if not log_entries:
            return
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Convert datetime objects in log entries
            adapted_entries = [
                (adapt_datetime(timestamp), level, message)
                for timestamp, level, message in log_entries
            ]
            
            cursor.executemany("""
                INSERT INTO logs (timestamp, level, message)
                VALUES (?, ?, ?)
            """, adapted_entries)
            
            conn.commit()
            print(f"Wrote {len(log_entries)} log entries to database")
            
        except sqlite3.Error as e:
            print(f"Error writing log batch: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    # ========================================================================
    # QUERY OPERATIONS (For testing and maintenance)
    # ========================================================================
    
    def get_recent_events(self, limit=25):
        """
        Get most recent events for testing/debugging.
        
        Args:
            limit (int): Maximum number of events to return
            
        Returns:
            list: List of event dictionaries
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT * FROM events 
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (limit,))
            
            events = [dict(row) for row in cursor.fetchall()]
            return events
            
        except sqlite3.Error as e:
            print(f"Error querying recent events: {e}")
            return []
        finally:
            conn.close()
    
    def get_event_count(self):
        """
        Get total number of events in database.
        
        Returns:
            int: Total event count
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT COUNT(*) as count FROM events")
            row = cursor.fetchone()
            return row['count'] if row else 0
            
        except sqlite3.Error as e:
            print(f"Error counting events: {e}")
            return 0
        finally:
            conn.close()
    
    def get_log_count(self):
        """
        Get total number of log entries in database.
        
        Returns:
            int: Total log count
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT COUNT(*) as count FROM logs")
            row = cursor.fetchone()
            return row['count'] if row else 0
            
        except sqlite3.Error as e:
            print(f"Error counting logs: {e}")
            return 0
        finally:
            conn.close()


# ============================================================================
# STANDALONE TESTING
# ============================================================================

if __name__ == "__main__":
    """
    Test database functionality when run directly.
    """
    print("Testing EventDatabase class...\n")
    
    # Use test database to avoid affecting production
    test_db_path = "/tmp/test_events.db"
    
    # Clean up any existing test database
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
    
    # Initialize database
    db = EventDatabase(test_db_path)
    
    # Test 1: Create event
    print("\n--- Test 1: Creating event ---")
    test_timestamp = datetime.now()
    event_id = db.add_new_event(
        timestamp=test_timestamp,
        motion_score=125,
        image_a_path="/test/path/image_a.jpg"
    )
    print(f"Created event ID: {event_id}")
    
    # Test 2: Update with Picture B
    print("\n--- Test 2: Updating Picture B ---")
    db.save_picture_b(event_id, "/test/path/image_b.jpg")
    
    # Test 3: Update with thumbnail
    print("\n--- Test 3: Updating thumbnail ---")
    db.save_thumbnail(event_id, "/test/path/thumb_b.jpg")
    
    # Test 4: Update with video
    print("\n--- Test 4: Updating video ---")
    db.save_video(event_id, "/test/path/video.h264")
    
    # Test 5: Streaming flags
    print("\n--- Test 5: Streaming control ---")
    print(f"Initial streaming flag: {db.get_streaming_flag()}")
    db.set_streaming_flag(1)
    print(f"After setting to 1: {db.get_streaming_flag()}")
    db.set_streaming_flag(0)
    print(f"After setting to 0: {db.get_streaming_flag()}")
    
    # Test 6: Logging
    print("\n--- Test 6: Batch logging ---")
    test_logs = [
        (datetime.now(), "INFO", "Test log message 1"),
        (datetime.now(), "WARNING", "Test log message 2"),
        (datetime.now(), "ERROR", "Test log message 3")
    ]
    db.add_log_batch(test_logs)
    
    # Test 7: Query events
    print("\n--- Test 7: Querying events ---")
    events = db.get_recent_events(limit=5)
    print(f"Found {len(events)} events")
    if events:
        print(f"Most recent event: ID={events[0]['id']}, "
              f"timestamp={events[0]['timestamp']}, "
              f"motion_score={events[0]['motion_score']}")
    
    # Test 8: Counts
    print("\n--- Test 8: Counts ---")
    print(f"Total events: {db.get_event_count()}")
    print(f"Total logs: {db.get_log_count()}")
    
    print("\n✓ All tests completed successfully!")
    print(f"Test database: {test_db_path}")