<?php
require_once 'includes/db.php';
require_once 'includes/functions.php';

$db = new Database();
$event = $db->get_event_by_id(1523);

echo "Video URL: " . get_video_url($event) . "\n";
echo "Image A URL: " . get_image_url($event['image_a_path']) . "\n";
echo "Video Size: " . get_file_size($event['video_path']) . "\n";
echo "Processing: " . (is_video_processing($event['video_path']) ? 'Yes' : 'No') . "\n";