/**
 * Yūgen Mayoiga — Image Loader Utility
 *
 * Provides a consistent, optimized image-loading contract for the entire frontend.
 *
 * Key features:
 *  - Centralized asset path resolution (no scattered string literals)
 *  - WebP/AVIF with PNG/JPG fallback via <picture> element helpers
 *  - Lazy vs eager loading strategy
 *  - Responsive srcSet generation
 *  - Descriptive alt text enforcement at the call site
 *  - No network requests to arbitrary external URLs
 *
 * Usage:
 *   import { assetPath, SceneImage, CoverImage } from '../utils/imageLoader'
 */

// ─────────────────────────────────────────────
// ASSET PATH HELPERS
// ─────────────────────────────────────────────

/**
 * Base path to all public assets.
 * All asset helpers build on this so a future CDN migration
 * only requires changing this one constant.
 */
const ASSET_ROOT = '/assets'

/**
 * Returns the full public URL for a named asset.
 * @param {string} folder  - subfolder under /assets/
 * @param {string} filename - filename with extension
 * @returns {string}
 *
 * @example assetPath('backgrounds', 'landing-village-night.webp')
 */
export function assetPath(folder, filename) {
  return `${ASSET_ROOT}/${folder}/${filename}`
}

/**
 * Pre-defined path builders for each asset category.
 * Import the one you need instead of calling assetPath directly.
 */
export const assets = {
  brand:       (f) => assetPath('brand', f),
  background:  (f) => assetPath('backgrounds', f),
  environment: (f) => assetPath('environments', f),
  character:   (f) => assetPath('characters', f),
  cover:       (f) => assetPath('story-covers', f),
  archive:     (f) => assetPath('archive', f),
  ending:      (f) => assetPath('endings', f),
  texture:     (f) => assetPath('textures', f),
  icon:        (f) => assetPath('icons', f),
}

// ─────────────────────────────────────────────
// KNOWN ASSET REGISTRY
// Update this object as artwork is finalized.
// Components import named constants rather than
// building paths themselves.
// ─────────────────────────────────────────────

export const knownAssets = {
  // Priority 1 — Essential
  backgrounds: {
    landingHero:         assets.background('landing-village-night.webp'),
    auth:                assets.background('auth-misty-shrine.webp'),
    readerPrimary:       assets.environment('reader-forest-moonlight.webp'),
    readerAlternate:     assets.environment('reader-abandoned-village.webp'),
  },
  characters: {
    portrait01:          assets.character('character-portrait-01.webp'),
    portrait02:          assets.character('character-portrait-02.webp'),
    portrait03:          assets.character('character-portrait-03.webp'),
    portrait04:          assets.character('character-portrait-04.webp'),
    portrait05:          assets.character('character-portrait-05.webp'),
  },
  covers: {
    forbiddenShrine:     assets.cover('story-cover-forbidden-shrine.webp'),
    silentStation:       assets.cover('story-cover-silent-station.webp'),
    lostVillage:         assets.cover('story-cover-lost-village.webp'),
    winterMoon:          assets.cover('story-cover-winter-moon.webp'),
    autumnAsh:           assets.cover('story-cover-autumn-ash.webp'),
  },
  endings: {
    dawnAtShrine:        assets.ending('ending-dawn-at-the-shrine.webp'),
    forgottenPath:       assets.ending('ending-forgotten-path.webp'),
    vanishingMist:       assets.ending('ending-vanishing-mist.webp'),
  },

  // Priority 2 — Supporting
  textures: {
    archivePaper:        assets.texture('texture-archive-paper.webp'),
    timelineWashi:       assets.texture('texture-timeline-washi.webp'),
    graphBackground:     assets.texture('texture-graph-dark.webp'),
  },
}

// ─────────────────────────────────────────────
// REACT COMPONENT HELPERS
// Pure functions that return props objects so
// they work with any element (<img>, <picture>, etc.)
// ─────────────────────────────────────────────

/**
 * Returns img props for a simple optimized image.
 *
 * @param {object} opts
 * @param {string}  opts.src         - primary image path (WebP or AVIF preferred)
 * @param {string}  opts.alt         - required descriptive alt text
 * @param {'lazy'|'eager'} [opts.loading='lazy']
 * @param {'async'|'sync'|'auto'} [opts.decoding='async']
 * @param {string}  [opts.sizes]     - responsive sizes hint
 * @param {string}  [opts.className]
 * @param {object}  [opts.style]
 */
export function imgProps({
  src,
  alt,
  loading = 'lazy',
  decoding = 'async',
  sizes,
  className,
  style,
}) {
  const props = { src, alt, loading, decoding }
  if (sizes)     props.sizes = sizes
  if (className) props.className = className
  if (style)     props.style = style
  return props
}

/**
 * Returns the srcs needed to build a <picture> element with WebP primary
 * and a raster fallback. The fallback is derived by replacing the extension.
 *
 * @param {string} webpPath   - path to the .webp version
 * @param {string} [fallbackExt='jpg']
 * @returns {{ webp: string, fallback: string }}
 */
export function pictureSources(webpPath, fallbackExt = 'jpg') {
  const fallback = webpPath.replace(/\.webp$/i, `.${fallbackExt}`)
  return { webp: webpPath, fallback }
}

/**
 * Generates a srcSet string for responsive images.
 *
 * @param {string} basePath   - e.g. '/assets/backgrounds/landing-village-night'
 * @param {string} ext        - e.g. 'webp'
 * @param {number[]} widths   - e.g. [640, 1280, 1920]
 * @returns {string}          - '...path-640w.webp 640w, ...path-1280w.webp 1280w'
 *
 * NOTE: Responsive variants must be generated offline (e.g. with sharp or squoosh)
 * and stored alongside the base asset with the matching naming convention.
 */
export function responsiveSrcSet(basePath, ext, widths) {
  return widths
    .map((w) => `${basePath}-${w}w.${ext} ${w}w`)
    .join(', ')
}

// ─────────────────────────────────────────────
// LOADING STRATEGY GUIDE
// ─────────────────────────────────────────────
/**
 * Recommended loading strategies by context:
 *
 * EAGER (loading="eager") — above the fold, largest contentful paint candidate
 *   - Landing hero background
 *   - Auth page background
 *   - Story reader scene image (current scene)
 *
 * LAZY (loading="lazy") — below the fold or not immediately visible
 *   - Story library covers (all except the first visible row)
 *   - Character portraits in side panels
 *   - Ending artwork (not shown until narrative completes)
 *   - Archive/memory textures
 *
 * DECODE ASYNC — always use decoding="async" for large raster images
 *   to avoid blocking the main thread.
 */
