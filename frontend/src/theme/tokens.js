/**
 * Yūgen Mayoiga — Design Token System
 * Cinematic Japanese dark fantasy
 *
 * This file is the single source of truth for all visual constants.
 * Import from this file; never hardcode hex values or spacing numbers in components.
 *
 * Compatible with Tailwind CSS v4 (used as JS values) and plain CSS custom properties.
 * See theme/index.css for the generated CSS custom-property layer.
 */

// ─────────────────────────────────────────────
// COLOR PALETTE
// ─────────────────────────────────────────────

export const colors = {
  // Primary backgrounds — layered surfaces
  bg: {
    obsidian:   '#101317',   // root background
    deep:       '#171C21',   // primary surface
    elevated:   '#1B2228',   // cards, panels raised one level
    secondary:  '#242C33',   // secondary panels, drawers
    border:     '#343C43',   // default border color
  },

  // Text hierarchy
  text: {
    primary:    '#F1EEE8',   // body, headings
    secondary:  '#B5B2AC',   // subtext, descriptions
    muted:      '#858A8D',   // labels, metadata
    inverse:    '#171713',   // text on light backgrounds (gold buttons)
  },

  // Brand accents
  accent: {
    crimsonMuted:  '#A33B42',  // primary CTA, important actions
    crimsonDeep:   '#702B34',  // hover / pressed crimson state
    gold:          '#C4AD88',  // selected states, highlights, the Yūgen meter
    goldLight:     '#D9C9A8',  // gold hover tint
    mist:          '#A9B6B9',  // mist, decorative secondary
    moonlight:     '#D7DCE0',  // moonlight, editorial highlights
  },

  // Semantic colors — intentionally desaturated/muted
  semantic: {
    successBg:   '#14251f',
    successText: '#6ee7b7',
    successBorder:'#2d6a52',

    warningBg:   '#241d10',
    warningText: '#fbbf24',
    warningBorder:'#6b4f10',

    errorBg:     '#2a191b',
    errorText:   '#fca5a5',
    errorBorder: '#7f2d35',

    infoBg:      '#141b25',
    infoText:    '#93c5fd',
    infoBorder:  '#2a3f5a',
  },

  // Utility overlays (use with rgba or CSS opacity)
  overlay: {
    dark10:  'rgba(0,0,0,0.10)',
    dark20:  'rgba(0,0,0,0.20)',
    dark40:  'rgba(0,0,0,0.40)',
    dark60:  'rgba(0,0,0,0.60)',
    dark80:  'rgba(0,0,0,0.80)',
    white05: 'rgba(255,255,255,0.05)',
    white10: 'rgba(255,255,255,0.10)',
    white15: 'rgba(255,255,255,0.15)',
  },
}

// ─────────────────────────────────────────────
// TYPOGRAPHY
// ─────────────────────────────────────────────

export const typography = {
  /**
   * Font families, ordered by cascade priority.
   *
   * Fonts to load via Google Fonts in index.html:
   *   Cormorant Garamond (400, 400i, 600, 600i)
   *   Inter (400, 500, 600)
   *   Noto Sans JP (400, 500)
   *   Noto Serif JP (400, 600)
   *   Noto Sans Devanagari (400, 500)
   *   Noto Sans Gurmukhi (400, 500)
   */
  families: {
    // Editorial serif — large headings, story titles, haiku, chapter names
    serif: '"Cormorant Garamond", "Noto Serif JP", Georgia, serif',

    // Interface sans-serif — labels, metadata, forms, navigation
    sans:  'Inter, "Noto Sans JP", "Noto Sans Devanagari", "Noto Sans Gurmukhi", system-ui, sans-serif',

    // Monospace — not currently used in UI; reserved for debug/admin
    mono:  '"JetBrains Mono", "Fira Code", ui-monospace, monospace',
  },

  // Script-aware stacks per locale
  locale: {
    en: {
      ui:        'Inter, system-ui, sans-serif',
      editorial: '"Cormorant Garamond", Georgia, serif',
    },
    ja: {
      ui:        '"Noto Sans JP", Inter, system-ui, sans-serif',
      editorial: '"Noto Serif JP", "Cormorant Garamond", Georgia, serif',
    },
    hi: {
      ui:        '"Noto Sans Devanagari", Inter, system-ui, sans-serif',
      editorial: '"Noto Sans Devanagari", "Cormorant Garamond", Georgia, serif',
    },
    pa: {
      ui:        '"Noto Sans Gurmukhi", Inter, system-ui, sans-serif',
      editorial: '"Noto Sans Gurmukhi", "Cormorant Garamond", Georgia, serif',
    },
  },

  // Type scale (rem, assumes 16px base)
  scale: {
    xs:   '0.75rem',    // 12px — metadata, fine print
    sm:   '0.8125rem',  // 13px — labels, captions
    base: '0.9375rem',  // 15px — body narrative
    md:   '1rem',       // 16px — standard body
    lg:   '1.125rem',   // 18px — slightly larger body
    xl:   '1.25rem',    // 20px — section headings
    '2xl':'1.5rem',     // 24px — panel headings
    '3xl':'1.875rem',   // 30px — page headings
    '4xl':'2.25rem',    // 36px — story titles
    '5xl':'3rem',       // 48px — hero headings
    '6xl':'3.75rem',    // 60px — editorial hero
    '7xl':'4.5rem',     // 72px — landing hero
  },

  // Semantic roles mapped to scale keys
  role: {
    heroTitle:    '7xl',
    pageHeading:  '5xl',
    sectionHead:  '3xl',
    panelHead:    '2xl',
    narrative:    'base',
    interfaceLabel: 'sm',
    metadata:     'xs',
  },

  // Line heights
  leading: {
    tight:    '1.25',
    snug:     '1.375',
    normal:   '1.5',
    relaxed:  '1.75',  // narrative body text
    loose:    '2.0',
  },

  // Letter spacing — editorial tracking
  tracking: {
    tight:    '-0.02em',
    normal:   '0em',
    wide:     '0.05em',
    wider:    '0.1em',
    widest:   '0.3em',   // eyebrow labels
    ultrawide:'0.4em',   // decorative labels
  },

  // Font weights
  weight: {
    normal:   '400',
    medium:   '500',
    semibold: '600',
  },
}

// ─────────────────────────────────────────────
// SPACING SCALE (4px grid)
// ─────────────────────────────────────────────

export const spacing = {
  '0':   '0px',
  px:    '1px',
  '0.5': '2px',
  '1':   '4px',    // micro
  '1.5': '6px',
  '2':   '8px',    // compact
  '3':   '12px',   // small component
  '4':   '16px',   // standard
  '5':   '20px',
  '6':   '24px',   // section
  '7':   '28px',
  '8':   '32px',   // large
  '10':  '40px',
  '12':  '48px',   // major separation
  '14':  '56px',
  '16':  '64px',   // hero / editorial
  '20':  '80px',
  '24':  '96px',
  '32':  '128px',
}

// ─────────────────────────────────────────────
// BORDER RADIUS
// ─────────────────────────────────────────────

export const radius = {
  none:  '0px',
  sm:    '4px',
  md:    '6px',    // small controls: tags, badges, inputs
  lg:    '10px',   // standard panels, cards
  xl:    '14px',   // large surfaces
  '2xl': '16px',   // hero media, full-bleed images
  full:  '9999px', // pills, meters
}

// ─────────────────────────────────────────────
// SHADOWS
// ─────────────────────────────────────────────

export const shadows = {
  // Layered cinematic shadows — dark, not harsh
  sm:   '0 1px 3px rgba(0,0,0,0.4)',
  md:   '0 4px 12px rgba(0,0,0,0.5)',
  lg:   '0 8px 24px rgba(0,0,0,0.6)',
  xl:   '0 16px 48px rgba(0,0,0,0.7)',
  glow: {
    gold:   '0 0 24px rgba(196,173,136,0.18)',   // gold ambient hint
    crimson:'0 0 24px rgba(163,59,66,0.22)',      // crimson ambient hint (use sparingly)
  },
}

// ─────────────────────────────────────────────
// BREAKPOINTS
// ─────────────────────────────────────────────

export const breakpoints = {
  xs:  '375px',   // compact mobile
  sm:  '640px',   // mobile landscape / small tablet
  md:  '768px',   // tablet portrait
  lg:  '1024px',  // tablet landscape / small desktop
  xl:  '1280px',  // standard desktop
  '2xl':'1536px', // wide desktop
}

// ─────────────────────────────────────────────
// TRANSITIONS & ANIMATION
// ─────────────────────────────────────────────

export const transitions = {
  // Duration tokens
  duration: {
    instant: '80ms',
    fast:    '150ms',
    normal:  '250ms',
    slow:    '400ms',
    scene:   '600ms',   // scene / artwork crossfades
    page:    '350ms',   // page-level transitions
  },

  // Easing curves
  easing: {
    standard: 'cubic-bezier(0.4, 0, 0.2, 1)',
    enter:    'cubic-bezier(0, 0, 0.2, 1)',
    exit:     'cubic-bezier(0.4, 0, 1, 1)',
    expressive:'cubic-bezier(0.34, 1.56, 0.64, 1)',  // slight overshoot for choice hover
  },

  // Named shorthand strings (value: "duration easing")
  default:   '250ms cubic-bezier(0.4, 0, 0.2, 1)',
  fast:      '150ms cubic-bezier(0.4, 0, 0.2, 1)',
  scene:     '600ms cubic-bezier(0, 0, 0.2, 1)',
  page:      '350ms cubic-bezier(0.4, 0, 0.2, 1)',
}

// ─────────────────────────────────────────────
// Z-INDEX SCALE
// ─────────────────────────────────────────────

export const zIndex = {
  base:      0,
  raised:    10,
  dropdown:  100,
  sticky:    200,
  overlay:   300,
  modal:     400,
  drawer:    500,
  toast:     600,
  tooltip:   700,
}

// ─────────────────────────────────────────────
// LAYOUT CONSTANTS
// ─────────────────────────────────────────────

export const layout = {
  maxWidth: {
    prose:    '65ch',    // comfortable reading width
    content:  '1024px',
    wide:     '1280px',
    full:     '100%',
  },
  // Named column templates for the story reader layout
  readerGrid: {
    desktop: 'minmax(0,1fr) 300px',   // narrative + intelligence panel
    wide:    'minmax(0,1fr) 340px',
  },
}

// ─────────────────────────────────────────────
// COMPONENT TOKENS (derived from above)
// Convenience aliases so components stay legible.
// ─────────────────────────────────────────────

export const components = {
  button: {
    primary: {
      bg:         colors.accent.crimsonMuted,
      bgHover:    colors.accent.crimsonDeep,
      text:       colors.text.primary,
      radius:     radius.lg,
      transition: transitions.fast,
    },
    secondary: {
      bg:         'transparent',
      border:     colors.bg.border,
      text:       colors.text.secondary,
      radius:     radius.lg,
      transition: transitions.fast,
    },
    gold: {
      bg:         colors.accent.gold,
      bgHover:    colors.accent.goldLight,
      text:       colors.text.inverse,
      radius:     radius.lg,
      transition: transitions.fast,
    },
    destructive: {
      border:     colors.semantic.errorBorder,
      bg:         colors.semantic.errorBg,
      text:       colors.semantic.errorText,
      radius:     radius.lg,
      transition: transitions.fast,
    },
  },

  input: {
    bg:           colors.bg.obsidian,
    border:       colors.bg.border,
    borderFocus:  colors.accent.gold,
    text:         colors.text.primary,
    placeholder:  colors.text.muted,
    radius:       radius.lg,
  },

  panel: {
    bg:           colors.bg.elevated,
    border:       colors.bg.border,
    radius:       radius.xl,
    padding:      spacing['5'],
    shadow:       shadows.md,
  },

  card: {
    bg:           colors.bg.elevated,
    bgHover:      colors.bg.secondary,
    border:       colors.bg.border,
    borderHover:  `${colors.accent.gold}40`,  // gold at 25% opacity
    radius:       radius.xl,
    shadow:       shadows.sm,
  },

  choiceButton: {
    bg:           colors.overlay.white05,
    bgHover:      colors.overlay.white10,
    border:       colors.overlay.white10,
    borderHover:  `${colors.accent.gold}66`,  // gold at 40% opacity
    text:         colors.text.secondary,
    textHover:    colors.accent.gold,
    radius:       radius.xl,
    transition:   transitions.default,
  },

  yugenMeter: {
    track:        colors.overlay.white10,
    fill:         colors.accent.gold,
    glow:         shadows.glow.gold,
  },

  toast: {
    success: {
      bg:     colors.semantic.successBg,
      border: colors.semantic.successBorder,
      text:   colors.semantic.successText,
    },
    error: {
      bg:     colors.semantic.errorBg,
      border: colors.semantic.errorBorder,
      text:   colors.semantic.errorText,
    },
    info: {
      bg:     colors.semantic.infoBg,
      border: colors.semantic.infoBorder,
      text:   colors.semantic.infoText,
    },
    warning: {
      bg:     colors.semantic.warningBg,
      border: colors.semantic.warningBorder,
      text:   colors.semantic.warningText,
    },
  },
}

// ─────────────────────────────────────────────
// DEFAULT EXPORT — unified token map
// ─────────────────────────────────────────────

const tokens = {
  colors,
  typography,
  spacing,
  radius,
  shadows,
  breakpoints,
  transitions,
  zIndex,
  layout,
  components,
}

export default tokens
