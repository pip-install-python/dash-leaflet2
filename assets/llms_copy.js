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
 * Per-page "Copy llms.txt URL" button handler.
 *
 * Wires up every `.llms-copy-button` so that clicking it copies
 * `<origin>/<page-path>/llms.txt` to the clipboard. Paste the result
 * into ChatGPT, Claude, or any LLM to share the page's prose docs.
 *
 * The `llms.toon` and `page.json` button handlers were removed in v0.5.0
 * — `dash-improve-my-llms` 2.0 dropped both endpoints.
 */

document.addEventListener('DOMContentLoaded', function () {
    window.DL2_LOG('LLM copy-button handler loaded');

    async function copyToClipboard(text) {
        // Modern Clipboard API path
        if (navigator.clipboard && navigator.clipboard.writeText) {
            try {
                await navigator.clipboard.writeText(text);
                return true;
            } catch (err) {
                console.warn('Clipboard API failed, trying fallback:', err);
            }
        }

        // Fallback for non-secure contexts (HTTP / older browsers)
        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.focus();
        textarea.select();
        try {
            const success = document.execCommand('copy');
            document.body.removeChild(textarea);
            return success;
        } catch (err) {
            console.error('execCommand failed:', err);
            document.body.removeChild(textarea);
            return false;
        }
    }

    function cleanPagePath() {
        const p = window.location.pathname;
        return p.endsWith('/') ? p.slice(0, -1) : p;
    }

    function flashButton(button, originalText, message, color) {
        button.textContent = message;
        button.style.color = color;
        setTimeout(() => {
            button.textContent = originalText;
            button.style.color = '';
        }, 2000);
    }

    function setupCopyButtons() {
        const byClass = document.querySelectorAll('.llms-copy-button');
        const byId = document.querySelectorAll('[id^="llm-copy-button-"]');
        const all = new Set([...byClass, ...byId]);

        all.forEach((button) => {
            if (button.dataset.copySetup) return;
            button.dataset.copySetup = 'true';

            button.addEventListener('click', async function (e) {
                e.preventDefault();
                e.stopPropagation();

                try {
                    const url = `${window.location.origin}${cleanPagePath()}/llms.txt`;
                    const ok = await copyToClipboard(url);
                    const original = button.textContent;
                    if (ok) {
                        flashButton(button, original, '✓ Copied!', 'var(--mantine-color-teal-6)');
                        window.DL2_LOG('Copied to clipboard:', url);
                    } else {
                        throw new Error('All copy methods failed');
                    }
                } catch (err) {
                    console.error('Failed to copy:', err);
                    const original = button.textContent;
                    flashButton(button, original, '❌ Failed', 'var(--mantine-color-red-6)');
                }
            });
        });
    }

    // Initial pass
    setupCopyButtons();

    // Dash sometimes finishes rendering after DOMContentLoaded; re-bind
    // a couple of times on a delay to catch late-arriving nodes.
    setTimeout(setupCopyButtons, 500);
    setTimeout(setupCopyButtons, 1000);
    setTimeout(setupCopyButtons, 2000);

    // Re-run on any page change
    const observer = new MutationObserver(() => {
        clearTimeout(window.llmsCopyTimeout);
        window.llmsCopyTimeout = setTimeout(setupCopyButtons, 100);
    });
    const target = document.getElementById('_pages_content') || document.body;
    observer.observe(target, { childList: true, subtree: true });

    window.DL2_LOG('LLM copy-button observer active');
});
