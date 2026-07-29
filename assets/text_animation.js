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
 * Claude-style typewriter animation for the navbar title.
 * Streams "dash-leaflet2" character-by-character with a blinking cursor.
 * Re-fires on Dash SPA navigation when the title node is re-rendered.
 */

document.addEventListener('DOMContentLoaded', function() {
    window.DL2_LOG('Text animation handler loaded');

    const TEXT_TO_TYPE = "dash-leaflet2";
    const TYPING_SPEED = 80;  // ms per character
    const INITIAL_DELAY = 500;  // delay before first char

    // Function to get the title element
    function getTitleElement() {
        return document.getElementById('dash-docs-title');
    }

    // Function to type out text character by character
    function typeWriter(text, element, index = 0) {
        if (index < text.length) {
            // Add next character
            element.textContent = text.substring(0, index + 1);

            // Continue to next character
            setTimeout(() => typeWriter(text, element, index + 1), TYPING_SPEED);
        } else {
            // Animation complete - remove typing class
            element.classList.remove('typing');
            window.DL2_LOG('Typing animation complete');
        }
    }

    // Function to start the animation
    function startAnimation() {
        const titleElement = getTitleElement();

        if (titleElement) {
            // Clear text and add typing class for cursor
            titleElement.textContent = '';
            titleElement.classList.add('typing');

            // Start typing after initial delay
            setTimeout(() => {
                typeWriter(TEXT_TO_TYPE, titleElement);
            }, INITIAL_DELAY);

            window.DL2_LOG('Started text animation');
        } else {
            window.DL2_LOG('Title element not found');
        }
    }

    // Run animation on initial load
    startAnimation();

    // Re-run animation when navigating (for Dash SPA)
    const observer = new MutationObserver(function(mutations) {
        // Check if the title element was re-rendered
        const titleElement = getTitleElement();
        if (titleElement && titleElement.textContent === TEXT_TO_TYPE && !titleElement.dataset.animated) {
            // Mark as animated to prevent re-animation on same element
            titleElement.dataset.animated = 'true';

            // Clear and restart animation
            clearTimeout(window.titleAnimationTimeout);
            window.titleAnimationTimeout = setTimeout(startAnimation, 100);
        }
    });

    // Observe document for changes
    observer.observe(document.body, {
        childList: true,
        subtree: true
    });

    window.DL2_LOG('Text animation observer active');
});

