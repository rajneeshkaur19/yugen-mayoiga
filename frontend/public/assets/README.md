# Yūgen Mayoiga — Asset Library

All production artwork for Yūgen Mayoiga lives here.

## Art direction

Every image must follow one consistent direction:

- **Style:** Cinematic Japanese dark fantasy
- **Lighting:** Atmospheric — moonlight, lantern glow, dawn, fog
- **Palette:** Desaturated, muted. No neon, no pure white, no oversaturated color
- **Detail:** Rich environmental texture. Quiet, isolated, melancholic
- **Format:** WebP primary. PNG/JPG fallback where needed. AVIF for large hero images
- **Text:** No text, logos, watermarks or UI elements embedded in artwork
- **Consistency:** All images share the same visual language

---

## Directory structure

```
assets/
├── brand/              Logo, wordmark, favicon variants
├── backgrounds/        Full-screen atmospheric backgrounds (landing, auth)
├── environments/       Story reader scene artwork (forest, shrine, station…)
├── characters/         Character portrait artwork
├── story-covers/       Story library cover images
├── archive/            Memory archive decorative artwork and textures
├── endings/            Story conclusion full-screen artwork
├── textures/           Subtle overlay textures (paper, washi, dark grain)
└── icons/              Custom SVG icon set (supplement Lucide)
```

---

## Naming conventions

Use lowercase, hyphenated, descriptive names. No spaces or underscores.

| Category | Pattern | Example |
|----------|---------|---------|
| Background | `{context}-{subject}-{time/condition}.webp` | `landing-village-night.webp` |
| Environment | `reader-{location}-{condition}.webp` | `reader-forest-moonlight.webp` |
| Character | `character-portrait-{nn}.webp` | `character-portrait-01.webp` |
| Story cover | `story-cover-{title-slug}.webp` | `story-cover-forbidden-shrine.webp` |
| Ending | `ending-{title-slug}.webp` | `ending-dawn-at-the-shrine.webp` |
| Texture | `texture-{surface}-{variant}.webp` | `texture-archive-paper.webp` |

---

## Priority 1 — Essential assets (required before Phase 2)

| # | File | Folder | Purpose |
|---|------|--------|---------|
| 1 | `landing-village-night.webp` | `backgrounds/` | Landing page hero |
| 2 | `auth-misty-shrine.webp` | `backgrounds/` | Authentication background |
| 3 | `reader-forest-moonlight.webp` | `environments/` | Story reader primary scene |
| 4 | `reader-abandoned-village.webp` | `environments/` | Story reader alternate scene |
| 5 | `story-cover-silent-station.webp` | `story-covers/` | Default story cover |
| 6 | `story-cover-forbidden-shrine.webp` | `story-covers/` | Story cover variant |
| 7 | `character-portrait-01.webp` | `characters/` | Primary character portrait |
| 8 | `ending-dawn-at-the-shrine.webp` | `endings/` | Story ending artwork |

## Priority 2 — Supporting assets (required before Phase 3)

| # | File | Folder | Purpose |
|---|------|--------|---------|
| 9 | `texture-archive-paper.webp` | `textures/` | Memory archive overlay |
| 10 | `texture-timeline-washi.webp` | `textures/` | Timeline decorative |
| 11 | `texture-graph-dark.webp` | `textures/` | Story graph canvas background |
| 12 | `story-cover-lost-village.webp` | `story-covers/` | Library cover |
| 13 | `story-cover-winter-moon.webp` | `story-covers/` | Library cover |
| 14 | `character-portrait-02.webp` through `05.webp` | `characters/` | Secondary portraits |
| 15 | `ending-forgotten-path.webp` | `endings/` | Alternate ending artwork |

---

## Image specifications

| Use | Format | Dimensions | Max size |
|-----|--------|-----------|---------|
| Landing hero | WebP | 1920 × 1080px | 300 KB |
| Auth background | WebP | 1280 × 900px | 200 KB |
| Scene environment | WebP | 1600 × 900px | 250 KB |
| Story cover | WebP | 600 × 900px (2:3) | 100 KB |
| Character portrait | WebP | 400 × 600px (2:3) | 80 KB |
| Ending artwork | WebP | 1920 × 1080px | 300 KB |
| Texture overlay | WebP | 800 × 800px | 60 KB |

Provide responsive variants for hero images at widths: 640w, 1280w, 1920w.
Name them `{base-name}-640w.webp`, `{base-name}-1280w.webp`, etc.

---

## Tools for asset generation

Artwork is generated using the Gemini image generation API (available via the Gemini API plugin).
All generated artwork must be reviewed for art direction consistency before committing.

Do not use random internet images as production assets.
Do not embed text, logos or UI chrome in generated artwork.
