import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { endingsApi } from '../../api/client'

export default function EndingScreen({
  story,
  currentScene,
  runtime,
  scenes = [],
  onOpenTimeline,
  onOpenGraph,
  onOpenMemories,
}) {
  const [matchingEnding, setMatchingEnding] = useState(null)

  useEffect(() => {
    if (!story?.id) return
    let active = true

    async function fetchEndings() {
      try {
        const list = await endingsApi.list(story.id)
        if (active && Array.isArray(list) && list.length > 0) {
          // If any ending definition matches or exists for this story
          setMatchingEnding(list[0])
        }
      } catch {
        // Fallback silently to scene-derived ending presentation
      }
    }

    fetchEndings()
    return () => {
      active = false
    }
  }, [story?.id])

  const turn = runtime?.turn_number ?? 1
  const yugen = runtime?.yugen_meter ?? 50
  const charCount = Object.keys(runtime?.characters || {}).length
  const sceneCount = scenes.length || 1

  const endingTitle = matchingEnding?.name || currentScene?.location || 'The Final Threshold'
  const sealText = matchingEnding?.seal_text || '終幕'

  return (
    <div className="relative min-h-[85vh] w-full flex flex-col justify-center items-center py-10 px-4 sm:px-6 animate-in fade-in duration-1000">
      {/* ─────────────────────────────────────────────────────────────
          1. FULL-WIDTH CINEMATIC HERO CARD
      ───────────────────────────────────────────────────────────── */}
      <div className="relative w-full max-w-4xl overflow-hidden rounded-3xl border border-[#A33B42]/30 bg-[#101317]/90 backdrop-blur-2xl shadow-[0_0_80px_rgba(0,0,0,0.9)]">
        {/* Background Artwork Layer with Deep Contrast & Vignette */}
        <div className="absolute inset-0 z-0 overflow-hidden">
          <img
            src="/assets/backgrounds/mayoiga-estate-night.png"
            alt="The Final Scene"
            className="h-full w-full object-cover object-center filter brightness-85 contrast-125 scale-105"
          />
          {/* Layered Cinematic Vignettes */}
          <div className="absolute inset-0 bg-gradient-to-t from-[#101317] via-[#101317]/50 to-transparent" />
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,transparent_35%,#101317_90%)]" />
        </div>

        {/* Top Gold Horizon Hairline */}
        <div className="relative z-10 h-px w-full bg-gradient-to-r from-transparent via-[#C4AD88]/50 to-transparent" />

        {/* ─────────────────────────────────────────────────────────────
            2. HERO FINALE CONTENT
        ───────────────────────────────────────────────────────────── */}
        <div className="relative z-10 px-6 sm:px-12 py-10 sm:py-14 text-center space-y-8">
          {/* Japanese Ending Seal Emblem */}
          <div className="flex flex-col items-center gap-3">
            <div className="relative">
              <div className="flex h-16 w-16 items-center justify-center rounded-full border border-[#C4AD88]/50 bg-[#1B2228]/90 text-[#C4AD88] shadow-[0_0_30px_rgba(196,173,136,0.2)]">
                <span className="font-cinematic text-2xl" style={{ fontFamily: 'serif' }}>
                  {sealText.length <= 2 ? sealText : '終'}
                </span>
              </div>
              {/* Outer pulsing ring */}
              <div className="absolute inset-0 rounded-full border border-[#C4AD88]/20 scale-125" />
            </div>

            <div className="space-y-1">
              <p className="font-mono text-[10px] uppercase tracking-[0.35em] text-[#C4AD88]">
                THE CHRONICLE CONCLUDES · {sealText}
              </p>
              <span className="text-xs font-mono text-[#858A8D] tracking-wider block">
                {story?.title}
              </span>
            </div>
          </div>

          {/* Grand Ending Title */}
          <div className="space-y-2">
            <h1 className="font-cinematic text-4xl sm:text-6xl font-semibold tracking-wide text-[#F1EEE8] leading-tight">
              {endingTitle}
            </h1>
            <p className="font-cinematic text-lg sm:text-xl italic text-[#C4AD88]/90">
              — {currentScene?.location || 'Where the Mist Settles'} —
            </p>
          </div>

          {/* Divider */}
          <div className="flex items-center justify-center gap-3 max-w-xs mx-auto">
            <div className="h-px flex-1 bg-gradient-to-r from-transparent to-[#C4AD88]/30" />
            <span className="text-[#C4AD88] text-xs">✦</span>
            <div className="h-px flex-1 bg-gradient-to-l from-transparent to-[#C4AD88]/30" />
          </div>

          {/* ─────────────────────────────────────────────────────────────
              3. FINAL NARRATIVE TEXT
          ───────────────────────────────────────────────────────────── */}
          <div className="max-w-2xl mx-auto space-y-6 text-left sm:text-center">
            {currentScene?.content && (
              <div className="font-cinematic text-lg sm:text-xl leading-relaxed text-[#D7DCE0] whitespace-pre-line space-y-4">
                {currentScene.content}
              </div>
            )}

            {/* Traditional Haiku Reflection if present */}
            {currentScene?.haiku && (
              <div className="mx-auto max-w-lg rounded-xl border border-[#C4AD88]/30 bg-[#171C21]/70 p-5 backdrop-blur-sm">
                <span className="block text-[9px] uppercase font-mono tracking-widest text-[#C4AD88] mb-1.5 text-center">
                  俳句 · Final Poetic Reflection
                </span>
                <p className="font-cinematic italic text-base sm:text-lg text-[#C4AD88] leading-relaxed whitespace-pre-line text-center">
                  {currentScene.haiku}
                </p>
              </div>
            )}
          </div>

          {/* ─────────────────────────────────────────────────────────────
              4. COMPACT JOURNEY RECORD (MINIMAL & TASTEFUL)
          ───────────────────────────────────────────────────────────── */}
          <div className="pt-2">
            <div className="mx-auto max-w-2xl rounded-2xl border border-white/[0.08] bg-[#14191E]/70 backdrop-blur-md p-4 sm:p-5">
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-center divide-y sm:divide-y-0 sm:divide-x divide-white/[0.06]">
                <div className="pt-2 sm:pt-0">
                  <span className="text-[9px] font-mono uppercase tracking-widest text-[#858A8D] block">
                    Duration
                  </span>
                  <span className="font-cinematic text-xl font-semibold text-[#F1EEE8] mt-0.5 block">
                    Turn {turn}
                  </span>
                </div>

                <div className="pt-2 sm:pt-0">
                  <span className="text-[9px] font-mono uppercase tracking-widest text-[#858A8D] block">
                    Final Yūgen
                  </span>
                  <span className="font-cinematic text-xl font-semibold text-[#C4AD88] mt-0.5 block">
                    {yugen}%
                  </span>
                </div>

                <div className="pt-2 sm:pt-0">
                  <span className="text-[9px] font-mono uppercase tracking-widest text-[#858A8D] block">
                    Anchors
                  </span>
                  <span className="font-cinematic text-xl font-semibold text-[#D7DCE0] mt-0.5 block">
                    {sceneCount} Scenes
                  </span>
                </div>

                <div className="pt-2 sm:pt-0">
                  <span className="text-[9px] font-mono uppercase tracking-widest text-[#858A8D] block">
                    Inhabitants
                  </span>
                  <span className="font-cinematic text-xl font-semibold text-[#F1EEE8] mt-0.5 block">
                    {charCount > 0 ? `${charCount} Souls` : 'Solitary'}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* ─────────────────────────────────────────────────────────────
              5. PLAYER ACTIONS
          ───────────────────────────────────────────────────────────── */}
          <div className="pt-4 flex flex-col sm:flex-row items-center justify-center gap-3.5 max-w-xl mx-auto flex-wrap">
            {/* 1. Return to Archive (Primary CTA) */}
            <Link
              to="/dashboard"
              className="w-full sm:w-auto rounded-xl border border-[#A33B42] bg-[#A33B42] px-8 py-3.5 text-xs font-semibold uppercase tracking-wider text-[#F1EEE8] hover:bg-[#702B34] transition shadow-[0_0_25px_rgba(163,59,66,0.4)] text-center"
            >
              Return to Archive
            </Link>

            {/* 2. View Chronicle Timeline */}
            {onOpenTimeline && (
              <button
                type="button"
                onClick={onOpenTimeline}
                className="w-full sm:w-auto rounded-xl border border-white/15 bg-[#1B2228] px-6 py-3.5 text-xs font-medium uppercase tracking-wider text-[#D7DCE0] hover:border-[#C4AD88]/50 hover:text-white transition"
              >
                View Chronicle
              </button>
            )}

            {/* 3. View Threads of Fate Graph */}
            {onOpenGraph && (
              <button
                type="button"
                onClick={onOpenGraph}
                className="w-full sm:w-auto rounded-xl border border-white/15 bg-[#1B2228] px-6 py-3.5 text-xs font-medium uppercase tracking-wider text-[#D7DCE0] hover:border-[#C4AD88]/50 hover:text-white transition"
              >
                Fate Map
              </button>
            )}

            {/* 4. Memories Vault */}
            {onOpenMemories && (
              <button
                type="button"
                onClick={onOpenMemories}
                className="w-full sm:w-auto rounded-xl border border-white/15 bg-[#1B2228] px-6 py-3.5 text-xs font-medium uppercase tracking-wider text-[#D7DCE0] hover:border-[#C4AD88]/50 hover:text-white transition"
              >
                Memories Vault
              </button>
            )}

            {/* 5. Begin New Story */}
            <Link
              to="/create"
              className="w-full sm:w-auto rounded-xl border border-[#C4AD88]/40 bg-transparent px-6 py-3.5 text-xs font-medium uppercase tracking-wider text-[#C4AD88] hover:bg-[#C4AD88]/10 hover:border-[#C4AD88] transition text-center"
            >
              Begin New Journey →
            </Link>
          </div>

          <p className="text-[10px] font-mono text-[#5A5F63] pt-2">
            Every choice left something behind. The manuscript is sealed.
          </p>
        </div>
      </div>
    </div>
  )
}
