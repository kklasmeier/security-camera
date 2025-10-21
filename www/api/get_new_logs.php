<?php
/**
 * AJAX Endpoint: Get New Logs
 * Fetches logs newer than a given timestamp with level filtering
 */

require_once '../includes/db.php';

header('Content-Type: application/json');

// Get parameters
$since = $_GET['since'] ?? '';
$filter_info = isset($_GET['info']) && $_GET['info'] == '1';
$filter_warning = isset($_GET['warning']) && $_GET['warning'] == '1';
$filter_error = isset($_GET['error']) && $_GET['error'] == '1';
// Build level filter array
$level_filter = [];
if ($filter_info) $level_filter[] = 'INFO';
if ($filter_warning) $level_filter[] = 'WARNING';
if ($filter_error) $level_filter[] = 'ERROR';

try {
    // Get new logs since timestamp
    $db = new Database();
    $logs = $db->get_logs_since($since, $level_filter);
    
    // Return JSON response
    echo json_encode([
        'success' => true,
        'logs' => $logs,
        'count' => count($logs)
    ]);
    
} catch (Exception $e) {
    // Handle errors gracefully
    http_response_code(500);
    echo json_encode([
        'success' => false,
        'error' => 'Failed to fetch logs',
        'count' => 0,
        'logs' => []
    ]);
}