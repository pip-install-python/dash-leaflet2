/* Debug logging, off by default. These handlers fire on every scroll event and
 * flooded the production console with hundreds of identical lines, burying real
 * errors. Set window.DL2_DEBUG = true in the console to turn them back on.
 *
 * Assigned to `window`, NOT declared with const/let: assets/*.js are classic
 * scripts sharing one global lexical scope, so a top-level `const log` in each
 * file throws "Identifier 'log' has already been declared" in every file after
 * the first. The ||= keeps it idempotent whatever order Dash loads them in. */
window.DL2_LOG = window.DL2_LOG ||
    function () { if (window.DL2_DEBUG) console.log.apply(console, arguments); };

/**
 * Sun Icon Rotation on Scroll
 * Rotates the sun icon (light theme icon) while user scrolls
 */

document.addEventListener('DOMContentLoaded', function() {
    window.DL2_LOG('Sun rotation handler loaded');

    let scrollTimeout;
    let lastScrollY = window.scrollY;

    // Function to get sun icon (refreshed each time)
    function getSunIcon() {
        return document.getElementById('light-theme-icon');
    }

    // Function to add rotating class based on direction
    function startRotation(direction) {
        const sunIcon = getSunIcon();
        if (sunIcon) {
            // Remove both classes first
            sunIcon.classList.remove('rotating-up', 'rotating-down');

            // Add the appropriate class
            if (direction === 'down') {
                sunIcon.classList.add('rotating-down');
                window.DL2_LOG('Started sun rotation - clockwise (scrolling down)');
            } else {
                sunIcon.classList.add('rotating-up');
                window.DL2_LOG('Started sun rotation - counter-clockwise (scrolling up)');
            }
        } else {
            window.DL2_LOG('Sun icon not found');
        }
    }

    // Function to remove rotating classes
    function stopRotation() {
        const sunIcon = getSunIcon();
        if (sunIcon) {
            sunIcon.classList.remove('rotating-up', 'rotating-down');
            window.DL2_LOG('Stopped sun rotation');
        }
    }

    // Handle scroll event
    function handleScroll() {
        const currentScrollY = window.scrollY;

        // Determine scroll direction
        const scrollDirection = currentScrollY > lastScrollY ? 'down' : 'up';

        // Update last scroll position
        lastScrollY = currentScrollY;

        // Start rotation with direction
        startRotation(scrollDirection);

        // Clear existing timeout
        clearTimeout(scrollTimeout);

        // Stop rotation after 200ms of no scrolling for smoother deceleration
        scrollTimeout = setTimeout(function() {
            stopRotation();
        }, 200);
    }

    // Add scroll listener with debug
    window.addEventListener('scroll', handleScroll, { passive: true });
    window.DL2_LOG('Scroll listener attached');

    // Setup with MutationObserver for Dash page updates
    function setupSunRotation() {
        const newSunIcon = document.getElementById('light-theme-icon');
        if (newSunIcon) {
            if (!newSunIcon.dataset.rotationSetup) {
                newSunIcon.dataset.rotationSetup = 'true';
                window.DL2_LOG('Sun rotation setup complete - icon found');
            }
        } else {
            window.DL2_LOG('Sun icon not found during setup');
        }
    }

    // Initial setup
    setupSunRotation();

    // Delayed setup for Dash-rendered content
    setTimeout(setupSunRotation, 500);
    setTimeout(setupSunRotation, 1000);

    // Re-run setup when Dash updates the page
    const observer = new MutationObserver(function(mutations) {
        clearTimeout(window.sunRotationTimeout);
        window.sunRotationTimeout = setTimeout(setupSunRotation, 100);
    });

    // Observe the document for changes
    observer.observe(document.body, {
        childList: true,
        subtree: true
    });

    window.DL2_LOG('Sun rotation observer active');
});
