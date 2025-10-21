<?php
/**
 * Logs Page - System Log Viewer
 * Terminal-style display with filtering and AJAX "Get More" functionality
 */

require_once 'includes/db.php';
require_once 'includes/functions.php';

$db = new Database();

// Parse filter parameters from URL
$filter_info = isset($_GET['info']) ? 1 : 0;
$filter_warning = isset($_GET['warning']) ? 1 : 0;
$filter_error = isset($_GET['error']) ? 1 : 0;

// If no filters in URL, default to all checked
if (!isset($_GET['info']) && !isset($_GET['warning']) && !isset($_GET['error'])) {
    $filter_info = 1;
    $filter_warning = 1;
    $filter_error = 1;
}

// Build level filter array
$level_filter = [];
if ($filter_info) $level_filter[] = 'INFO';
if ($filter_warning) $level_filter[] = 'WARNING';
if ($filter_error) $level_filter[] = 'ERROR';

// DEBUG - Remove this later
echo "<!-- DEBUG: filter_info=$filter_info, filter_warning=$filter_warning, filter_error=$filter_error -->";
echo "<!-- DEBUG: level_filter=" . implode(',', $level_filter) . " -->";
echo "<!-- DEBUG: log count=" . count($logs ?? []) . " -->";

// Get last 1000 logs with current filter
$logs = [];
$no_filters_selected = empty($level_filter);

if (!$no_filters_selected) {
    $logs = $db->get_logs(1000, 0, $level_filter, 'ASC');
    
    // DEBUG
    echo "<!-- DEBUG: After query, log count=" . count($logs) . " -->";
    if (!empty($logs)) {
        echo "<!-- DEBUG: First log level=" . $logs[0]['level'] . " -->";
        echo "<!-- DEBUG: Last log level=" . $logs[count($logs)-1]['level'] . " -->";
    }
}

// Get the most recent timestamp for "Get More" functionality
$last_timestamp = !empty($logs) ? $logs[0]['timestamp'] : '';

// Page title
$page_title = 'System Logs';

// Include header
include 'includes/header.php';
?>

<div class="container">
    <h1 class="logs-title">System Logs</h1>
    
    <!-- Filter Form -->
    <form method="get" action="logs.php" class="log-filters">
        <label class="filter-checkbox">
            <input 
                type="checkbox" 
                name="info" 
                value="1"
                <?php echo $filter_info ? 'checked' : ''; ?>
                onchange="this.form.submit()"
            >
            <span class="filter-label">INFO</span>
        </label>
        
        <label class="filter-checkbox">
            <input 
                type="checkbox" 
                name="warning" 
                value="1"
                <?php echo $filter_warning ? 'checked' : ''; ?>
                onchange="this.form.submit()"
            >
            <span class="filter-label">WARNING</span>
        </label>
        
        <label class="filter-checkbox">
            <input 
                type="checkbox" 
                name="error" 
                value="1"
                <?php echo $filter_error ? 'checked' : ''; ?>
                onchange="this.form.submit()"
            >
            <span class="filter-label">ERROR</span>
        </label>
    </form>
    
    <?php if ($no_filters_selected): ?>
        <!-- No Filters Selected Message -->
        <div class="logs-status" style="text-align: center; padding: var(--space-xl); color: var(--color-text-secondary);">
            Please select at least one filter level
        </div>
    <?php elseif (empty($logs)): ?>
        <!-- No Logs Found Message -->
        <div class="logs-status" style="text-align: center; padding: var(--space-xl); color: var(--color-text-secondary);">
            No logs found for selected filters
        </div>
    <?php else: ?>
        <!-- Logs Table -->
        <div class="logs-container">
            <table class="logs-table">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Timestamp</th>
                        <th>Level</th>
                        <th>Message</th>
                    </tr>
                </thead>
                <tbody id="logs-tbody">
                    <?php foreach ($logs as $log): ?>
                        <tr class="log-row log-<?php echo strtolower($log['level']); ?>">
                            <td class="log-id"><?php echo htmlspecialchars($log['id']); ?></td>
                            <td class="log-timestamp">
                                <?php echo format_log_timestamp($log['timestamp']); ?>
                            </td>
                            <td class="log-level">
                                <span class="level-badge level-<?php echo strtolower($log['level']); ?>">
                                    <?php echo htmlspecialchars($log['level']); ?>
                                </span>
                            </td>
                            <td class="log-message"><?php echo htmlspecialchars($log['message']); ?></td>
                        </tr>
                    <?php endforeach; ?>
                </tbody>
            </table>
        </div>
        
        <!-- Get More Button and Status -->
        <div class="logs-actions">
            <button id="get-more-btn" class="btn btn-primary" onclick="getMoreLogs()">
                Get More Logs
            </button>
        </div>
        
        <div id="logs-status" class="logs-status">
            Showing <?php echo count($logs); ?> most recent logs
        </div>
        
        <!-- Hidden inputs for JavaScript -->
        <input type="hidden" id="last-timestamp" value="<?php echo htmlspecialchars($last_timestamp); ?>">
        <input type="hidden" id="filter-info" value="<?php echo $filter_info; ?>">
        <input type="hidden" id="filter-warning" value="<?php echo $filter_warning; ?>">
        <input type="hidden" id="filter-error" value="<?php echo $filter_error; ?>">
    <?php endif; ?>
</div>

<script>
// Auto-scroll to bottom on page load
document.addEventListener('DOMContentLoaded', function() {
    const container = document.querySelector('.logs-container');
    if (container) {
        container.scrollTop = container.scrollHeight;
    }
});
</script>

<?php
// Include footer
include 'includes/footer.php';
?>