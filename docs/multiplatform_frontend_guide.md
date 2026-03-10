# RAVEN Multiplatform Frontend Guide

This guide defines the mobile-first UI constraints for web + Capacitor delivery.

## Local Codex Skill

Installed local skill path:

- `/Users/surfiniaburger/.codex/skills/raven-multiplatform-frontend/SKILL.md`

Included templates:

- `templates/responsive-shell.md`
- `templates/status-palette.md`
- `templates/timeline-card-pattern.md`

Restart Codex after skill changes so the new skill is picked up.

## Mobile-First Principles

1. Camera-first hierarchy: header, live stage, controls, intelligence, timeline.
2. Touch ergonomics: all action controls are minimum 44px height.
3. Safe area support: use `env(safe-area-inset-*)` around shell and sticky controls.
4. Operational readability: status chips and severity colors remain legible at `360x800`.
5. Preserve live protocol: keep websocket path and event payload parsing unchanged.

## Capacitor Readiness Notes

1. Avoid hard full-height traps (`h-screen`) that conflict with mobile browser/UI chrome.
2. Use `min-height: 100dvh` for root layout.
3. Keep bottom action dock tappable above gesture bars and notch areas.
4. Test with explicit backend URL when local proxy is unavailable in device context.

## WebSocket Configuration

- Default dev behavior: Vite proxy forwards `/ws` to backend local port.
- Device or split-host testing: set `VITE_WS_BASE_URL` to explicit ws/wss base.

Example:

```bash
VITE_WS_BASE_URL=ws://192.168.1.22:8000 npm run dev
```

## Troubleshooting

1. `ws proxy error ECONNREFUSED`: backend is down or wrong port target.
2. Session never connects on device: `VITE_WS_BASE_URL` points to localhost instead of LAN/remote host.
3. Camera black screen: verify browser/app camera permission and secure-context rules.
4. Mic stream missing: confirm microphone permission and no OS-level mute block.
5. Control dock overlaps system UI: verify safe-area inset CSS is active.

## Validation Matrix

Required viewport checks:

1. `360x800`
2. `390x844`
3. `768x1024`
4. `1280x800`

Required behavior checks:

1. Start/Stop session controls work.
2. Live camera feed remains visible and uncropped.
3. Timeline updates as events arrive.
4. Hazard severity and source evidence render clearly.
5. Connected/disconnected/error states are visually distinct.

## Demo Screenshot Guidance (Before/After)

Capture this pair for judge storytelling:

1. Before: old grid with dense flat panels and limited mobile hierarchy.
2. After: emergency command layout showing camera-first stage, sticky controls, status chips, and source evidence.

Use identical scenario prompts for both images for fair visual comparison.
