import { useMemo, useState } from 'react'

// ─── Filter tab definitions ────────────────────────────────────────────────────
const FILTERS = [
  { id: 'all',     label: 'All',      kanji: '全' },
  { id: 'visited', label: 'Visited',  kanji: '過' },
  { id: 'current', label: 'Now',      kanji: '今' },
  { id: 'ending',  label: 'Endings',  kanji: '末' },
]

// ─── Determine scene status relative to current position ──────────────────────
function getSceneStatus(scene, currentIndex, sceneIndex) {
  if (scene.is_ending) return 'ending'
  if (currentIndex === -1) return sceneIndex === 0 ? 'current' : 'upcoming'
  if (sceneIndex < currentIndex) return 'visited'
  if (sceneIndex === currentIndex) return 'current'
  return 'upcoming'
}

// ─── Visual tier config per status ────────────────────────────────────────────
const STATUS_CONFIG = {
  visited: {
    dot: 'border border-[#C4AD88] bg-[#C4AD88]',
    innerDot: 'h-1.5 w-1.5 rounded-full bg-[#101317]',
    card: 'border-white/10 bg-[#101317]/80',
    cardHover: 'hover:border-[#C4AD88]/30 hover:bg-[#101317]',
    chapterLabel: 'text-[#C4AD88]',
    badge: null,
    titleColor: 'text-[#D7DCE0]',
    lineColor: 'bg-[#C4AD88]/30',
    opacity: '',
  },
  current: {
    dot: 'border-2 border-[#A33B42] bg-[#14191E] shadow-[0_0_14px_rgba(163,59,66,0.6)]',
    innerDot: null, // pulsing ring rendered separately
    card: 'border-[#A33B42]/50 bg-[#1B2228] shadow-[0_0_28px_rgba(163,59,66,0.12)]',
    cardHover: '',
    chapterLabel: 'text-[#A33B42]',
    badge: { label: 'Current Scene', cls: 'border border-[#A33B42]/60 bg-[#A33B42]/20 text-[#F1EEE8]' },
    titleColor: 'text-[#F1EEE8]',
    lineColor: 'bg-[#A33B42]/50',
    opacity: '',
  },
  ending: {
    dot: 'border border-[#C4AD88] bg-gradient-to-b from-[#C4AD88] to-[#A33B42]',
    innerDot: 'h-1.5 w-1.5 rounded-full bg-[#101317]',
    card: 'border-[#C4AD88]/30 bg-[#1B2228]/60',
    cardHover: 'hover:border-[#C4AD88]/50',
    chapterLabel: 'text-[#C4AD88]',
    badge: { label: '✦ Narrative Climax', cls: 'border border-[#C4AD88]/50 bg-[#C4AD88]/10 text-[#C4AD88]' },
    titleColor: 'text-[#F1EEE8]',
    lineColor: 'bg-[#C4AD88]/20',
    opacity: '',
  },
  upcoming: {
    dot: 'border border-white/15 bg-[#101317]',
    innerDot: null,
    card: 'border-white/5 bg-[#101317]/30',
    cardHover: '',
    chapterLabel: 'text-[#5A5F63]',
    badge: { label: 'Uncharted', cls: 'border border-white/10 bg-transparent text-[#5A5F63]' },
    titleColor: 'text-[#5A5F63]',
    lineColor: 'bg-white/5',
    opacity: 'opacity-40',
  },
}

// ─── A single timeline scene card ─────────────────────────────────────────────
function SceneCard({ scene, status, index, isExpanded, onToggle, isLast }) {
  const cfg = STATUS_CONFIG[status]
  const isCurrent = status === 'current'
  const isVisited = status === 'visited'
  const isUpcoming = status === 'upcoming'

  // Truncate content for preview
  const preview = scene.content
    ? scene.content.slice(0, 140).trim() + (scene.content.length > 140 ? '…' : '')
    : null

  const canExpand = (isVisited || isCurrent) && (preview || scene.haiku || scene.mood)

  return (
    <div className={`relative flex gap-5 ${cfg.opacity}`}>
      {/* ─── Spine line + dot column ─── */}
      <div className="relative flex flex-col items-center w-5 shrink-0">
        {/* Dot */}
        <div
          className={`relative z-10 flex h-5 w-5 shrink-0 items-center justify-center rounded-full transition-all mt-1 ${cfg.dot}`}
        >
          {isCurrent ? (
            <span className="h-2 w-2 rounded-full bg-[#A33B42] animate-ping" />
          ) : cfg.innerDot ? (
            <span className={cfg.innerDot} />
          ) : null}
        </div>

        {/* Connector line to next node */}
        {!isLast && (
          <div
            className={`w-px flex-1 mt-1 ${cfg.lineColor} min-h-[2rem]`}
          />
        )}
      </div>

      {/* ─── Card ─── */}
      <div className="flex-1 pb-8">
        <div
          onClick={() => canExpand && onToggle(scene.id)}
          className={`rounded-xl border p-5 transition-all duration-200 ${cfg.card} ${cfg.cardHover} ${
            canExpand ? 'cursor-pointer' : ''
          }`}
        >
          {/* Top row: chapter label + status badge */}
          <div className="flex items-center justify-between mb-2 gap-2 flex-wrap">
            <span className={`font-mono text-[10px] uppercase tracking-[0.2em] font-semibold ${cfg.chapterLabel}`}>
              Scene {String(scene.scene_number).padStart(2, '0')}
            </span>

            <div className="flex items-center gap-2">
              {cfg.badge && (
                <span className={`rounded-full border px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${cfg.badge.cls}`}>
                  {cfg.badge.label}
                </span>
              )}
              {isVisited && (
                <span className="rounded-full border border-[#C4AD88]/30 px-2.5 py-0.5 text-[10px] text-[#C4AD88] uppercase tracking-wide">
                  Traversed
                </span>
              )}
            </div>
          </div>

          {/* Scene title / location */}
          <h3 className={`font-cinematic text-xl font-semibold leading-snug tracking-wide ${cfg.titleColor}`}>
            {scene.location}
          </h3>

          {/* Mood tag */}
          {scene.mood && !isUpcoming && (
            <p className="mt-1 text-[11px] font-mono text-[#858A8D] uppercase tracking-wider">
              Atmosphere · {scene.mood}
            </p>
          )}

          {/* Expandable content — narration preview + haiku */}
          {canExpand && isExpanded && (
            <div className="mt-4 space-y-3 border-t border-white/[0.07] pt-4">
              {preview && (
                <p className="font-cinematic text-sm leading-relaxed text-[#D7DCE0]/80 whitespace-pre-line">
                  {preview}
                </p>
              )}
              {scene.haiku && (
                <div className="border-l-2 border-[#C4AD88]/40 pl-4">
                  <span className="block text-[9px] font-mono uppercase tracking-widest text-[#C4AD88] mb-1">
                    俳句 · Haiku
                  </span>
                  <p className="font-cinematic text-sm italic text-[#C4AD88]/80 leading-relaxed whitespace-pre-line">
                    {scene.haiku}
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Expand affordance */}
          {canExpand && (
            <div className="mt-3 flex items-center gap-1 text-[10px] text-[#858A8D]">
              <span className="transition-transform duration-200" style={{ display: 'inline-block', transform: isExpanded ? 'rotate(180deg)' : 'rotate(0deg)' }}>
                ▾
              </span>
              <span>{isExpanded ? 'Collapse' : 'Read excerpt'}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ─── Main component ────────────────────────────────────────────────────────────
export default function TimelineModal({ isOpen, onClose, scenes = [], currentSceneId, turnNumber = 1, storyTitle = '' }) {
  const [activeFilter, setActiveFilter] = useState('all')
  const [expandedId, setExpandedId] = useState(null)

  if (!isOpen) return null

  // Sort scenes by scene_number ascending (defensive — API should already return them ordered)
  const sortedScenes = useMemo(
    () => [...scenes].sort((a, b) => a.scene_number - b.scene_number),
    [scenes]
  )

  // Find current scene index
  const currentIndex = useMemo(
    () => sortedScenes.findIndex((s) => String(s.id) === String(currentSceneId)),
    [sortedScenes, currentSceneId]
  )

  // Assign status to every scene
  const annotated = useMemo(
    () =>
      sortedScenes.map((scene, idx) => ({
        scene,
        status: getSceneStatus(scene, currentIndex, idx),
      })),
    [sortedScenes, currentIndex]
  )

  // Apply active filter
  const filtered = useMemo(() => {
    if (activeFilter === 'all') return annotated
    if (activeFilter === 'visited') return annotated.filter((s) => s.status === 'visited')
    if (activeFilter === 'current') return annotated.filter((s) => s.status === 'current')
    if (activeFilter === 'ending') return annotated.filter((s) => s.scene.is_ending)
    return annotated
  }, [annotated, activeFilter])

  // Counts for filter badges
  const counts = useMemo(() => ({
    all: annotated.length,
    visited: annotated.filter((s) => s.status === 'visited').length,
    current: annotated.filter((s) => s.status === 'current').length,
    ending: annotated.filter((s) => s.scene.is_ending).length,
  }), [annotated])

  function toggleExpand(id) {
    setExpandedId((prev) => (prev === id ? null : id))
  }

  // ── Stat pills (above timeline) ──────────────────────────────────────
  const visitedCount = counts.visited
  const totalCount = counts.all
  const progressPct = totalCount > 0 ? Math.round(((visitedCount + counts.current) / totalCount) * 100) : 0

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6">
      {/* Backdrop */}
      <div
        onClick={onClose}
        className="fixed inset-0 bg-black/85 backdrop-blur-md"
      />

      {/* Panel */}
      <div className="relative z-10 flex flex-col w-full max-w-2xl max-h-[90vh] rounded-2xl overflow-hidden border border-white/[0.08] bg-[#101317] text-[#F1EEE8] shadow-2xl">

        {/* ── Decorative top bar accent ── */}
        <div className="h-px w-full bg-gradient-to-r from-transparent via-[#C4AD88]/40 to-transparent" />

        {/* ─────────────── HEADER ─────────────── */}
        <div className="shrink-0 px-6 pt-6 pb-5 bg-[#101317] border-b border-white/[0.07]">
          <div className="flex items-start justify-between gap-4">
            {/* Left: Kanji seal + title */}
            <div className="flex items-start gap-4">
              {/* Kanji emblem */}
              <div className="relative shrink-0">
                <div className="flex h-12 w-12 items-center justify-center rounded-full border border-[#C4AD88]/30 bg-[#1B2228] shadow-inner">
                  <span
                    className="font-cinematic text-xl text-[#C4AD88]"
                    style={{ fontFamily: 'serif' }}
                    title="Chronicle"
                  >
                    記
                  </span>
                </div>
                {/* Subtle outer ring */}
                <div className="absolute inset-0 rounded-full border border-[#C4AD88]/10 scale-110" />
              </div>

              <div>
                <div className="flex items-center gap-2 mb-0.5">
                  <p className="text-[9px] font-mono uppercase tracking-[0.3em] text-[#858A8D]">
                    THE CHRONICLE · 年代記
                  </p>
                  {storyTitle && (
                    <>
                      <span className="text-[9px] text-[#5A5F63]">·</span>
                      <span className="text-[9px] font-mono text-[#C4AD88] tracking-wider truncate max-w-[180px] sm:max-w-xs">
                        {storyTitle}
                      </span>
                    </>
                  )}
                </div>
                <h2 className="font-cinematic text-2xl font-semibold tracking-wide text-[#F1EEE8]">
                  The Chronicle
                </h2>
                <p className="mt-0.5 text-[11px] text-[#858A8D] font-mono">
                  A record of everything that has unfolded
                </p>
              </div>
            </div>

            {/* Right: close */}
            <button
              onClick={onClose}
              className="shrink-0 rounded-lg border border-white/10 p-2 text-[#858A8D] hover:border-white/20 hover:text-[#F1EEE8] transition"
              aria-label="Close chronicle"
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* ── Progress bar + stats ── */}
          <div className="mt-5 space-y-2.5">
            {/* Arc progress bar */}
            <div className="flex items-center justify-between text-[10px] font-mono text-[#858A8D]">
              <span>Journey Progress</span>
              <span className="text-[#C4AD88]">{progressPct}%</span>
            </div>
            <div className="h-1 w-full rounded-full bg-white/[0.06] overflow-hidden">
              <div
                className="h-full rounded-full bg-gradient-to-r from-[#A33B42] to-[#C4AD88] transition-all duration-700"
                style={{ width: `${progressPct}%` }}
              />
            </div>

            {/* Inline stat pills */}
            <div className="flex items-center gap-3 pt-1 flex-wrap">
              <div className="flex items-center gap-1.5 text-[10px] text-[#858A8D]">
                <span className="h-1.5 w-1.5 rounded-full bg-[#C4AD88]" />
                <span>{visitedCount} traversed</span>
              </div>
              <div className="flex items-center gap-1.5 text-[10px] text-[#858A8D]">
                <span className="h-1.5 w-1.5 rounded-full bg-[#A33B42] animate-pulse" />
                <span>Turn {turnNumber}</span>
              </div>
              <div className="flex items-center gap-1.5 text-[10px] text-[#858A8D]">
                <span className="h-1.5 w-1.5 rounded-full bg-white/20" />
                <span>{totalCount} narrative anchors</span>
              </div>
              {counts.ending > 0 && (
                <div className="flex items-center gap-1.5 text-[10px] text-[#C4AD88]">
                  <span>✦</span>
                  <span>{counts.ending} climax{counts.ending !== 1 ? 'es' : ''}</span>
                </div>
              )}
            </div>
          </div>

          {/* ── Filter tabs ── */}
          <div className="mt-4 flex items-center gap-2 flex-wrap">
            {FILTERS.map((f) => {
              const count = counts[f.id]
              const isActive = activeFilter === f.id
              return (
                <button
                  key={f.id}
                  onClick={() => setActiveFilter(f.id)}
                  className={`flex items-center gap-1.5 rounded-full border px-3 py-1 text-[11px] font-semibold transition-all ${
                    isActive
                      ? 'border-[#C4AD88]/60 bg-[#C4AD88]/10 text-[#C4AD88]'
                      : 'border-white/10 bg-transparent text-[#858A8D] hover:border-white/20 hover:text-[#D7DCE0]'
                  }`}
                >
                  <span
                    className="font-cinematic text-xs"
                    style={{ fontFamily: 'serif' }}
                  >
                    {f.kanji}
                  </span>
                  <span>{f.label}</span>
                  {count > 0 && (
                    <span className={`rounded-full px-1.5 text-[9px] font-mono ${isActive ? 'bg-[#C4AD88]/20 text-[#C4AD88]' : 'bg-white/[0.07] text-[#5A5F63]'}`}>
                      {count}
                    </span>
                  )}
                </button>
              )
            })}
          </div>
        </div>

        {/* ─────────────── TIMELINE BODY ─────────────── */}
        <div className="flex-1 overflow-y-auto px-6 py-6 overscroll-contain">
          {filtered.length === 0 ? (
            /* ── Empty state ── */
            <div className="flex flex-col items-center justify-center py-16 text-center space-y-5">
              {/* Torii glyph */}
              <div className="relative">
                <div className="flex h-16 w-16 items-center justify-center rounded-full border border-white/10 bg-[#1B2228]">
                  <span
                    className="font-cinematic text-3xl text-[#858A8D]/60"
                    style={{ fontFamily: 'serif' }}
                  >
                    鳥
                  </span>
                </div>
                <div className="absolute inset-0 rounded-full border border-white/5 scale-125" />
              </div>

              <div className="space-y-1.5 max-w-xs">
                <p className="font-cinematic text-lg text-[#D7DCE0]">
                  {activeFilter === 'all'
                    ? 'The chronicle is yet unwritten.'
                    : 'No entries match this filter.'}
                </p>
                <p className="text-xs text-[#5A5F63] font-mono leading-relaxed">
                  {activeFilter === 'all'
                    ? 'Your journey will leave its first mark here.'
                    : 'Try viewing all scenes instead.'}
                </p>
              </div>

              {activeFilter !== 'all' && (
                <button
                  onClick={() => setActiveFilter('all')}
                  className="rounded-full border border-white/10 px-4 py-1.5 text-xs text-[#858A8D] hover:border-white/20 hover:text-[#F1EEE8] transition"
                >
                  Show all scenes
                </button>
              )}
            </div>
          ) : (
            /* ── Timeline entries ── */
            <div className="relative">
              {filtered.map(({ scene, status }, idx) => (
                <SceneCard
                  key={scene.id}
                  scene={scene}
                  status={status}
                  index={idx}
                  isExpanded={expandedId === scene.id}
                  onToggle={toggleExpand}
                  isLast={idx === filtered.length - 1}
                />
              ))}
            </div>
          )}
        </div>

        {/* ─────────────── FOOTER ─────────────── */}
        <div className="shrink-0 flex items-center justify-between border-t border-white/[0.07] bg-[#101317] px-6 py-4">
          <div className="flex items-center gap-2 text-[10px] text-[#5A5F63] font-mono">
            <span
              className="font-cinematic text-sm text-[#C4AD88]/40"
              style={{ fontFamily: 'serif' }}
            >
              記
            </span>
            <span>
              {filtered.length} of {totalCount} scene{totalCount !== 1 ? 's' : ''}
            </span>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg border border-white/10 bg-[#1B2228] px-5 py-2 text-xs text-[#F1EEE8] hover:border-white/20 transition"
          >
            Close Chronicle
          </button>
        </div>
      </div>
    </div>
  )
}
