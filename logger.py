"""
Security Camera System - Logging Module
========================================
Batched logging system that writes to SQLite database.
Non-blocking with background writer thread.
Flushes logs every 5 seconds to reduce SD card writes.
"""

import threading
import time
from datetime import datetime
from queue import Queue
from database import EventDatabase
from config import DATABASE_PATH, LOG_BATCH_INTERVAL


class DatabaseLogger:
    """
    Thread-safe batched logger that writes to SQLite database.
    
    Logs are queued in memory and written to database in batches
    every LOG_BATCH_INTERVAL seconds (default: 5 seconds).
    
    This reduces SD card writes from hundreds per minute to ~12 per minute.
    
    Usage:
        logger = DatabaseLogger()
        logger.log("System started")
        logger.log("Motion detected", level="INFO")
        logger.log("Camera error", level="ERROR")
        
        # When shutting down:
        logger.stop()
    """
    
    def __init__(self, db_path=None):
        """
        Initialize logger and start background writer thread.
        
        Args:
            db_path (str, optional): Path to database file.
                                    Defaults to DATABASE_PATH from config.
        """
        self.db = EventDatabase(db_path or DATABASE_PATH)
        self.log_queue = Queue()
        self.running = True
        
        # Start background writer thread
        self.writer_thread = threading.Thread(
            target=self._batch_writer,
            name="LogWriter",
            daemon=True
        )
        self.writer_thread.start()
        
        print("DatabaseLogger initialized - batching every "
              f"{LOG_BATCH_INTERVAL} seconds")
    
    def log(self, message, level="INFO"):
        """
        Queue a log message for writing to database.
        
        Non-blocking - returns immediately.
        Message is printed to console immediately for real-time monitoring.
        Actual database write happens in background every LOG_BATCH_INTERVAL seconds.
        
        Args:
            message (str): Log message
            level (str): Log level - "INFO", "WARNING", or "ERROR"
            
        Example:
            logger.log("Motion detected at front door")
            logger.log("Failed to save video", level="ERROR")
        """
        timestamp = datetime.now()
        
        # Validate level
        if level not in ["INFO", "WARNING", "ERROR"]:
            level = "INFO"
        
        # Queue for batch writing
        self.log_queue.put((timestamp, level, message))
        
        # Also print to console immediately for real-time monitoring
        timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp_str}] [{level}] {message}")
    
    def _batch_writer(self):
        """
        Background thread that writes queued logs to database.
        
        Runs in a loop, flushing logs every LOG_BATCH_INTERVAL seconds.
        This is a daemon thread and will automatically stop when main program exits.
        """
        while self.running:
            # Wait for batch interval
            time.sleep(LOG_BATCH_INTERVAL)
            
            # Flush any queued logs
            self._flush_logs()
    
    def _flush_logs(self):
        """
        Write all queued logs to database in a single transaction.
        
        This is called automatically by the background writer thread,
        but can also be called manually to force immediate write.
        """
        if self.log_queue.empty():
            return
        
        # Collect all queued logs
        log_batch = []
        while not self.log_queue.empty():
            try:
                log_entry = self.log_queue.get_nowait()
                log_batch.append(log_entry)
            except:
                break
        
        # Write batch to database
        if log_batch:
            try:
                self.db.add_log_batch(log_batch)
            except Exception as e:
                print(f"Error writing log batch to database: {e}")
    
    def stop(self):
        """
        Stop the logger and flush any remaining logs.
        
        Should be called during graceful shutdown to ensure
        all queued logs are written to database.
        """
        print("DatabaseLogger stopping - flushing remaining logs...")
        self.running = False
        
        # Flush any remaining logs
        self._flush_logs()
        
        # Wait for writer thread to finish (with timeout)
        self.writer_thread.join(timeout=2.0)
        
        print("DatabaseLogger stopped")


# ============================================================================
# GLOBAL LOGGER INSTANCE
# ============================================================================

# Create a single global logger instance that all modules can use
_global_logger = None


def get_logger(db_path=None):
    """
    Get or create the global logger instance.
    
    This ensures all modules use the same logger instance,
    which is more efficient than creating multiple loggers.
    
    Args:
        db_path (str, optional): Path to database file.
                                Only used on first call.
    
    Returns:
        DatabaseLogger: Global logger instance
        
    Example:
        from logger import get_logger
        log = get_logger()
        log("System started")
    """
    global _global_logger
    
    if _global_logger is None:
        _global_logger = DatabaseLogger(db_path)
    
    return _global_logger


def log(message, level="INFO"):
    """
    Convenience function to log using the global logger.
    
    This is the recommended way to log from other modules.
    
    Args:
        message (str): Log message
        level (str): Log level - "INFO", "WARNING", or "ERROR"
        
    Example:
        from logger import log
        
        log("Motion detected")
        log("Camera error", level="ERROR")
    """
    logger = get_logger()
    logger.log(message, level)


def stop_logger():
    """
    Stop the global logger and flush remaining logs.
    
    Should be called during system shutdown.
    
    Example:
        from logger import stop_logger
        stop_logger()
    """
    global _global_logger
    
    if _global_logger is not None:
        _global_logger.stop()
        _global_logger = None

def log_memory_usage():
    """
    Log current memory usage for monitoring.
    Useful for debugging memory issues.
    """
    try:
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        mem_info = process.memory_info()
        mem_mb = mem_info.rss / (1024 * 1024)  # Convert to MB
        
        log(f"Memory usage: {mem_mb:.1f} MB", level="INFO")
        
    except ImportError:
        # psutil not available, use simpler method
        import resource
        mem_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        mem_mb = mem_kb / 1024  # Convert to MB
        log(f"Memory usage: ~{mem_mb:.1f} MB", level="INFO")
    except Exception as e:
        log(f"Could not log memory usage: {e}", level="WARNING")

# ============================================================================
# STANDALONE TESTING
# ============================================================================

if __name__ == "__main__":
    """
    Test logging functionality when run directly.
    """
    print("Testing DatabaseLogger...\n")
    
    # Use test database
    test_db_path = "/tmp/test_events.db"
    
    # Test 1: Create logger
    print("--- Test 1: Creating logger ---")
    logger = DatabaseLogger(test_db_path)
    
    # Test 2: Log various messages
    print("\n--- Test 2: Logging messages ---")
    logger.log("System startup test")
    logger.log("Motion detected in zone 1", level="INFO")
    logger.log("Low disk space warning", level="WARNING")
    logger.log("Failed to save video file", level="ERROR")
    logger.log("Camera reconnected", level="INFO")
    
    print(f"\nWaiting {LOG_BATCH_INTERVAL} seconds for batch write...")
    time.sleep(LOG_BATCH_INTERVAL + 1)
    
    # Test 3: Verify logs written to database
    print("\n--- Test 3: Verifying database ---")
    db = EventDatabase(test_db_path)
    log_count = db.get_log_count()
    print(f"Total logs in database: {log_count}")
    
    # Test 4: Multiple rapid logs
    print("\n--- Test 4: Rapid logging (10 messages) ---")
    for i in range(10):
        logger.log(f"Rapid test message {i+1}")
    
    print(f"Waiting {LOG_BATCH_INTERVAL} seconds for batch write...")
    time.sleep(LOG_BATCH_INTERVAL + 1)
    
    log_count = db.get_log_count()
    print(f"Total logs in database: {log_count}")
    
    # Test 5: Test global logger functions
    print("\n--- Test 5: Testing global logger functions ---")
    log("Testing global log function")
    log("Testing with warning level", level="WARNING")
    
    # Test 6: Force flush
    print("\n--- Test 6: Force flush ---")
    logger._flush_logs()
    log_count = db.get_log_count()
    print(f"Total logs after force flush: {log_count}")
    
    # Test 7: Graceful shutdown
    print("\n--- Test 7: Graceful shutdown ---")
    logger.log("Final message before shutdown")
    logger.stop()
    
    # Verify final count
    log_count = db.get_log_count()
    print(f"Final log count: {log_count}")
    
    print("\n✓ All tests completed successfully!")
    print(f"Test database: {test_db_path}")
    
    # Show some sample logs from database
    print("\n--- Sample logs from database ---")
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM logs ORDER BY timestamp DESC LIMIT 5")
    
    print("\nMost recent 5 logs:")
    for row in cursor.fetchall():
        print(f"  [{row['timestamp']}] [{row['level']}] {row['message']}")
    
    conn.close()