import { useEffect, useRef } from 'react';
import { useLeafletMap, useLeafletBearing } from '../context';
import { DashComponentProps } from '../props';

type Props = {
    /**
     * Whether keyboard input is processed. When `false`, no key handler is
     * installed. Useful for disabling controls while a modal/form is focused.
     * [MUTABLE]
     */
    enabled?: boolean;

    /**
     * Degrees of map bearing change per ArrowLeft / ArrowRight keypress.
     * Default 5.
     */
    bearingStep?: number;

    /**
     * Pixels of map pan per Cmd+Arrow / Ctrl+Arrow keypress. Default 80
     * (matches Leaflet's own keyboard panOffset).
     */
    panStep?: number;

    /**
     * Direction map: each property holds the action ('rotate-cw', 'rotate-ccw',
     * 'pan-up', 'pan-down', 'pan-left', 'pan-right') triggered by a given
     * key + modifier combination. Defaults to:
     *
     *   ArrowLeft        → rotate-ccw  (turn camera left)
     *   ArrowRight       → rotate-cw   (turn camera right)
     *   ArrowUp          → rotate-ccw  (same — feels natural for flight sims)
     *   ArrowDown        → rotate-cw
     *   Cmd|Ctrl+ArrowLeft   → pan-left
     *   Cmd|Ctrl+ArrowRight  → pan-right
     *   Cmd|Ctrl+ArrowUp     → pan-up
     *   Cmd|Ctrl+ArrowDown   → pan-down
     *
     * Pages can override individual entries (e.g. flight sims that want
     * ArrowUp/Down to be throttle, not rotation) by passing a partial object.
     */
    keymap?: Record<string, string>;

    /**
     * Number of bearing changes emitted (each rotate keypress increments).
     * Useful as the sole Input for "did the user rotate?". [READONLY]
     */
    n_rotations?: number;

    /**
     * Number of pan keypresses processed. [READONLY]
     */
    n_pans?: number;

    /**
     * The most recent key + action processed, as
     * { key, action, modifier, ts }. [READONLY]
     */
    lastKey?: { key: string; action: string; modifier: boolean; ts: number };
} & DashComponentProps;

const DEFAULT_KEYMAP: Record<string, string> = {
    'ArrowLeft':      'rotate-ccw',
    'ArrowRight':     'rotate-cw',
    'ArrowUp':        'rotate-ccw',
    'ArrowDown':      'rotate-cw',
    'mod+ArrowLeft':  'pan-left',
    'mod+ArrowRight': 'pan-right',
    'mod+ArrowUp':    'pan-up',
    'mod+ArrowDown':  'pan-down',
};

/**
 * KeyboardControl installs a window-level keyboard listener that drives map
 * rotation and pan. Place it as a child of <Map>. No DOM is rendered — it's a
 * pure side-effect component.
 *
 * Default behavior:
 *   - Arrow keys rotate the map bearing (5° / press by default)
 *   - Cmd / Ctrl + Arrow keys pan the map (Leaflet's built-in arrow-key panning
 *     is suppressed by `map.keyboard.disable()` so the two don't both fire)
 *
 * This makes the page feel like a flight sim: the arrows turn the camera, the
 * modifier is the "manual pan" escape hatch. Pages can flip the bindings by
 * passing a custom `keymap`.
 *
 * Listens on `window`, not the map container — so a user pressing arrows while
 * the map div doesn't have focus still rotates. Pages with form inputs should
 * either set `enabled=false` while the form is focused or override the keymap.
 */
const KeyboardControl = ({
    enabled = true,
    bearingStep = 5,
    panStep = 80,
    keymap,
    setProps,
}: Props) => {
    const map = useLeafletMap();
    const { bearing, setBearing } = useLeafletBearing();

    // Refs so the listener (bound once) can see the latest values.
    const bearingRef = useRef(bearing);
    bearingRef.current = bearing;
    const stepRef = useRef(bearingStep);
    stepRef.current = bearingStep;
    const panStepRef = useRef(panStep);
    panStepRef.current = panStep;
    const enabledRef = useRef(enabled);
    enabledRef.current = enabled;
    const keymapRef = useRef<Record<string, string>>({ ...DEFAULT_KEYMAP, ...(keymap || {}) });
    keymapRef.current = { ...DEFAULT_KEYMAP, ...(keymap || {}) };

    const rotationsRef = useRef(0);
    const pansRef = useRef(0);

    useEffect(() => {
        if (!map) return;
        // Disable Leaflet's built-in arrow-key panning — our keymap owns those
        // keys now. The user gets pan back via Cmd/Ctrl+Arrow (handled here).
        try { (map as any).keyboard?.disable(); } catch (e) {}

        const onKeyDown = (e: KeyboardEvent) => {
            if (!enabledRef.current) return;
            // Ignore if the user is typing in an input/textarea.
            const t = e.target as HTMLElement;
            if (t && /input|textarea|select/i.test(t.tagName)) return;
            if ((t as any)?.isContentEditable) return;

            const mod = e.metaKey || e.ctrlKey;
            const lookup = (mod ? 'mod+' : '') + e.key;
            const action = keymapRef.current[lookup];
            if (!action) return;
            e.preventDefault();

            switch (action) {
                case 'rotate-cw':
                    setBearing(bearingRef.current + stepRef.current);
                    rotationsRef.current += 1;
                    break;
                case 'rotate-ccw':
                    setBearing(bearingRef.current - stepRef.current);
                    rotationsRef.current += 1;
                    break;
                case 'pan-up':
                    (map as any).panBy([0, -panStepRef.current]);
                    pansRef.current += 1;
                    break;
                case 'pan-down':
                    (map as any).panBy([0, panStepRef.current]);
                    pansRef.current += 1;
                    break;
                case 'pan-left':
                    (map as any).panBy([-panStepRef.current, 0]);
                    pansRef.current += 1;
                    break;
                case 'pan-right':
                    (map as any).panBy([panStepRef.current, 0]);
                    pansRef.current += 1;
                    break;
                default:
                    return;
            }

            if (setProps) {
                setProps({
                    n_rotations: rotationsRef.current,
                    n_pans: pansRef.current,
                    lastKey: {
                        key: e.key,
                        action,
                        modifier: mod,
                        ts: Date.now(),
                    },
                });
            }
        };

        window.addEventListener('keydown', onKeyDown);
        return () => {
            window.removeEventListener('keydown', onKeyDown);
            try { (map as any).keyboard?.enable(); } catch (e) {}
        };
    }, [map, setBearing, setProps]);

    return null;
};

export default KeyboardControl;
