---
name: brand-guidelines
description: Provides Anthropic's official brand color and typography tokens (hex values, font families, sizes, accent order) as reference data to apply when styling an artifact. Use it when brand colors or style guidelines, visual formatting, or company design standards apply. This skill supplies the values; apply them using your target tool's styling API (e.g. python-pptx, CSS, Markdown).
license: Complete terms in LICENSE.txt
---

# Anthropic Brand Styling

## Overview

This skill provides Anthropic's official brand identity tokens — colors, typography, and accent rules — as a reference data sheet. It does not ship any code or perform styling itself; use the values below with the styling API of whatever tool you are producing the artifact in.

**Keywords**: branding, corporate identity, visual identity, post-processing, styling, brand colors, typography, Anthropic brand, visual formatting, visual design

## Scope

- The **color hex values, font families, and accent order** are universal — they transfer to any medium (slides, web, Markdown, print).
- The **point sizes and python-pptx references** below are `.pptx`-oriented; they describe how the tokens map onto PowerPoint artifacts.
- For **Markdown or HTML** output, only the token values transfer — point thresholds (24pt+) and python-pptx mechanics do not apply; translate them to the target medium's units (CSS `rem`/`px`, heading levels).

## Brand Guidelines

### Colors

**Main Colors:**

- Dark: `#141413` - Primary text and dark backgrounds
- Light: `#faf9f5` - Light backgrounds and text on dark
- Mid Gray: `#b0aea5` - Secondary elements
- Light Gray: `#e8e6dc` - Subtle backgrounds

**Accent Colors:**

- Orange: `#d97757` - Primary accent
- Blue: `#6a9bcc` - Secondary accent
- Green: `#788c5d` - Tertiary accent

### Typography

- **Headings**: Poppins (fallback: Arial)
- **Body Text**: Lora (fallback: Georgia)
- **Note**: Fonts should be pre-installed in the target environment for best results.

## Token Reference

### Font Assignment

- Headings (24pt+ in `.pptx`): Poppins
- Body text: Lora
- Fallbacks (use when Poppins/Lora are unavailable): Arial for headings, Georgia for body
- Preserve text hierarchy and existing formatting when applying these.

### Text Color Selection

Pick the text color that contrasts more with the background — a checkable rule:

- **Rigorous (preferred):** compute the WCAG contrast ratio of both Dark (`#141413`) and Light (`#faf9f5`) against the background and use whichever is higher. This always maximizes legibility.
- **Quick heuristic** (when a full contrast calc isn't available): light/pale background → Dark text; dark background → Light text.

(WCAG relative luminance `L = 0.2126·R + 0.7152·G + 0.0722·B` on linearized sRGB channels; contrast ratio = `(L_lighter + 0.05) / (L_darker + 0.05)`. A flat 0.5 luminance cutoff is *not* WCAG-accurate, so prefer the contrast-ratio comparison above.)

### Shape and Accent Colors

- Non-text shapes use the accent colors.
- Accent rotation order: Orange (`#d97757`) → Blue (`#6a9bcc`) → Green (`#788c5d`), then repeat.
- This rotation maintains visual interest while staying on-brand.

## Application Notes

### Fonts

- Use system-installed Poppins and Lora when available; otherwise use the Arial/Georgia fallbacks above.
- No font installation is bundled with this skill. For best results, pre-install Poppins and Lora in the target environment.

### Color

- Color values are given as hex for precise brand matching.
- In `.pptx` workflows, convert hex to `python-pptx`'s `RGBColor` (e.g. `RGBColor(0xD9, 0x77, 0x57)`); in CSS use the hex directly; in Markdown use whatever the renderer supports.
- The hex values are the source of truth — keep them identical across mediums to maintain color fidelity.
