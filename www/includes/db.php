<?php

class Database {
    private $db_path;
    private $pdo;
    
    public function __construct($db_path = '/home/pi/sec_cam/events.db') {
        $this->db_path = $db_path;
        $this->connect();
    }
    
    private function connect() {
        try {
            if (!file_exists($this->db_path)) {
                throw new Exception("Database file not found: {$this->db_path}");
            }
            
            $this->pdo = new PDO("sqlite:{$this->db_path}");
            $this->pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
            $this->pdo->setAttribute(PDO::ATTR_DEFAULT_FETCH_MODE, PDO::FETCH_ASSOC);
        } catch (Exception $e) {
            error_log("Database connection error: " . $e->getMessage());
            $this->pdo = null;
        }
    }
    
    public function isConnected() {
        return $this->pdo !== null;
    }
    
    // ========================================
    // EVENTS METHODS
    // ========================================
    
    /**
     * Get recent events with pagination
     * @param int $limit Number of events to return
     * @param int $offset Starting position
     * @return array Array of event records
     */
    public function get_recent_events($limit = 12, $offset = 0) {
        if (!$this->isConnected()) return [];
        
        try {
            $stmt = $this->pdo->prepare("
                SELECT * FROM events 
                ORDER BY timestamp DESC 
                LIMIT :limit OFFSET :offset
            ");
            $stmt->bindValue(':limit', $limit, PDO::PARAM_INT);
            $stmt->bindValue(':offset', $offset, PDO::PARAM_INT);
            $stmt->execute();
            
            return $stmt->fetchAll();
        } catch (Exception $e) {
            error_log("Error fetching recent events: " . $e->getMessage());
            return [];
        }
    }
    
    /**
     * Get single event by ID
     * @param int $id Event ID
     * @return array|null Event record or null if not found
     */
    public function get_event_by_id($id) {
        if (!$this->isConnected()) return null;
        
        try {
            $stmt = $this->pdo->prepare("
                SELECT * FROM events 
                WHERE id = :id
            ");
            $stmt->bindValue(':id', $id, PDO::PARAM_INT);
            $stmt->execute();
            
            $result = $stmt->fetch();
            return $result !== false ? $result : null;
        } catch (Exception $e) {
            error_log("Error fetching event by ID: " . $e->getMessage());
            return null;
        }
    }
    
    /**
     * Get total count of events
     * @return int Total number of events
     */
    public function get_event_count() {
        if (!$this->isConnected()) return 0;
        
        try {
            $stmt = $this->pdo->query("SELECT COUNT(*) as count FROM events");
            $result = $stmt->fetch();
            return (int)$result['count'];
        } catch (Exception $e) {
            error_log("Error getting event count: " . $e->getMessage());
            return 0;
        }
    }
    
    /**
     * Get next event ID (for navigation)
     * @param int $current_id Current event ID
     * @return int|null Next event ID or null if none
     */
    public function get_next_event_id($current_id) {
        if (!$this->isConnected()) return null;
        
        try {
            $stmt = $this->pdo->prepare("
                SELECT id FROM events 
                WHERE id > :current_id 
                ORDER BY id ASC 
                LIMIT 1
            ");
            $stmt->bindValue(':current_id', $current_id, PDO::PARAM_INT);
            $stmt->execute();
            
            $result = $stmt->fetch();
            return $result ? (int)$result['id'] : null;
        } catch (Exception $e) {
            error_log("Error getting next event ID: " . $e->getMessage());
            return null;
        }
    }
    
    /**
     * Get previous event ID (for navigation)
     * @param int $current_id Current event ID
     * @return int|null Previous event ID or null if none
     */
    public function get_previous_event_id($current_id) {
        if (!$this->isConnected()) return null;
        
        try {
            $stmt = $this->pdo->prepare("
                SELECT id FROM events 
                WHERE id < :current_id 
                ORDER BY id DESC 
                LIMIT 1
            ");
            $stmt->bindValue(':current_id', $current_id, PDO::PARAM_INT);
            $stmt->execute();
            
            $result = $stmt->fetch();
            return $result ? (int)$result['id'] : null;
        } catch (Exception $e) {
            error_log("Error getting previous event ID: " . $e->getMessage());
            return null;
        }
    }
    
    /**
     * Get logs with optional filtering
     * @param int $limit Number of logs to return
     * @param int $offset Starting position
     * @param array|null $level_filter Array of log levels to filter (e.g., ['INFO', 'WARNING'])
     * @param string $order Sort order: 'ASC' or 'DESC' (default: DESC)
     * @return array Array of log records
     */
    public function get_logs($limit = 1000, $offset = 0, $level_filter = null, $order = 'DESC') {
        if (!$this->isConnected()) return [];
        
        try {
            $sql = "SELECT * FROM logs";
            
            // Handle array of level filters
            if ($level_filter && is_array($level_filter) && !empty($level_filter)) {
                $placeholders = [];
                foreach ($level_filter as $index => $level) {
                    $placeholders[] = ":level{$index}";
                }
                $sql .= " WHERE level IN (" . implode(',', $placeholders) . ")";
            }
            
            // Validate order parameter
            $order = strtoupper($order) === 'ASC' ? 'ASC' : 'DESC';
            
            // Always get newest logs first, then optionally reverse
            $sql .= " ORDER BY timestamp DESC LIMIT :limit OFFSET :offset";
            
            $stmt = $this->pdo->prepare($sql);
            
            // Bind level filter values
            if ($level_filter && is_array($level_filter) && !empty($level_filter)) {
                foreach ($level_filter as $index => $level) {
                    $stmt->bindValue(":level{$index}", $level, PDO::PARAM_STR);
                }
            }
            
            $stmt->bindValue(':limit', $limit, PDO::PARAM_INT);
            $stmt->bindValue(':offset', $offset, PDO::PARAM_INT);
            $stmt->execute();
            
            $results = $stmt->fetchAll();
            
            // If ASC requested, reverse the array (newest at bottom)
            if ($order === 'ASC') {
                $results = array_reverse($results);
            }
            
            return $results;
        } catch (Exception $e) {
            error_log("Error fetching logs: " . $e->getMessage());
            return [];
        }
    }    
    
    /**
     * Get count of logs with optional filtering
     * @param string|null $level_filter Filter by log level
     * @return int Total number of logs
     */
    public function get_log_count($level_filter = null) {
        if (!$this->isConnected()) return 0;
        
        try {
            $sql = "SELECT COUNT(*) as count FROM logs";
            
            if ($level_filter && in_array($level_filter, ['INFO', 'WARNING', 'ERROR'])) {
                $sql .= " WHERE level = :level";
            }
            
            $stmt = $this->pdo->prepare($sql);
            
            if ($level_filter && in_array($level_filter, ['INFO', 'WARNING', 'ERROR'])) {
                $stmt->bindValue(':level', $level_filter, PDO::PARAM_STR);
            }
            
            $stmt->execute();
            $result = $stmt->fetch();
            return (int)$result['count'];
        } catch (Exception $e) {
            error_log("Error getting log count: " . $e->getMessage());
            return 0;
        }
    }
    
    /**
     * Get logs since a specific timestamp (for "Get More" functionality)
     * @param string $timestamp ISO format timestamp
     * @param array|null $level_filter Array of log levels to filter
     * @return array Array of log records
     */
    public function get_logs_since($timestamp, $level_filter = null) {
        if (!$this->isConnected()) return [];
        
        try {
            $sql = "SELECT * FROM logs WHERE timestamp > :timestamp";
            
            // Handle array of level filters
            if ($level_filter && is_array($level_filter) && !empty($level_filter)) {
                $placeholders = [];
                foreach ($level_filter as $index => $level) {
                    $placeholders[] = ":level{$index}";
                }
                $sql .= " AND level IN (" . implode(',', $placeholders) . ")";
            }
            
            $sql .= " ORDER BY timestamp ASC";
            
            $stmt = $this->pdo->prepare($sql);
            $stmt->bindValue(':timestamp', $timestamp, PDO::PARAM_STR);
            
            // Bind level filter values
            if ($level_filter && is_array($level_filter) && !empty($level_filter)) {
                foreach ($level_filter as $index => $level) {
                    $stmt->bindValue(":level{$index}", $level, PDO::PARAM_STR);
                }
            }
            
            $stmt->execute();
            
            return $stmt->fetchAll();
        } catch (Exception $e) {
            error_log("Error fetching logs since timestamp: " . $e->getMessage());
            return [];
        }
    }
    
    // ========================================
    // SYSTEM CONTROL METHODS
    // ========================================
    
    /**
     * Get streaming flag status
     * @return int 0 or 1
     */
    public function get_streaming_flag() {
        if (!$this->isConnected()) return 0;
        
        try {
            $stmt = $this->pdo->query("
                SELECT streaming FROM system_control WHERE id = 1
            ");
            $result = $stmt->fetch();
            
            if ($result) {
                return (int)$result['streaming'];
            }
            
            // If no record exists, create one
            $this->pdo->exec("
                INSERT OR IGNORE INTO system_control (id, streaming) 
                VALUES (1, 0)
            ");
            return 0;
        } catch (Exception $e) {
            error_log("Error getting streaming flag: " . $e->getMessage());
            return 0;
        }
    }
    
    /**
     * Set streaming flag status
     * @param int $value 0 or 1
     * @return bool Success status
     */
    public function set_streaming_flag($value) {
        if (!$this->isConnected()) return false;
        
        try {
            $value = $value ? 1 : 0;
            
            $stmt = $this->pdo->prepare("
                INSERT OR REPLACE INTO system_control (id, streaming, updated_at) 
                VALUES (1, :streaming, CURRENT_TIMESTAMP)
            ");
            $stmt->bindValue(':streaming', $value, PDO::PARAM_INT);
            $stmt->execute();
            
            return true;
        } catch (Exception $e) {
            error_log("Error setting streaming flag: " . $e->getMessage());
            return false;
        }
    }
}
