# macOS launcher visual and interaction QA

final result: passed

Scope: native macOS development MVP, selected amber direction with the user's later request for a denser grid and optional system theme. This is not a claim of pixel-identical mock reproduction or cross-platform release readiness.

Source: `../assets/designs/xlaunch/amber-classic-selected.png` (relative to launcher: `../assets`); actual repository path `assets/designs/xlaunch/amber-classic-selected.png`, 1448×1086.
Implementation evidence: local deliverables `outputs/XLaunch-macOS-compact.png` and `outputs/XLaunch-macOS-system.png`, captured using QQuickWindow::grabWindow on macOS 26.6.2. Native logical viewport approximately 1352×798, 2× device density (2704×1596). No CSS viewport applies. The source is 4:3 and the host viewport is wider; compared regional composition rather than stretching either artifact. Source and implementation were opened together in the same comparison tool call.

## Iterations

1. P1: category column expanded to fill the screen, clipping the grid. Fixed explicit minimum/maximum category width. Recapture confirmed all app columns visible.
2. P2: partially visible bottom row at rest. Fixed cell height to an integral number of rows. Subsequent user request increased density to five rows and responsive 140px target column width; latest amber capture shows 35 complete app items.
3. Qt native control style rejected custom backgrounds. Set Basic style with explicit QML styling; subsequent capture and runtime no longer show those style warnings.

## Fidelity surfaces

- Typography: platform font, readable light labels in amber and dark labels in the system palette. Labels elide/wrap in compact cells. Native content replaces concept app names intentionally.
- Layout: left categories, top search, central grid and keyboard footer preserved. Higher density is requested, not accidental drift. Region details were readable in full-resolution tool inspection.
- Colors: warm blurred amber raster with translucent controls preserved. System palette is intentionally a separate mode, verified visually in light appearance; dark-mode switching and Linux theme integration remain validation gaps.
- Images: generated clean wallpaper rather than a screenshot used as UI; actual macOS application icons supplied by AppKit. Wallpaper differs subtly from the source; residual P3 art-direction polish.
- Copy: unavailable AI/system-command integrations are stated honestly. No fake Agent execution. Missing decorative search glyph is P3 polish, not a missing interaction.

## Interaction evidence

Native accessibility actions verified query `计算器` produced one result, clicking it started the macOS Calculator process, an unmatched query showed zero results, and the Network category filtered to network apps. Filter/bounds self-test passed; last timed CTest run was 0.23s. Menu/theme code compiled and both visual modes rendered. Keyboard shortcuts are implemented but not exhaustively exercised by UI automation.

No actionable P0/P1/P2 layout issue remains for this MVP. Remaining product work: global shortcut, full desktop-specific theme integration, live inventory refresh, Agent/system providers and signed self-contained distribution. These are documented feature limits, not implied completed features.
