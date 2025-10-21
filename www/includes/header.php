<?php
// Determine current page for active navigation highlighting
$current_page = basename($_SERVER['PHP_SELF']);

// Default page title
$page_title = isset($page_title) ? $page_title : 'Security Camera System';
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title><?php echo htmlspecialchars($page_title); ?></title>
    <link rel="icon" type="image/x-icon" href="/assets/favicon.ico">
    <link rel="icon" type="image/png" sizes="32x32" href="/assets/favicon-32x32.png">
    <link rel="icon" type="image/png" sizes="16x16" href="/assets/favicon-16x16.png">
    <link rel="stylesheet" href="/assets/style.css">
</head>
<body>
    <header class="site-header">
        <div class="header-container">
            <div class="logo">
                <img src="/assets/camera-logo.png" alt="Camera" class="logo-icon" style="width: 32px; height: 32px; vertical-align: middle;">
                <span class="logo-text-full">Security Camera System</span>
                <span class="logo-text-short">Sec Cam</span>
            </div>
            
            <button class="hamburger" id="hamburger" aria-label="Toggle navigation">
                <span class="hamburger-line"></span>
                <span class="hamburger-line"></span>
                <span class="hamburger-line"></span>
            </button>
            
            <nav class="nav-menu" id="navMenu">
                <a href="/index.php" class="nav-link <?php echo ($current_page == 'index.php' || $current_page == '') ? 'active' : ''; ?>">
                    Events
                </a>
                <a href="/live.php" class="nav-link <?php echo $current_page == 'live.php' ? 'active' : ''; ?>">
                    Live View
                </a>
                <a href="/logs.php" class="nav-link <?php echo $current_page == 'logs.php' ? 'active' : ''; ?>">
                    Logs
                </a>
            </nav>
        </div>
    </header>
    
    <main class="main-content">