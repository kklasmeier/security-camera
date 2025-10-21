<?php
require_once '../includes/db.php';

header('Content-Type: application/json');

// Get action parameter
$action = $_GET['action'] ?? '';

if (!in_array($action, ['start', 'stop'])) {
    echo json_encode([
        'success' => false,
        'message' => 'Invalid action. Use start or stop.'
    ]);
    exit;
}

try {
    // Connect to database
    $db = new Database();
    
    // Set streaming flag
    $value = ($action === 'start') ? 1 : 0;
    $db->set_streaming_flag($value);
    
    // Return success
    echo json_encode([
        'success' => true,
        'streaming' => $value,
        'action' => $action,
        'message' => $action === 'start' ? 'Stream started' : 'Stream stopped'
    ]);
    
} catch (Exception $e) {
    echo json_encode([
        'success' => false,
        'message' => 'Database error: ' . $e->getMessage()
    ]);
}