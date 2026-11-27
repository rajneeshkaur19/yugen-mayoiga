import { useMemo, useState } from 'react'

const TABS = [
  { id: 'atmosphere', label: 'Atmosphere', kanji: '気' },
  { id: 'conditions', label: 'World Variables', kanji: '態' },
  { id: 'locations',  label: 'Locations', kanji: '処' },
  { id: 'characters', label: 'Character Presence', kanji: '魂' },
]

// Yūgen density breakdown
function getYugenPerception(meter = 50) {
  if (meter >= 75) {
    return {
      tier: 'Manifest Realm · 幽顕',
      desc: 'The supernatural boundary is fractured. Hidden spirits and anomalies bleed into direct perception.',
      color: 'text-[#A33B42]',
      border: 'border-[#A33B42]/50',
      badgeBg: 'bg-[#A33B42]/20',
    }
  }
  if (meter >= 40) {
    return {
      tier: 'Veiled Threshold · 境目',
      desc: 'Reality is thin. Uncanny murmurs, shifting shadows, and memory fragments stir just out of sight.',
      color: 'text-[#C4AD88]',
      border: 'border-[#C4AD88]/50',
      badgeBg: 'bg-[#C4AD88]/15',
    }
  }
  return {
    tier: 'Mundane Silence · 静寂',
    desc: 'The veil remains undisturbed. Only subtle oddities and cold drafts hint at what lies underneath.',
    color: 'text-[#858A8D]',
    border: 'border-white/10',
    badgeBg: 'bg-white/5',
  }
}

function getWorldImage(location = '') {
  const loc = location.toLowerCase()
  if (loc.includes('shrine') || loc.includes('torii') || loc.includes('rain')) return '/assets/backgrounds/rain-soaked-shrine.png'
  if (loc.includes('village') || loc.includes('street') || loc.includes('crossing')) return '/assets/backgrounds/village-street-night.png'
  if (loc.includes('bamboo')) return '/assets/story-covers/cover-bamboo-forest.png'
  if (loc.includes('room') || loc.includes('chamber') || loc.includes('lantern') || loc.includes('letter')) return '/assets/backgrounds/midnight-engawa.png'
  return '/assets/backgrounds/mayoiga-estate-night.png'
}

export default function WorldStateModal({
  isOpen,
  onClose,
  runtime = {},
  currentScene = null,
  scenes = [],
  storyTitle = '',
}) {
  const [activeTab, setActiveTab] = useState('atmosphere')
  const [expandedLocationId, setExpandedLocationId] = useState(null)
  const [expandedVarKey, setExpandedVarKey] = useState(null)

  if (!isOpen) return null

  const worldState = runtime?.world_state || {}
  const yugenMeter = runtime?.yugen_meter ?? 50
  const turn = runtime?.turn_number ?? 1
  const characters = runtime?.characters || {}
  const relationships = runtime?.relationships || {}

  const perception = getYugenPerception(yugenMeter)

  // Current location fallback
  const currentLocationName = currentScene?.location || worldState?.location || 'Sanctuary Interior'
  const currentMood = currentScene?.mood || worldState?.mood || 'Subtle and mysterious'

  // Extract known variables from world_state
  const varEntries = Object.entries(worldState)

  // Character list array
  const characterList = Object.entries(characters).map(([id, char]) => ({
    id,
    name: char.name || 'Unknown Entity',
    role: char.role || 'Companion',
    emotions: char.emotions || { fear: 50, anxiety: 50, anger: 50, sadness: 50, happiness: 50, trust: 50 },
  }))

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6">
      {/* Backdrop */}
      <div
        onClick={onClose}
        className="fixed inset-0 bg-black/85 backdrop-blur-md"
      />

      {/* Main Modal Panel */}
      <div className="relative z-10 flex flex-col w-full max-w-3xl max-h-[90vh] rounded-2xl overflow-hidden border border-white/[0.08] bg-[#101317] text-[#F1EEE8] shadow-2xl">
        {/* Top Gold Horizon Accent */}
        <div className="h-px w-full bg-gradient-to-r from-transparent via-[#C4AD88]/40 to-transparent" />

        {/* ─────────────── HEADER ─────────────── */}
        <div className="shrink-0 px-6 pt-6 pb-4 bg-[#101317] border-b border-white/[0.07]">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-start gap-4">
              {/* Japanese Emblem */}
              <div className="relative shrink-0">
                <div className="flex h-12 w-12 items-center justify-center rounded-full border border-[#C4AD88]/30 bg-[#1B2228] shadow-inner">
                  <span
                    className="font-cinematic text-xl text-[#C4AD88]"
                    style={{ fontFamily: 'serif' }}
                    title="Realm"
                  >
                    界
                  </span>
                </div>
                <div className="absolute inset-0 rounded-full border border-[#C4AD88]/10 scale-110" />
              </div>

              <div>
                <div className="flex items-center gap-2 mb-0.5 flex-wrap">
                  <p className="text-[9px] font-mono uppercase tracking-[0.3em] text-[#858A8D]">
                    LIVING WORLD MATRIX · 世界の態
                  </p>
                  {storyTitle && (
                    <>
                      <span className="text-[9px] text-[#5A5F63]">·</span>
                      <span className="text-[9px] font-mono text-[#C4AD88] tracking-wider truncate max-w-[160px] sm:max-w-xs">
                        {storyTitle}
                      </span>
                    </>
                  )}
                </div>
                <h2 className="font-cinematic text-2xl font-semibold tracking-wide text-[#F1EEE8]">
                  The World Beyond
                </h2>
                <p className="mt-0.5 text-[11px] text-[#858A8D] font-mono">
                  Every choice reshapes what remains.
                </p>
              </div>
            </div>

            {/* Close button */}
            <button
              onClick={onClose}
              className="shrink-0 rounded-lg border border-white/10 p-2 text-[#858A8D] hover:border-white/20 hover:text-[#F1EEE8] transition"
              aria-label="Close World Matrix"
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Quick Stats Pill Row */}
          <div className="mt-4 flex items-center gap-3 text-[10px] font-mono text-[#858A8D] flex-wrap">
            <div className="flex items-center gap-1.5 rounded-full border border-white/10 bg-[#1B2228]/60 px-3 py-1">
              <span className="h-1.5 w-1.5 rounded-full bg-[#A33B42] animate-pulse" />
              <span className="text-[#D7DCE0]">Turn {turn}</span>
            </div>
            <div className="flex items-center gap-1.5 rounded-full border border-[#C4AD88]/30 bg-[#1B2228]/60 px-3 py-1">
              <span className="text-[#C4AD88]">幽玄 Yūgen</span>
              <span className="font-semibold text-[#F1EEE8]">{yugenMeter}%</span>
            </div>
            <div className="flex items-center gap-1.5 rounded-full border border-white/10 bg-[#1B2228]/60 px-3 py-1">
              <span className="text-[#858A8D]">Current Locale:</span>
              <span className="text-[#C4AD88] truncate max-w-[180px]">{currentLocationName}</span>
            </div>
          </div>

          {/* Navigation Tabs */}
          <div className="mt-4 flex items-center gap-2 overflow-x-auto pb-1">
            {TABS.map((tab) => {
              const isActive = activeTab === tab.id
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center gap-2 rounded-full border px-3.5 py-1.5 text-xs font-semibold whitespace-nowrap transition-all ${
                    isActive
                      ? 'border-[#C4AD88]/60 bg-[#C4AD88]/15 text-[#C4AD88] shadow-[0_0_15px_rgba(196,173,136,0.15)]'
                      : 'border-white/10 bg-transparent text-[#858A8D] hover:border-white/20 hover:text-[#D7DCE0]'
                  }`}
                >
                  <span className="font-cinematic text-sm" style={{ fontFamily: 'serif' }}>
                    {tab.kanji}
                  </span>
                  <span>{tab.label}</span>
                </button>
              )
            })}
          </div>
        </div>

        {/* ─────────────── TAB CONTENT BODY ─────────────── */}
        <div className="flex-1 overflow-y-auto px-6 py-6 overscroll-contain space-y-6">
          {/* TAB 1: ATMOSPHERE */}
          {activeTab === 'atmosphere' && (
            <div className="space-y-6">
              {/* Environmental Artwork Header Card */}
              <div className="relative h-48 sm:h-56 overflow-hidden rounded-xl border border-white/10 bg-[#101317]">
                <img
                  src={getWorldImage(currentLocationName)}
                  alt="Environmental Realm"
                  className="h-full w-full object-cover object-center filter brightness-95 contrast-125"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-[#101317] via-[#101317]/60 to-transparent" />
                <div className="absolute inset-0 bg-gradient-to-r from-[#101317]/80 via-transparent to-transparent" />

                <div className="absolute bottom-4 left-5 right-5 flex flex-col sm:flex-row sm:items-end justify-between gap-3">
                  <div>
                    <span className="text-[10px] uppercase font-mono tracking-widest text-[#C4AD88] block">
                      Active Atmosphere · 現象
                    </span>
                    <h3 className="font-cinematic text-2xl sm:text-3xl font-semibold text-[#F1EEE8] mt-0.5">
                      {currentLocationName}
                    </h3>
                    <p className="text-xs text-[#858A8D] mt-0.5 italic font-cinematic">
                      Mood · {currentMood}
                    </p>
                  </div>

                  <div className="flex items-center gap-2">
                    <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${perception.border} ${perception.badgeBg} ${perception.color}`}>
                      {perception.tier}
                    </span>
                  </div>
                </div>
              </div>

              {/* Yūgen Gauge Deep Dive */}
              <div className="rounded-xl border border-white/10 bg-[#171C21]/90 p-5 space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="font-cinematic text-base text-[#C4AD88]">✦</span>
                    <h4 className="font-cinematic text-lg font-semibold text-[#F1EEE8]">
                      Supernatural Density (幽玄 Yūgen Meter)
                    </h4>
                  </div>
                  <span className="font-mono text-2xl font-bold text-[#F1EEE8]">
                    {yugenMeter}<span className="text-sm font-normal text-[#858A8D]">/100</span>
                  </span>
                </div>

                {/* Progress bar */}
                <div className="space-y-1.5">
                  <div className="h-2.5 w-full rounded-full bg-white/[0.06] overflow-hidden p-0.5 border border-white/5">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-[#A33B42] via-[#C4AD88] to-[#F1EEE8] transition-all duration-700"
                      style={{ width: `${Math.min(100, Math.max(0, yugenMeter))}%` }}
                    />
                  </div>
                  <div className="flex justify-between text-[10px] font-mono text-[#858A8D]">
                    <span>0% Mundane Grounding</span>
                    <span>50% Veil Shift</span>
                    <span>100% Full Manifestation</span>
                  </div>
                </div>

                <p className="text-xs text-[#D7DCE0]/80 leading-relaxed font-cinematic">
                  {perception.desc}
                </p>
              </div>

              {/* Environmental Variables Cards */}
              <div className="grid gap-3 sm:grid-cols-3">
                <div className="rounded-xl border border-white/10 bg-[#171C21] p-4">
                  <span className="text-[10px] uppercase font-mono tracking-wider text-[#858A8D] block">
                    Time Flow
                  </span>
                  <p className="font-cinematic text-lg font-semibold text-[#F1EEE8] mt-1">
                    {worldState.time || 'Hour of the Ox · 深夜'}
                  </p>
                  <span className="text-[10px] text-[#5A5F63] font-mono mt-1 block">
                    Turn {turn} sequence
                  </span>
                </div>

                <div className="rounded-xl border border-white/10 bg-[#171C21] p-4">
                  <span className="text-[10px] uppercase font-mono tracking-wider text-[#858A8D] block">
                    Weather Manifest
                  </span>
                  <p className="font-cinematic text-lg font-semibold text-[#F1EEE8] mt-1">
                    {worldState.weather || 'Cold Mist & Mountain Rain'}
                  </p>
                  <span className="text-[10px] text-[#5A5F63] font-mono mt-1 block">
                    Environmental modifier
                  </span>
                </div>

                <div className="rounded-xl border border-white/10 bg-[#171C21] p-4">
                  <span className="text-[10px] uppercase font-mono tracking-wider text-[#858A8D] block">
                    Sanctuary Tension
                  </span>
                  <p className={`font-cinematic text-lg font-semibold mt-1 ${yugenMeter > 70 ? 'text-[#A33B42]' : 'text-[#C4AD88]'}`}>
                    {worldState.danger || (yugenMeter > 70 ? 'Heightened' : yugenMeter > 35 ? 'Latent' : 'Dormant')}
                  </p>
                  <span className="text-[10px] text-[#5A5F63] font-mono mt-1 block">
                    Instability threshold
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: WORLD VARIABLES & FLAGS */}
          {activeTab === 'conditions' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between border-b border-white/[0.08] pb-2">
                <div>
                  <h3 className="font-cinematic text-lg font-semibold text-[#F1EEE8]">
                    Active State Variables & Thresholds
                  </h3>
                  <p className="text-[11px] text-[#858A8D] font-mono">
                    Persistent key-value variables altered by previous decisions
                  </p>
                </div>
                <span className="text-[10px] font-mono text-[#C4AD88]">
                  {varEntries.length} Recorded
                </span>
              </div>

              {varEntries.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-12 text-center space-y-4">
                  <div className="flex h-14 w-14 items-center justify-center rounded-full border border-white/10 bg-[#1B2228]">
                    <span className="font-cinematic text-2xl text-[#858A8D]" style={{ fontFamily: 'serif' }}>
                      態
                    </span>
                  </div>
                  <div className="space-y-1 max-w-sm">
                    <p className="font-cinematic text-lg text-[#D7DCE0]">
                      The world has yet to reveal its true nature.
                    </p>
                    <p className="text-xs text-[#5A5F63] font-mono leading-relaxed">
                      As your journey unfolds, its hidden conditions will emerge.
                    </p>
                  </div>
                </div>
              ) : (
                <div className="grid gap-3 sm:grid-cols-2">
                  {varEntries.map(([key, value]) => {
                    const isBool = typeof value === 'boolean'
                    const isExpanded = expandedVarKey === key
                    const isTrue = value === true

                    return (
                      <div
                        key={key}
                        onClick={() => setExpandedVarKey(isExpanded ? null : key)}
                        className="group rounded-xl border border-white/10 bg-[#171C21]/80 p-4 transition-all hover:border-[#C4AD88]/30 cursor-pointer"
                      >
                        <div className="flex items-start justify-between gap-2">
                          <span className="text-xs font-mono uppercase tracking-wider text-[#858A8D] group-hover:text-[#D7DCE0] transition">
                            {key.replace(/_/g, ' ')}
                          </span>
                          {isBool ? (
                            <span
                              className={`rounded-full border px-2 py-0.5 text-[9px] font-mono font-semibold uppercase ${
                                isTrue
                                  ? 'border-[#C4AD88]/40 bg-[#C4AD88]/15 text-[#C4AD88]'
                                  : 'border-white/10 bg-white/5 text-[#5A5F63]'
                              }`}
                            >
                              {isTrue ? 'Active · 展' : 'False · 閉'}
                            </span>
                          ) : (
                            <span className="rounded-full border border-white/10 bg-[#1B2228] px-2 py-0.5 text-[10px] font-mono text-[#C4AD88]">
                              Value
                            </span>
                          )}
                        </div>

                        <p className="font-cinematic text-lg font-semibold text-[#F1EEE8] mt-1.5 break-words">
                          {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                        </p>

                        {isExpanded && (
                          <div className="mt-3 pt-3 border-t border-white/5 text-[11px] text-[#858A8D] font-mono">
                            <span>Key: </span>
                            <span className="text-[#C4AD88]">{key}</span>
                            <span className="block mt-0.5 text-[10px] text-[#5A5F63]">
                              Stored in unified playthrough memory
                            </span>
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          )}

          {/* TAB 3: LOCATIONS */}
          {activeTab === 'locations' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between border-b border-white/[0.08] pb-2">
                <div>
                  <h3 className="font-cinematic text-lg font-semibold text-[#F1EEE8]">
                    Story Geography & Anchors
                  </h3>
                  <p className="text-[11px] text-[#858A8D] font-mono">
                    Locations manifested and recorded in this journey
                  </p>
                </div>
                <span className="text-[10px] font-mono text-[#C4AD88]">
                  {scenes.length} Anchors
                </span>
              </div>

              {scenes.length === 0 ? (
                <div className="rounded-xl border border-white/10 bg-[#171C21] p-6 text-center text-xs text-[#858A8D]">
                  Location topography is still cloaked in mountain fog.
                </div>
              ) : (
                <div className="space-y-3">
                  {scenes.map((sc, idx) => {
                    const isCurrent = String(sc.id) === String(currentScene?.id)
                    const isExpanded = expandedLocationId === sc.id

                    return (
                      <div
                        key={sc.id}
                        onClick={() => setExpandedLocationId(isExpanded ? null : sc.id)}
                        className={`rounded-xl border p-4 transition-all cursor-pointer ${
                          isCurrent
                            ? 'border-[#A33B42]/60 bg-[#1B2228] shadow-[0_0_20px_rgba(163,59,66,0.15)]'
                            : 'border-white/10 bg-[#171C21]/70 hover:border-[#C4AD88]/30'
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            <span className="font-mono text-xs text-[#C4AD88]">
                              {String(idx + 1).padStart(2, '0')}.
                            </span>
                            <h4 className="font-cinematic text-xl font-semibold text-[#F1EEE8]">
                              {sc.location}
                            </h4>
                          </div>

                          <div className="flex items-center gap-2">
                            {isCurrent && (
                              <span className="flex items-center gap-1.5 rounded-full border border-[#A33B42]/60 bg-[#A33B42]/20 px-2.5 py-0.5 text-[10px] font-semibold text-[#F1EEE8]">
                                <span className="h-1.5 w-1.5 rounded-full bg-[#A33B42] animate-ping" />
                                Current Location
                              </span>
                            )}
                            {sc.is_ending && (
                              <span className="rounded-full border border-[#C4AD88]/50 bg-[#C4AD88]/10 px-2 py-0.5 text-[10px] text-[#C4AD88]">
                                ✦ Climax
                              </span>
                            )}
                          </div>
                        </div>

                        <p className="mt-1 text-xs text-[#858A8D] font-mono">
                          Atmosphere · {sc.mood || 'Unsettling silence'}
                        </p>

                        {isExpanded && (
                          <div className="mt-4 pt-3 border-t border-white/5 space-y-2">
                            {sc.content && (
                              <p className="font-cinematic text-sm leading-relaxed text-[#D7DCE0]/80 italic">
                                “{sc.content.slice(0, 180)}…”
                              </p>
                            )}
                            {sc.haiku && (
                              <div className="border-l-2 border-[#C4AD88]/40 pl-3 py-1">
                                <span className="text-[9px] uppercase font-mono tracking-widest text-[#C4AD88] block">
                                  Poetic Reflection
                                </span>
                                <p className="font-cinematic italic text-xs text-[#C4AD88]/90 whitespace-pre-line">
                                  {sc.haiku}
                                </p>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          )}

          {/* TAB 4: CHARACTER PRESENCE & EMOTIONAL RESONANCE */}
          {activeTab === 'characters' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between border-b border-white/[0.08] pb-2">
                <div>
                  <h3 className="font-cinematic text-lg font-semibold text-[#F1EEE8]">
                    Character Emotional Presence
                  </h3>
                  <p className="text-[11px] text-[#858A8D] font-mono">
                    Living state of individuals touched by this realm
                  </p>
                </div>
                <span className="text-[10px] font-mono text-[#C4AD88]">
                  {characterList.length} Inhabitant{characterList.length !== 1 ? 's' : ''}
                </span>
              </div>

              {characterList.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-12 text-center space-y-3">
                  <span className="font-cinematic text-3xl text-[#858A8D]/50" style={{ fontFamily: 'serif' }}>
                    人
                  </span>
                  <p className="font-cinematic text-base text-[#D7DCE0]">
                    No other souls have made themselves known yet.
                  </p>
                  <p className="text-xs text-[#5A5F63] font-mono">
                    They wander in the mist until your choices bring them near.
                  </p>
                </div>
              ) : (
                <div className="grid gap-4 sm:grid-cols-2">
                  {characterList.map((char) => {
                    const emos = char.emotions

                    return (
                      <div
                        key={char.id}
                        className="rounded-xl border border-white/10 bg-[#171C21] p-5 space-y-4"
                      >
                        <div className="flex items-start justify-between">
                          <div>
                            <span className="text-[9px] font-mono uppercase tracking-widest text-[#C4AD88]">
                              {char.role}
                            </span>
                            <h4 className="font-cinematic text-xl font-semibold text-[#F1EEE8] mt-0.5">
                              {char.name}
                            </h4>
                          </div>
                          <span className="flex h-8 w-8 items-center justify-center rounded-full border border-[#C4AD88]/30 bg-[#1B2228] font-cinematic text-xs text-[#C4AD88]">
                            魂
                          </span>
                        </div>

                        {/* Emotion Meters */}
                        <div className="space-y-2.5 pt-2 border-t border-white/5">
                          {/* Trust */}
                          <div>
                            <div className="flex justify-between text-[11px] font-mono mb-1">
                              <span className="text-[#858A8D]">Trust</span>
                              <span className="text-[#C4AD88]">{emos.trust ?? 50}%</span>
                            </div>
                            <div className="h-1.5 w-full rounded-full bg-white/[0.06] overflow-hidden">
                              <div
                                className="h-full rounded-full bg-[#C4AD88]"
                                style={{ width: `${Math.min(100, Math.max(0, emos.trust ?? 50))}%` }}
                              />
                            </div>
                          </div>

                          {/* Fear */}
                          <div>
                            <div className="flex justify-between text-[11px] font-mono mb-1">
                              <span className="text-[#858A8D]">Fear</span>
                              <span className="text-[#A33B42]">{emos.fear ?? 20}%</span>
                            </div>
                            <div className="h-1.5 w-full rounded-full bg-white/[0.06] overflow-hidden">
                              <div
                                className="h-full rounded-full bg-[#A33B42]"
                                style={{ width: `${Math.min(100, Math.max(0, emos.fear ?? 20))}%` }}
                              />
                            </div>
                          </div>

                          {/* Affection */}
                          <div>
                            <div className="flex justify-between text-[11px] font-mono mb-1">
                              <span className="text-[#858A8D]">Affection</span>
                              <span className="text-[#D7DCE0]">{emos.affection ?? 30}%</span>
                            </div>
                            <div className="h-1.5 w-full rounded-full bg-white/[0.06] overflow-hidden">
                              <div
                                className="h-full rounded-full bg-[#D7DCE0]"
                                style={{ width: `${Math.min(100, Math.max(0, emos.affection ?? 30))}%` }}
                              />
                            </div>
                          </div>

                          {/* Suspicion */}
                          <div>
                            <div className="flex justify-between text-[11px] font-mono mb-1">
                              <span className="text-[#858A8D]">Suspicion</span>
                              <span className="text-[#77323A]">{emos.suspicion ?? 25}%</span>
                            </div>
                            <div className="h-1.5 w-full rounded-full bg-white/[0.06] overflow-hidden">
                              <div
                                className="h-full rounded-full bg-[#77323A]"
                                style={{ width: `${Math.min(100, Math.max(0, emos.suspicion ?? 25))}%` }}
                              />
                            </div>
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          )}
        </div>

        {/* ─────────────── FOOTER ─────────────── */}
        <div className="shrink-0 flex items-center justify-between border-t border-white/[0.07] bg-[#101317] px-6 py-4">
          <div className="flex items-center gap-2 text-[10px] text-[#5A5F63] font-mono">
            <span className="font-cinematic text-sm text-[#C4AD88]/50" style={{ fontFamily: 'serif' }}>
              界
            </span>
            <span>
              Real-time synchronization with narrative runtime
            </span>
          </div>

          <button
            onClick={onClose}
            className="rounded-lg border border-white/10 bg-[#1B2228] px-5 py-2 text-xs font-semibold text-[#F1EEE8] hover:border-white/20 hover:text-white transition"
          >
            Close World Matrix
          </button>
        </div>
      </div>
    </div>
  )
}
