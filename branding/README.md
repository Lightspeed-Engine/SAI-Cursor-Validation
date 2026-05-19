# Branding guide — sAI Solvrighn AI (Cursor track)

## Hierarchy (do not mix levels on extension tiles)

| Level | Name | Use on this repo |
|-------|------|------------------|
| **Parent** | **Revolution Lifecycle** | README footer / “A Revolution Lifecycle project” only |
| **Ecosystem** | **Lightspeed Engine (LSE)** | Optional; not required on per-extension tiles |
| **Product line** | **sAI Solvrighn AI** | Primary voice: “Harness AI CLIs inside your IDE” |
| **This extension** | **Cursor Activity Correlator** / **SAI Cursor Validation** | VSIX name, OpenVSX listing, hooks kit |

## What you have today (assets in this folder)

| File | What it is |
|------|------------|
| [`sai-solvrighn-ai-banner.png`](sai-solvrighn-ai-banner.png) | Product line lockup (hexagon + gradient **sAI**, Solvrighn AI) |
| [`providers/sai-claude-card.png`](providers/sai-claude-card.png) | Per-runtime tile: play on **Claude** asterisk + “sAI Claude” |
| [`providers/sai-gemini-card.png`](providers/sai-gemini-card.png) | Per-runtime tile: play on **Gemini** sparkles + “sAI Gemini” |
| [`providers/sai-cursor-card.png`](providers/sai-cursor-card.png) | Per-runtime tile: **Cursor-style cube** (grayscale shadow faces, inspired-by) + teal **sAI** outfit + “sAI Cursor” |
| [`lse/bolt-and-gear-hero.png`](lse/bolt-and-gear-hero.png) | LSE mark: **gear + lightning bolt** (optional alternate, not the tile pattern) |
| [`revolution-lifecycle-logo.png`](revolution-lifecycle-logo.png) | RLC parent logo (orange circle + arrow) |
| [`lightspeed-engine-extensions.png`](lightspeed-engine-extensions.png) | Ecosystem poster (values: Transparency, Trust, …) |

**Cursor:** [`providers/sai-cursor-card.png`](providers/sai-cursor-card.png) — same tile pattern as Claude/Gemini; cube reads via **light/dark faces** (not multicolor); **teal** on border, **sAI**, and pill.

## Recommended Cursor extension icon

**Use the sAI Cursor provider card** (shadow cube + teal accents) for parity with Claude/Gemini tiles — crop the top icon region to 128×128 for VSIX.

| Approach | Use when |
|----------|----------|
| **sAI Cursor card** (recommended) | Marketplace tile + README; matches product line |
| **LSE bolt + gear** | Ecosystem docs, optional secondary mark |

**Implementation:** crop `providers/sai-cursor-card.png` (cube area) to:

- `cursor-activity/media/icon.png` — 128×128 (VS Code requirement)
- Optional: `media/icon.svg` for README

Then in `cursor-activity/package.json`:

```json
"icon": "media/icon.png"
```

## Naming (suggested)

| Surface | Suggested label |
|---------|-----------------|
| GitHub repo | **SAI Cursor Validation** |
| VSIX `displayName` | **sAI Cursor Activity** (under Solvrighn AI line) |
| OpenVSX short description | Governed live activity timeline for Cursor Agent |
| Publisher | `lightspeed-engine` (org) |

## README usage

- **Repo hero:** product line banner or ecosystem poster (your choice).
- **Extension:** LSE icon in marketplace; do not require full Lightspeed Engine poster on the tile.

## VSIX icons (done)

| File | Size | Use |
|------|------|-----|
| `cursor-activity/media/icon.png` | 128×128 | `package.json` `"icon"` (marketplace) |
| `cursor-activity/media/icon-256.png` | 256×256 | README / docs (optional) |

Crop source: top-center cube on `providers/sai-cursor-card.png`. Optional: refine cube in Figma for exact proportions.
