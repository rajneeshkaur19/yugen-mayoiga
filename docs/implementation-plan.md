# Yūgen Mayoiga — Week 5 Frontend Implementation Plan

**Milestone:** Week 5 — Frontend I  
**Design direction:** Cinematic Japanese dark fantasy  
**Status:** Phase 1 complete (design tokens, asset structure, roadmap)

---

## Repository audit summary

### Tech stack (confirmed)

| Layer | Technology |
|-------|-----------|
| Framework | React 19 + Vite 8 |
| Styling | Tailwind CSS v4 (`@tailwindcss/vite` plugin) |
| Routing | React Router v7 |
| Auth | JWT via `localStorage` (`yugen_access_token`) |
| API client | `frontend/src/api/client.js` — fetch-based, no external HTTP library |
| State | Local `useState` + Context (AuthContext, ToastContext) |
| TypeScript | Not used — plain `.jsx` / `.js` throughout |
| Backend proxy | Vite dev-server proxies `/api` → `http://127.0.0.1:8000` |

### Existing pages (all in `frontend/src/pages/`)

| File | Route | Status |
|------|-------|--------|
| `App.jsx` (HomePage inline) | `/` | Functional — minimal inline landing |
| `LoginPage.jsx` | `/login` | Functional — form + auth |
| `RegisterPage.jsx` | `/register` | Functional — form + auth |
| `ForgotPasswordPage.jsx` | `/forgot-password` | Functional |
| `ResetPasswordPage.jsx` | `/reset-password` | Functional |
| `DashboardPage.jsx` | `/dashboard` | Functional — story list |
| `CreateStoryPage.jsx` | `/stories/new` | Functional — template wizard |
| `StoryReaderPage.jsx` | `/stories/:storyId` | Functional — full reader with choices |

### Existing API contracts (do not change)

| Namespace | Endpoints used |
|-----------|---------------|
| `authApi` | `/auth/register`, `/auth/login`, `/auth/forgot-password`, `/auth/reset-password`, `/auth/me` |
| `storiesApi` | `/stories` (GET/POST), `/stories/:id` (GET/DELETE) |
| `scenesApi` | `/stories/:id/scenes` (GET/POST) |
| `choicesApi` | `/stories/:id/scenes/:sceneId/choices` (GET/POST) |
| `stateApi` | `/stories/:id/state`, `/stories/:id/yugen-meter` |
| `actionApi` | `/stories/:id/choice` (POST) |
| `charactersApi` | `/stories/:id/characters` (GET) |

### Runtime state fields (from `stateApi.get()`)

```
runtime.yugen_meter        number 0–100
runtime.turn_number        number
runtime.characters         object { [id]: { name, role, emotions } }
runtime.world_state        object { [key]: any }
runtime.relationships      object { [pair]: { [key]: value } }
runtime.current_scene_id   string | null
```

### Existing components

| File | Purpose |
|------|---------|
| `ProtectedRoute.jsx` | Auth guard wrapper |
| `AuthContext.jsx` | `user`, `loading`, `login()`, `register()`, `logout()` |
| `ToastContext.jsx` | `showToast(message, type)`, `dismissToast()` |

### Existing public assets (pre-existing folders — now reorganized)

```
frontend/public/assets/
  backgrounds/   (was populated — now part of new structure)
  icons/         (was populated — now part of new structure)
  images/        (old folder — to be migrated to named subfolders)
  sounds/        (preserve as-is)
```

---

## Phase 1 deliverables (complete)

| Deliverable | Files created |
|-------------|--------------|
| Design token system | `frontend/src/theme/tokens.js` |
| CSS custom properties + font loading | `frontend/src/theme/index.css` |
| Image loader utility | `frontend/src/utils/imageLoader.js` |
| Asset directory structure | `frontend/public/assets/{brand,backgrounds,environments,characters,story-covers,archive,endings,textures,icons}/` |
| Asset README | `frontend/public/assets/README.md` |
| `index.css` updated | Imports `tailwindcss` then `./theme/index.css` |
| `index.html` updated | Proper title, meta, Google Fonts preconnect |
| This roadmap | `docs/implementation-plan.md` |

---

## Screen-by-screen implementation plan

---

### SCREEN 01 — Landing Page

**Current state:** Inline `HomePage` component in `App.jsx`. Minimal text + two links. No artwork. No animation.

**Target:** Full-screen cinematic hero environment. Editorial headline. Atmospheric. Fog motion.

#### Files to create / modify

| Action | File |
|--------|------|
| Extract to new file | `src/pages/LandingPage.jsx` |
| Update route in | `src/App.jsx` |
| New component | `src/components/common/FogOverlay.jsx` |

#### Required design tokens
- `colors.bg.obsidian` as root background
- `colors.accent.crimsonMuted` for primary CTA button
- `colors.accent.gold` for eyebrow label and secondary links
- `typography.families.serif` for hero headline
- `transitions.scene` for fog animation

#### Required assets
- `backgrounds/landing-village-night.webp` (Priority 1 — block Phase 2)
- Responsive variants: `landing-village-night-640w.webp`, `-1280w.webp`, `-1920w.webp`

#### API integration
None. Unauthenticated page.

#### Responsive behavior
- **Desktop:** Full-screen hero, centered content overlay, horizontal CTA row
- **Tablet:** Same layout, slightly smaller headline
- **Mobile:** Single column, reduced hero height, stacked CTAs, re-composed image focal point

#### Loading / empty / error states
- Image loads with CSS fade-in (`opacity: 0 → 1`)
- If image fails to load: solid `bg-obsidian` background (design remains readable)

#### Animation
- Subtle CSS `@keyframes` fog drift on `FogOverlay` (opacity oscillation)
- Entrance: narrative text fades up 300ms after mount
- Respects `prefers-reduced-motion`

#### QA criteria
- [ ] Logo and nav readable over artwork at all screen sizes
- [ ] CTA buttons meet WCAG AA contrast against overlay
- [ ] No horizontal overflow on mobile
- [ ] Image loads with correct `loading="eager"` and `fetchpriority="high"`
- [ ] Fog animation pauses when `prefers-reduced-motion: reduce`

---

### SCREEN 02 — Authentication (Login / Register / Forgot / Reset)

**Current state:** Four functional pages. Centered card layout. Correct auth wiring. No artwork.

**Target:** Split-screen — atmospheric artwork left, focused form right (desktop). Full artwork with form overlay (mobile).

#### Files to modify

| Action | File |
|--------|------|
| Restyle | `src/pages/LoginPage.jsx` |
| Restyle | `src/pages/RegisterPage.jsx` |
| Restyle | `src/pages/ForgotPasswordPage.jsx` |
| Restyle | `src/pages/ResetPasswordPage.jsx` |
| New shared component | `src/components/common/AuthLayout.jsx` |
| New shared component | `src/components/common/FormField.jsx` |

> **Preservation rule:** Do not change any `onSubmit`, `useAuth`, `useToast`, or API call logic. Only change JSX structure and class names.

#### Required design tokens
- `components.input` for form field styling
- `components.button.primary` (crimson) for submit
- `components.button.secondary` for secondary links
- `colors.semantic.error*` for validation feedback

#### Required assets
- `backgrounds/auth-misty-shrine.webp` (Priority 1)

#### Responsive behavior
- **Desktop (≥768px):** 50/50 split. Artwork left, scrollable form right
- **Mobile:** Artwork as blurred full-screen background. Form centered over it with dark overlay

#### Loading / error states
- Submitting state: button text changes, spinner icon, `disabled`
- Field errors: red border + `role="alert"` message below field
- Toast for server errors (already wired via `useToast`)

#### QA criteria
- [ ] All four auth pages render correctly
- [ ] Form submission still works (login, register, forgot, reset)
- [ ] Email token-based reset still works end-to-end
- [ ] Error messages are accessible (`aria-describedby`)
- [ ] Split layout collapses cleanly to single column on mobile

---

### SCREEN 03 — Story Library (Dashboard)

**Current state:** `DashboardPage.jsx` — functional story list in a 3-column card grid.

**Target:** Editorial archive layout. Large story covers. Cinematic story cards. Welcome header. Begin-new-story CTA.

#### Files to modify

| Action | File |
|--------|------|
| Restyle | `src/pages/DashboardPage.jsx` |
| New component | `src/components/story/StoryCard.jsx` |
| New component | `src/components/common/AppShell.jsx` (shared nav/header) |

#### Required design tokens
- `components.card` for story card surfaces
- `colors.accent.gold` for genre labels and hover states
- `components.button.primary` (crimson) for "Begin a new story" CTA
- `components.button.destructive` for delete

#### Required assets
- `story-covers/story-cover-silent-station.webp`
- `story-covers/story-cover-forbidden-shrine.webp`
- Fallback: solid `bg-elevated` with title if no cover matched

#### API integration
- `storiesApi.list()` — unchanged. Maps `story.genre` to cover image lookup
- `storiesApi.delete(id)` — unchanged. Requires confirmation dialog (replace `window.confirm` with inline confirmation in Phase 2)

#### States
| State | Behavior |
|-------|---------|
| Loading | Skeleton card placeholders (3 × animated shimmer) |
| Empty | Full-width editorial empty state with CTA |
| Stories exist | Story card grid |
| Error | Inline error panel with retry |
| Search (Phase 2) | Filtered list with "no results" state |

#### Responsive behavior
- **Desktop:** 2–3 column story card grid
- **Tablet:** 2 column
- **Mobile:** Single column, full-width cards

#### QA criteria
- [ ] Story list loads correctly on mount
- [ ] Delete with confirmation still works
- [ ] Empty state CTA navigates to `/stories/new`
- [ ] Story cards link to `/stories/:id`
- [ ] Loading skeleton shown during fetch

---

### SCREEN 04 — Story Creation Wizard

**Current state:** `CreateStoryPage.jsx` — single-page form with all fields visible. Template story creation is functional.

**Target:** Multi-step immersive wizard. One decision per step. Progress indicator. Artwork background.

#### Files to modify / create

| Action | File |
|--------|------|
| Refactor | `src/pages/CreateStoryPage.jsx` |
| New component | `src/components/story/WizardStep.jsx` |
| New component | `src/components/story/WizardProgress.jsx` |

> **Preservation rule:** The template scene and choice creation logic (`templateScenes`, `scenesApi`, `choicesApi`) must be preserved exactly. Only the UI wrapper changes.

#### Wizard steps

| Step | Fields | Notes |
|------|--------|-------|
| 1 | `title`, `theme` | Premise & idea |
| 2 | `genre`, `tone` | Genre & atmosphere |
| 3 | `season`, `length` | World & scope |
| 4 | Review summary | Read-only, back/confirm |
| 5 | Submitting state | Full-screen "preparing your world" overlay |

#### Required design tokens
- `components.button.primary` for Next/Begin
- `components.button.secondary` for Back
- `components.input` for text fields
- `colors.accent.gold` for progress dots

#### Required assets
- `backgrounds/landing-village-night.webp` (reuse from landing) or a dedicated wizard background

#### API integration
- Unchanged. All `storiesApi`, `scenesApi`, `choicesApi`, `stateApi` calls preserved verbatim.

#### Responsive behavior
- **Desktop / Tablet:** Full-screen step layout with artwork half
- **Mobile:** Single column, artwork as subtle background tint

#### QA criteria
- [ ] All form fields still submit correctly
- [ ] Validation still fires (title required)
- [ ] Template scenes and choices created correctly
- [ ] Navigation to story reader after creation works
- [ ] Back navigation preserves entered data

---

### SCREEN 05 — Immersive Story Reader ⭐ (Most important screen)

**Current state:** `StoryReaderPage.jsx` — functional two-column layout. Correct choice handling, state display, haiku, ending detection. All API calls working.

**Target:** Three-region cinematic layout. Scene artwork. Dramatic narrative presentation. Character panel. Rich choice buttons.

#### Files to modify / create

| Action | File |
|--------|------|
| Restyle (preserve all logic) | `src/pages/StoryReaderPage.jsx` |
| New component | `src/components/story/SceneArtwork.jsx` |
| New component | `src/components/story/NarrativeText.jsx` |
| New component | `src/components/story/ChoiceList.jsx` |
| New component | `src/components/story/ChoiceButton.jsx` |
| New component | `src/components/character/CharacterPanel.jsx` |
| New component | `src/components/story/YugenMeter.jsx` |
| New component | `src/components/story/StoryControls.jsx` |

> **Preservation rule:** `followChoice()`, `loadStory()`, `loadChoices()`, `setRuntime()`, `setCurrentSceneId()` and all API calls must remain unchanged. Only presentation changes.

#### Layout regions

**Desktop (≥1024px):**
```
┌─────────────────────────────────────┬──────────────┐
│  Scene Artwork (full bleed, top)    │              │
│─────────────────────────────────────│  Character   │
│  Scene heading + mood               │  Panel       │
│  Narrative text                     │              │
│  Haiku (if present)                 │  Yūgen Meter │
│  Choice buttons                     │  World State │
└─────────────────────────────────────┴──────────────┘
```

**Mobile:**
- Artwork top (60vw tall)
- Narrative below
- Choices stacked vertically
- Character info in bottom drawer (toggle)

#### Required design tokens
- `components.choiceButton` for choice presentation
- `components.yugenMeter` for the meter bar
- `components.panel` for character + world-state panels
- `transitions.scene` for artwork crossfade between scenes
- `colors.accent.crimsonMuted` for active / busy choice state

#### Required assets
- `environments/reader-forest-moonlight.webp` (primary)
- `environments/reader-abandoned-village.webp` (alternate)
- `characters/character-portrait-01.webp` through `05.webp`
- Fallback: `bg-elevated` color block if environment image not found

#### API integration — exact preservation

| State | Source | Display |
|-------|--------|---------|
| `story.title`, `story.genre`, `story.season`, `story.tone` | `storiesApi.get()` | Header |
| `currentScene.content` | `scenesApi.list()` + state | Narrative body |
| `currentScene.haiku` | Same | Haiku block |
| `currentScene.location`, `currentScene.mood` | Same | Scene eyebrow |
| `currentScene.is_ending` | Same | Ending vs choices |
| `choices` | `choicesApi.list()` | Choice buttons |
| `runtime.yugen_meter` | `stateApi.get()` | Meter bar |
| `runtime.turn_number` | Same | Turn indicator |
| `runtime.characters` | Same | Character panel |
| `runtime.world_state` | Same | World state panel |
| `runtime.relationships` | Same | Relationship list |

#### Choice interaction states
- Default: idle border + muted text
- Hover: gold border + gold text + subtle bg
- Busy (submitting): all choices `disabled`, spinner shown, "The story is unfolding…" message
- Error: toast shown, choices re-enabled

#### Responsive behavior
- **Desktop:** Three-region side-by-side layout
- **Tablet:** Two-region (narrative + collapsed panel)
- **Mobile:** Single column; character panel as bottom sheet

#### QA criteria
- [ ] Choice submission still calls `actionApi.submitChoice()` with correct payload
- [ ] `setCurrentSceneId()` updates after choice
- [ ] Yūgen meter updates after each choice
- [ ] `busy` state correctly disables all choices during submission
- [ ] Ending state renders ending panel (not choices)
- [ ] Haiku block visible only when `currentScene.haiku` has content
- [ ] All character and world-state data from runtime displayed
- [ ] "No choices" state handled gracefully
- [ ] No scene state invented or fabricated

---

### SCREEN 06 — Character Intelligence

**Current state:** `src/pages/Character/` folder exists (empty).

**Target:** Character detail panel — portrait, name, description, emotional state, relationship indicators, interaction history.

#### Files to create

| File | Purpose |
|------|---------|
| `src/pages/Character/CharacterPage.jsx` | Page component |
| `src/components/character/CharacterPortrait.jsx` | Portrait + name + role |
| `src/components/character/EmotionDisplay.jsx` | Emotion key/value chips |
| `src/components/character/RelationshipList.jsx` | Relationship pairs |

#### New route (add to App.jsx)
```
/stories/:storyId/characters/:characterId
```

#### API integration
- `charactersApi.list(storyId)` — existing endpoint
- `runtime.characters[id]` — from `stateApi.get()` already loaded in reader

#### Data displayed (backend-sourced only)

| Field | Source | Fallback |
|-------|--------|---------|
| `character.name` | `runtime.characters` | "Unknown" |
| `character.role` | Same | "Character" |
| `character.emotions` | Same | Empty state message |
| Relationships | `runtime.relationships` | Empty state message |

> Never invent character traits or values not present in the API response.

#### Required assets
- `characters/character-portrait-01.webp` through `05.webp`
- Fallback: initials avatar in `bg-secondary`

#### QA criteria
- [ ] Only data from API is rendered
- [ ] Empty emotion/relationship states have appropriate message
- [ ] Portrait fallback renders correctly when image missing
- [ ] Page accessible from story reader panel

---

### SCREEN 07 — Memory Archive

**Current state:** `src/pages/Memories/` folder exists (empty).

**Target:** Chronological memory list with archival visual treatment. Subtle paper textures. Category filters.

#### Files to create

| File | Purpose |
|------|---------|
| `src/pages/Memories/MemoriesPage.jsx` | Page component |
| `src/components/memory/MemoryEntry.jsx` | Single memory card |
| `src/components/memory/MemoryFilter.jsx` | Category filter bar |

#### New route
```
/stories/:storyId/memories
```

#### API integration
- Backend endpoint to be confirmed. If not yet implemented, page renders with empty state and placeholder message: *"The archive is quiet. No memories have been recorded yet."*
- Do not fabricate memory entries.

#### Required assets
- `textures/texture-archive-paper.webp` (subtle overlay, `mix-blend-mode: overlay`, low opacity)

#### QA criteria
- [ ] Only actual stored memories displayed
- [ ] Empty state message shown when no memories exist
- [ ] No fabricated data rendered
- [ ] Texture overlay does not reduce text readability

---

### SCREEN 08 — Story Timeline

**Current state:** `src/pages/Timeline/` folder exists (empty).

**Target:** Vertical timeline of significant story events. Chapter markers, choice points, consequences.

#### Files to create

| File | Purpose |
|------|---------|
| `src/pages/Timeline/TimelinePage.jsx` | Page component |
| `src/components/story/TimelineEvent.jsx` | Single event node |

#### New route
```
/stories/:storyId/timeline
```

#### API integration
- Uses scene list (`scenesApi.list()`) as the backbone
- Uses runtime state for turn number and current position
- If a dedicated timeline endpoint is added in a future milestone, replace the data source here

#### QA criteria
- [ ] Timeline reflects actual visited scenes in order
- [ ] Current scene highlighted
- [ ] Empty / single-scene state handled
- [ ] Responsive: vertical on mobile, potentially horizontal on wide desktop

---

### SCREEN 09 — Story Graph

**Current state:** `src/pages/StoryGraph/` folder exists (empty).

**Target:** Interactive graph canvas showing branching narrative structure. Scene nodes, branch connections, current path highlighted.

#### Files to create

| File | Purpose |
|------|---------|
| `src/pages/StoryGraph/StoryGraphPage.jsx` | Page component |
| `src/components/graph/GraphCanvas.jsx` | Graph rendering wrapper |
| `src/components/graph/SceneNode.jsx` | Individual node |

#### New route
```
/stories/:storyId/graph
```

#### Dependency note
The spec recommends React Flow. Before adding it, verify:
1. No existing graph library is already installed
2. The package is compatible with React 19

If React Flow is added: install via pnpm, add to `package.json`. Do not modify `vite.config.js` for it.

#### API integration
- `scenesApi.list()` for all scenes
- `choicesApi.list()` per scene for edges (or a dedicated graph endpoint if added)
- `stateApi.get()` for `current_scene_id`

> Do not invent branches or outcomes. Graph only shows what the backend provides.

#### QA criteria
- [ ] Graph reflects actual story structure
- [ ] Current scene node is visually highlighted
- [ ] Clicking a node shows scene details
- [ ] Graph canvas does not overflow on small screens

---

### SCREEN 10 — World State

**Current state:** `src/pages/StoryWorld/` folder exists (empty).

**Target:** Current story world overview — environment, variables, character and relationship state.

#### Files to create

| File | Purpose |
|------|---------|
| `src/pages/StoryWorld/WorldStatePage.jsx` | Page component |
| `src/components/world/WorldStatePanel.jsx` | World variable display |
| `src/components/world/RelationshipGrid.jsx` | Relationship indicators |

#### New route
```
/stories/:storyId/world
```

#### API integration
- `stateApi.get()` — `runtime.world_state` and `runtime.relationships`
- Display only fields present in the response. No fabrication.

#### QA criteria
- [ ] Only fields from API displayed
- [ ] Empty world state has clear message
- [ ] Relationship display is readable and labelled

---

### SCREEN 11 — Ending Experience

**Current state:** Ending is handled inline in `StoryReaderPage.jsx` as a simple `<div>` block.

**Target:** Full-screen cinematic ending. Emotional weight. Ending title, narrative conclusion, outcome summary, replay/return actions.

#### Files to create / modify

| Action | File |
|--------|------|
| New component | `src/components/story/EndingScreen.jsx` |
| Update ending detection | `src/pages/StoryReaderPage.jsx` |

No new route. The ending renders in-page when `currentScene.is_ending === true`, replacing the choice list with a full-screen overlay.

#### Required assets
- `endings/ending-dawn-at-the-shrine.webp`
- `endings/ending-forgotten-path.webp`
- Fallback: `bg-obsidian` with centered content

#### QA criteria
- [ ] Ending state detected correctly from `currentScene.is_ending`
- [ ] Ending screen shown only when backend confirms the scene is an ending
- [ ] Return to library link works
- [ ] Ending artwork loads lazily (not needed until scene reached)

---

### SCREEN 12 — Settings and Language

**Current state:** No settings page exists.

**Target:** Interface language selector (EN / JA / HI / PA) and story language preference. Persisted independently.

#### Files to create

| File | Purpose |
|------|---------|
| `src/pages/SettingsPage.jsx` | Settings page |
| `src/context/LocaleContext.jsx` | Interface language state |
| `src/utils/locale.js` | Language persistence helpers |

#### New route
```
/settings
```

#### Language architecture

**Interface language** (UI strings):
- Stored in `localStorage` as `yugen_ui_lang`
- Defaults to `en`
- Applied via `lang` attribute on `<html>` element
- Controls font stack via `:lang()` CSS selectors already defined in `theme/index.css`
- Centralized string file: `src/i18n/{en,ja,hi,pa}.js` (Phase 2 — strings not hardcoded yet)

**Story language** (narrative content language):
- Stored in story creation form state
- Passed to backend at story creation time only
- Does not affect UI strings
- Changing story language after creation is not supported (would require backend changes)

> Actual AI multilingual story generation is not a Week 5 feature. The language selector is infrastructure only.

#### QA criteria
- [ ] UI language selection persists across page reloads
- [ ] Story language selection visible in story creation wizard
- [ ] Changing UI language does not reset story state
- [ ] Changing story language in wizard does not silently change story content
- [ ] `<html lang="">` attribute updates correctly

---

## Shared component plan

These components are used across multiple screens. Build them before the screens that depend on them.

| Component | Used by | Priority |
|-----------|---------|---------|
| `AppShell.jsx` | Dashboard, Reader, all intelligence screens | Phase 2 — first |
| `AuthLayout.jsx` | All auth pages | Phase 2 — first |
| `FormField.jsx` | Auth pages, Settings | Phase 2 |
| `StoryCard.jsx` | Dashboard | Phase 2 |
| `ChoiceButton.jsx` | Story reader | Phase 2 |
| `YugenMeter.jsx` | Story reader, World state | Phase 2 |
| `CharacterPanel.jsx` | Story reader, Character page | Phase 2 |
| `SceneArtwork.jsx` | Story reader | Phase 2 |
| `NarrativeText.jsx` | Story reader | Phase 2 |
| `EndingScreen.jsx` | Story reader | Phase 2 |
| `FogOverlay.jsx` | Landing page | Phase 2 |
| `TimelineEvent.jsx` | Timeline page | Phase 3 |
| `MemoryEntry.jsx` | Memories page | Phase 3 |
| `GraphCanvas.jsx` | Story graph page | Phase 3 |

---

## Implementation phases

### Phase 1 — Foundation (complete)
- [x] Design token system (`tokens.js`, `theme/index.css`)
- [x] Asset directory structure
- [x] Image loader utility
- [x] `index.css` imports theme
- [x] `index.html` metadata + font preconnect
- [x] This roadmap

### Phase 2 — Core screens (next)
Implement in this order to maintain a working app throughout:

1. **AppShell** — shared navigation/header component
2. **AuthLayout** — shared auth page wrapper
3. **Screen 01** — Landing page (extract from `App.jsx`, add artwork, fog)
4. **Screen 02** — Auth pages (restyle with artwork, preserve all logic)
5. **Screen 03** — Story library / Dashboard (editorial layout, story cards)
6. **Screen 04** — Story creation wizard (multi-step, preserve template logic)
7. **Screen 05** — Story reader (cinematic layout, all existing logic preserved)
8. **Screen 11** — Ending experience (EndingScreen component, inline in reader)

After Phase 2: full regression test of all API flows.

### Phase 3 — Intelligence layer
9.  **Screen 06** — Character intelligence page
10. **Screen 07** — Memory archive
11. **Screen 08** — Story timeline
12. **Screen 09** — Story graph (React Flow evaluation first)
13. **Screen 10** — World state page
14. **Screen 12** — Settings and language

### Phase 4 — Polish and QA
- Responsive audit (mobile, tablet, desktop)
- Reduced-motion audit
- Accessibility audit (focus management, ARIA, contrast)
- Loading / empty / error state review for all screens
- Image optimization pass (WebP, responsive srcSet)
- Performance review (Lighthouse, bundle size)
- README and milestone documentation update

---

## QA acceptance checklist

### Visual identity
- [ ] All screens share the design system (tokens, typography, spacing)
- [ ] No hardcoded hex values in component files
- [ ] Cinematic atmosphere established on landing and reader
- [ ] No generic SaaS dashboard appearance

### Functionality
- [ ] Authentication flows work end-to-end (login, register, forgot, reset)
- [ ] Story creation with template still works
- [ ] Choice submission and scene progression works
- [ ] Yūgen meter updates correctly
- [ ] Story deletion with confirmation works
- [ ] Protected routes redirect unauthenticated users

### Responsive
- [ ] Desktop (≥1280px): full multi-column layouts
- [ ] Tablet (768px–1279px): adapted two-column layouts
- [ ] Mobile (≤767px): single column, no horizontal overflow

### Accessibility
- [ ] All interactive elements keyboard-navigable
- [ ] Focus rings visible
- [ ] `aria-live` on dynamic content (toast, choice processing)
- [ ] `alt` text on all images
- [ ] `prefers-reduced-motion` respected for all animations

### Performance
- [ ] Hero images use `loading="eager"` and `fetchpriority="high"`
- [ ] Below-fold images use `loading="lazy"`
- [ ] All images served as WebP
- [ ] `vite build` completes without errors or warnings

### Code hygiene
- [ ] No `.bak` files committed
- [ ] No `console.log` in production code
- [ ] No hardcoded API URLs (all via `client.js`)
- [ ] No invented API endpoints
- [ ] No fabricated story/character/memory data
- [ ] `src/pages/StoryReaderPage.jsx.before-runtime-panel.bak` removed before final commit

---

## Asset checklist (Priority 1 — required before Phase 2 screens)

| Asset | Path | Status |
|-------|------|--------|
| Landing hero | `backgrounds/landing-village-night.webp` | ⬜ Pending |
| Auth background | `backgrounds/auth-misty-shrine.webp` | ⬜ Pending |
| Reader primary | `environments/reader-forest-moonlight.webp` | ⬜ Pending |
| Reader alternate | `environments/reader-abandoned-village.webp` | ⬜ Pending |
| Story cover default | `story-covers/story-cover-silent-station.webp` | ⬜ Pending |
| Story cover alt | `story-covers/story-cover-forbidden-shrine.webp` | ⬜ Pending |
| Character portrait 01 | `characters/character-portrait-01.webp` | ⬜ Pending |
| Ending artwork | `endings/ending-dawn-at-the-shrine.webp` | ⬜ Pending |

> Generate artwork using the Gemini API image generation capability, following the art direction in `frontend/public/assets/README.md`.

---

## Decisions deferred to Phase 2 review

| Decision | Context |
|----------|---------|
| React Flow for story graph | Confirm React 19 compatibility before installing |
| `window.confirm` replacement | Replace with inline confirmation dialog in Dashboard |
| Stagger animation library | Use CSS only for Phase 2; evaluate Framer Motion only if CSS is insufficient |
| i18n library | Evaluate `react-i18next` vs a minimal custom hook for Phase 3 |
| Backend memory endpoint | Confirm `/stories/:id/memories` exists before building Screen 07 |
| Backend graph endpoint | Confirm whether a dedicated graph API endpoint will be added |

---

*Last updated: Week 5 — Phase 1 complete.*  
*Next review: After Phase 2 screens are implemented.*
