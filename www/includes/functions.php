<?php
/**
 * Helper Functions for Security Camera Web Interface
 * Contains formatting and utility functions used across multiple pages
 */
date_default_timezone_set('America/New_York');
/**
 * Format event timestamp with smart relative dates
 * 
 * @param string $timestamp MySQL datetime string (e.g., "2025-10-19 14:30:45")
 * @return string Formatted timestamp
 * 
 * Returns:
 * - "2:34 PM" for today
 * - "Yesterday 2:34 PM" for yesterday
 * - "Tuesday 2:34 PM" for 2-7 days ago
 * - "Oct 12, 2025 2:34 PM" for 8+ days ago
 */
function format_event_timestamp($timestamp) {
    // Convert ISO format timestamp to Unix timestamp
    $event_time = strtotime($timestamp);
    
    // If strtotime failed, return the original timestamp
    if ($event_time === false) {
        return $timestamp;
    }
    
    $now = time();
    
    // Compare dates (not times) to determine which day
    $event_date = date('Y-m-d', $event_time);
    $today_date = date('Y-m-d', $now);
    $yesterday_date = date('Y-m-d', strtotime('-1 day', $now));
    
    // Today
    if ($event_date === $today_date) {
        return 'Today ' . date('g:i A', $event_time);
    }
    
    // Yesterday
    if ($event_date === $yesterday_date) {
        return 'Yesterday ' . date('g:i A', $event_time);
    }
    
    // Within last 7 days - show day of week
    $days_ago = floor(($now - $event_time) / 86400);
    if ($days_ago >= 2 && $days_ago <= 7) {
        return date('l g:i A', $event_time); // "Tuesday 2:34 PM"
    }
    
    // Older - show full date
    return date('M j, Y g:i A', $event_time); // "Oct 12, 2025 2:34 PM"
}

/**
 * Get motion score badge information
 * 
 * @param int $score Motion detection score (0-999+)
 * @return array ['color' => string, 'label' => string, 'emoji' => string]
 * 
 * Color coding:
 * - Low (0-149): Red - common, minor motion
 * - Medium (150-249): Yellow - moderate motion
 * - High (250+): Green - significant motion/activity
 */
function get_motion_badge($score) {
    if ($score >= 250) {
        return [
            'color' => 'high',    // CSS class: .badge-high
            'label' => 'High',
            'symbol' => '●'       // Solid circle (will be colored by CSS)
        ];
    } elseif ($score >= 150) {
        return [
            'color' => 'medium',  // CSS class: .badge-medium
            'label' => 'Medium',
            'symbol' => '●'       // Solid circle (will be colored by CSS)
        ];
    } else {
        return [
            'color' => 'low',     // CSS class: .badge-low
            'label' => 'Low',
            'symbol' => '●'       // Solid circle (will be colored by CSS)
        ];
    }
}

/**
 * Check if video is still being processed/converted
 * 
 * @param string $video_path Full path to MP4 file (e.g., "/home/pi/sec_cam/videos/20251019_143045.mp4")
 * @return bool True if .h264.pending file exists (still processing), false otherwise
 * 
 * The camera system creates a .h264.pending marker file while converting .h264 to .mp4
 * Example: /home/pi/sec_cam/videos/20251019_143045.h264.pending
 */
function is_video_processing($video_path) {
    // Don't process if video_path is empty or null
    if (empty($video_path)) {
        return false;
    }
    
    // Convert .mp4 path to .h264 path
    $h264_path = str_replace('.mp4', '.h264', $video_path);
    $pending_marker = $h264_path . '.pending';
    
    // Check if pending marker file exists
    return file_exists($pending_marker);
}

/**
 * Get web-accessible URL for event thumbnail
 * 
 * @param array $event Event record from database with 'thumbnail_path' key
 * @return string Web-accessible URL path (e.g., "/thumbs/20251019_143045_thumb.jpg")
 * 
 * Converts absolute filesystem path to web URL path
 * Returns placeholder if thumbnail doesn't exist
 */
function get_thumbnail_url($event) {
    // Check if thumbnail_path exists and file is readable
    if (!empty($event['thumbnail_path']) && file_exists($event['thumbnail_path'])) {
        // Convert absolute path to web path
        $web_path = str_replace('/home/pi/sec_cam', '', $event['thumbnail_path']);
        return $web_path;
    }
    
    // Fallback: return inline SVG placeholder (matches dark theme)
    return 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="320" height="180"%3E%3Crect fill="%231a1a1a" width="320" height="180"/%3E%3Ctext x="50%25" y="50%25" dominant-baseline="middle" text-anchor="middle" font-family="system-ui" font-size="48" fill="%23666"%3E📷%3C/text%3E%3Ctext x="50%25" y="65%25" dominant-baseline="middle" text-anchor="middle" font-family="system-ui" font-size="14" fill="%23666"%3ENo Image%3C/text%3E%3C/svg%3E';
}

/**
 * Sanitize and validate page number
 * 
 * @param mixed $page Raw page parameter from $_GET
 * @return int Valid page number (>= 1)
 */
function sanitize_page($page) {
    $page = (int)$page;
    return ($page < 1) ? 1 : $page;
}

/**
 * Sanitize and validate per_page parameter
 * 
 * @param mixed $per_page Raw per_page parameter from $_GET
 * @return int Valid per_page value (12, 24, 48, or 100)
 */
function sanitize_per_page($per_page) {
    $per_page = (int)$per_page;
    $allowed = [12, 24, 48, 100];
    
    return in_array($per_page, $allowed) ? $per_page : 12;
}

/**
 * Build pagination URL preserving current parameters
 * 
 * @param int $page Target page number
 * @param int $per_page Current per_page setting
 * @return string URL with query parameters
 */
function build_pagination_url($page, $per_page) {
    $params = [];
    
    if ($page > 1) {
        $params[] = 'page=' . $page;
    }
    
    if ($per_page != 12) {
        $params[] = 'per_page=' . $per_page;
    }
    
    return 'index.php' . (count($params) > 0 ? '?' . implode('&', $params) : '');
}

/**
 * Format file size for display
 * 
 * @param int $bytes File size in bytes
 * @return string Formatted size (e.g., "2.5 MB")
 */
function format_file_size($bytes) {
    if ($bytes == 0) return '0 B';
    
    $units = ['B', 'KB', 'MB', 'GB'];
    $factor = floor((strlen($bytes) - 1) / 3);
    
    return sprintf("%.1f %s", $bytes / pow(1024, $factor), $units[$factor]);
}

/**
 * Format duration in seconds to readable format
 * 
 * @param int $seconds Duration in seconds
 * @return string Formatted duration (e.g., "30s", "1m 45s", "1h 2m")
 */
function format_duration($seconds) {
    if ($seconds < 60) {
        return $seconds . 's';
    } elseif ($seconds < 3600) {
        $minutes = floor($seconds / 60);
        $secs = $seconds % 60;
        return $secs > 0 ? "{$minutes}m {$secs}s" : "{$minutes}m";
    } else {
        $hours = floor($seconds / 3600);
        $minutes = floor(($seconds % 3600) / 60);
        return $minutes > 0 ? "{$hours}h {$minutes}m" : "{$hours}h";
    }
}

/**
 * Convert video file path to web URL
 * 
 * @param array $event Event record with 'video_path' key
 * @return string|null Web URL or null if not available
 */
function get_video_url($event) {
    if (empty($event['video_path']) || !file_exists($event['video_path'])) {
        return null;
    }
    
    // Convert absolute path to web path
    // /home/pi/sec_cam/videos/file.mp4 → /videos/file.mp4
    return str_replace('/home/pi/sec_cam', '', $event['video_path']);
}

/**
 * Convert image file path to web URL
 * 
 * @param string $path Absolute file path
 * @return string|null Web URL or null if not available
 */
function get_image_url($path) {
    if (empty($path) || !file_exists($path)) {
        return null;
    }
    
    // Convert absolute path to web path
    // /home/pi/sec_cam/pictures/file.jpg → /pictures/file.jpg
    return str_replace('/home/pi/sec_cam', '', $path);
}

/**
 * Get formatted file size from file path
 * 
 * @param string $path Absolute file path
 * @return string Formatted size (e.g., "2.3 MB") or "N/A"
 */
function get_file_size($path) {
    if (empty($path) || !file_exists($path)) {
        return 'N/A';
    }
    
    $bytes = filesize($path);
    
    if ($bytes >= 1073741824) {
        return number_format($bytes / 1073741824, 2) . ' GB';
    } elseif ($bytes >= 1048576) {
        return number_format($bytes / 1048576, 2) . ' MB';
    } elseif ($bytes >= 1024) {
        return number_format($bytes / 1024, 2) . ' KB';
    } else {
        return $bytes . ' bytes';
    }
}

/**
 * Format log timestamp for display
 * Logs always show full timestamp for diagnostic purposes
 * Format: Oct 19, 2025 8:43:15 PM
 * 
 * @param string $timestamp ISO format timestamp from database
 * @return string Formatted timestamp
 */
function format_log_timestamp($timestamp) {
    $time = strtotime($timestamp);
    return date('M j, Y g:i:s A', $time);
}

?>