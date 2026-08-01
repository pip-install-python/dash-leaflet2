"""Home — the introduction video.

Its own module rather than part of `example.py` because the two are different
things: `example.py` is the live Leaflet 2 demo that proves the library
renders, and this is a recording that explains it. `.. exec::` imports each by
module path, so keeping them separate lets the markdown place them
independently.

Embedded from `youtube-nocookie.com`, which is YouTube's no-tracking-cookie
origin. It plays identically and does not set the visitor-tracking cookies the
standard embed does — worth having on a documentation site that otherwise
counts nothing about its readers beyond an anonymised page view.
"""

import dash_mantine_components as dmc
from dash import html

VIDEO_ID = "Wlmw98JrJZI"
VIDEO_URL = f"https://youtu.be/{VIDEO_ID}"
VIDEO_TITLE = "Dash Leaflet 2.0: Drone Tracking, Image Overlays & Map Packages in Python"

component = dmc.Stack(
    [
        html.Div(
            html.Iframe(
                src=(
                    f"https://www.youtube-nocookie.com/embed/{VIDEO_ID}"
                    "?rel=0&modestbranding=1"
                ),
                title=VIDEO_TITLE,
                # `fullscreen` belongs in `allow`, not in a separate
                # `allowFullScreen` prop: Dash 4.4.1's html.Iframe does not
                # expose the legacy attribute at all, and without the
                # permission the player still renders a fullscreen button that
                # silently does nothing — which reads as a broken embed rather
                # than a missing feature.
                allow=(
                    "accelerometer; autoplay; clipboard-write; encrypted-media; "
                    "fullscreen; gyroscope; picture-in-picture; web-share"
                ),
                # Nothing here needs the container's origin, and the iframe is
                # third-party — so it gets only what a video player requires.
                referrerPolicy="strict-origin-when-cross-origin",
                style={
                    "position": "absolute",
                    "top": 0,
                    "left": 0,
                    "width": "100%",
                    "height": "100%",
                    "border": "0",
                    "borderRadius": "8px",
                },
            ),
            # The padding-bottom trick rather than `aspect-ratio`: it holds the
            # 16:9 box open from first paint in every engine, so the page does
            # not reflow when the iframe finally loads. (Dash 4.4.1's
            # html.Iframe exposes no `loading` prop, so the embed is eager and
            # the reserved box is what keeps the layout stable regardless.)
            style={
                "position": "relative",
                "paddingBottom": "56.25%",
                "height": 0,
                "overflow": "hidden",
                "borderRadius": "8px",
            },
        ),
        # A real link as well as the player. An agent reading /llms.txt never
        # sees the iframe, and neither does anyone whose browser blocks the
        # embed — both should still be able to reach the video.
        dmc.Anchor(
            f"Watch on YouTube: {VIDEO_TITLE}",
            href=VIDEO_URL,
            target="_blank",
            size="sm",
            c="dimmed",
        ),
    ],
    gap="xs",
)
