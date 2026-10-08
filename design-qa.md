# Design QA

- Source visual truth: `C:\Users\impurity\.codex\generated_images\01a0ebe3-3212-7ca1-8a0e-b5102238a489\exec-9b6d75c3-e509-447c-9ba6-9a6ca371258c.png`
- Browser-rendered implementation: `C:\Users\impurity\gold_dashboard\implementation-final.png`
- Side-by-side comparison: `C:\Users\impurity\gold_dashboard\design-comparison.jpg`
- Intended design viewport: 1440 × 1024 CSS px
- Available browser QA viewport: 1280 × 720 CSS px at devicePixelRatio 2
- Source pixels: 1488 × 1059
- Implementation capture pixels: 1280 × 720
- Density normalization: both views were proportionally contained in equal 720 × 512 comparison frames; no stretching or crop was used.
- State: personalized assessment, step 2, maximum drawdown 20%, default continuous recommendation.

## Full-view comparison evidence

The implementation preserves the selected visual target's four defining elements: fixed institutional navigation, a five-step assessment workspace, a live right-side allocation result, and the dark mountain/data-flow environment. The hierarchy remains assessment first, result second. Gold and Bitcoin imagery, Q4-M0 attribution, continuous weights, and the single primary progression action are present.

## Focused-region evidence

The full-view comparison is sufficiently legible for the key regions at the available viewport: stepper and slider, asset icons and weights, allocation ring, model/AI role statement, and sidebar navigation. No separate crop was required. At the shorter 720px browser height, lower supporting content continues below the fold; the primary assessment action remains visible.

## Required fidelity surfaces

- Fonts and typography: Chinese serif display headings and system Chinese sans-serif UI text preserve the reference hierarchy. The implementation uses robust local fallbacks instead of a network font dependency. Line height and weights remain readable over imagery.
- Spacing and layout rhythm: three-zone structure, major proportions, borders, glass surfaces, and step spacing match the reference closely. The layout remains scrollable at shorter viewport heights.
- Colors and visual tokens: midnight navy, charcoal, metallic gold, muted copper, off-white, and emerald status accents match the source direction with adequate panel contrast.
- Image quality and asset fidelity: the mountain/data-flow background and both asset emblems are generated raster assets, not CSS drawings or placeholders. They render sharply and maintain the selected art direction.
- Copy and content: core Chinese labels, Q4-M0 method attribution, model-versus-AI responsibility, personalized weights, benchmark explanation, and research disclaimer are present and accurate.

## Comparison history

### Iteration 1 findings

- P1: background and asset emblems failed to render through Streamlit media URLs.
- P1: the browser's remembered collapsed state moved the sidebar off-screen.
- P2: the engine heading wrapped awkwardly at medium desktop width.
- P0 functional: values from earlier questionnaire steps reset after their widgets left the page.

### Fixes applied

- Embedded the generated raster assets as optimized data URIs while retaining project copies.
- Forced the desktop sidebar into its intended visible position and raised its stacking order.
- Added a medium-width typography adjustment for the engine heading.
- Separated persistent answer state from temporary widget state and verified cross-step retention.

### Post-fix evidence

- Final browser capture shows the background, gold bars, Bitcoin emblem, navigation, assessment, and live result rendered together.
- Changing maximum drawdown from 20% to 30% moved the continuous recommendation from 63.6%/36.4% to 59.2%/40.8%.
- Advancing through later steps retained the 30% drawdown answer and the resulting 67.2 risk score.
- “我的配置方案” navigation opened the amount-conversion view with consistent weights.
- Offline AI explanation returned a guarded explanation without modifying weights.
- Browser console errors checked: 0.
- Automated tests: 6 passed.

## Findings

No actionable P0, P1, or P2 issues remain.

## Follow-up polish

- P3: on a 1280 × 720 screen, secondary metrics and the AI explanation button require vertical scrolling; this is accepted because the selected reference targets a taller 1440 × 1024 canvas and the primary action remains visible.

final result: passed
