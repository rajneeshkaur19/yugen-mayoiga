import { useEffect, useMemo, useState } from 'react'
import { charactersApi, memoriesApi } from '../../api/client'

export default function CharacterDossierModal({
  isOpen,
  onClose,
  characters = {},
  relationships = {},
  storyId = null,
}) {
  const [dbCharacters, setDbCharacters] = useState([])
  const [characterMemories, setCharacterMemories] = useState([])
  const [loadingExtras, setLoadingExtras] = useState(false)
  const [selectedIndex, setSelectedIndex] = useState(0)
  const [generatingPortrait, setGeneratingPortrait] = useState(false)
  const [portraitError, setPortraitError] = useState(null)
  const [portraitImgError, setPortraitImgError] = useState(false)

  // Fetch deeper character records & memories if storyId is available
  useEffect(() => {
    if (!isOpen || !storyId) return
    let active = true

    async function fetchCharacterIntelligence() {
      setLoadingExtras(true)
      try {
        const [charsData, memsData] = await Promise.all([
          charactersApi.list(storyId).catch(() => []),
          memoriesApi.list(storyId).catch(() => []),
        ])

        if (active) {
          setDbCharacters(Array.isArray(charsData) ? charsData : [])
          setCharacterMemories(Array.isArray(memsData) ? memsData : [])
        }
      } catch {
        // Fallback gracefully to runtime props
      } finally {
        if (active) setLoadingExtras(false)
      }
    }

    fetchCharacterIntelligence()
    return () => { active = false }
  }, [isOpen, storyId])

  useEffect(() => {
    setPortraitImgError(false)
    setPortraitError(null)
  }, [selectedIndex])

  async function handleGeneratePortrait(characterId) {
    if (!storyId || !characterId || generatingPortrait) return
    setGeneratingPortrait(true)
    setPortraitError(null)
    setPortraitImgError(false)
    try {
      const updated = await charactersApi.generatePortrait(storyId, characterId)
      if (updated) {
        setDbCharacters((prev) =>
          prev.map((c) => (String(c.id) === String(characterId) ? { ...c, ...updated } : c))
        )
      }
    } catch (err) {
      setPortraitError(err.message || 'Portrait generation unavailable.')
    } finally {
      setGeneratingPortrait(false)
    }
  }

  // Combine runtime characters with any database records
  const characterList = useMemo(() => {
    // If DB characters exist, they form the primary source of truth
    if (dbCharacters && dbCharacters.length > 0) {
      return dbCharacters.map((dc) => {
        const runtimeMatch = Object.values(characters || {}).find(
          (c) => String(c.id) === String(dc.id) || c.name?.toLowerCase() === dc.name?.toLowerCase()
        )

        const trustVal = runtimeMatch?.emotions?.trust ?? (runtimeMatch?.trust ?? 55)
        const fearVal = runtimeMatch?.emotions?.fear ?? (runtimeMatch?.fear ?? 35)
        const affectionVal = runtimeMatch?.emotions?.affection ?? (runtimeMatch?.affection ?? 60)
        const suspicionVal = runtimeMatch?.emotions?.suspicion ?? (runtimeMatch?.suspicion ?? 30)

        let statusTag = 'Watchful & Reserved'
        if (fearVal >= 55 && trustVal < 45) statusTag = 'Fearful & Guarded'
        else if (trustVal >= 65 && fearVal < 40) statusTag = 'Trusting & Allied'
        else if (suspicionVal >= 60) statusTag = 'Guarded & Calculating'
        else if (fearVal >= 60) statusTag = 'Trembling in Silence'

        return {
          id: dc.id,
          dbId: dc.id,
          name: dc.name,
          role: dc.role || 'Inhabitant of Mayoiga',
          statusTag,
          background: dc.background || 'A presence that has lingered in this mountain sanctuary.',
          visual_description: dc.visual_description,
          visual_prompt_anchor: dc.visual_prompt_anchor,
          portrait_image_url: dc.portrait_image_url,
          personality:
            runtimeMatch?.personality ||
            (dc.role?.includes('Maiden') || dc.role?.includes('Archivist')
              ? 'Intuitive, easily unsettled by shifting corridors, bound by an old vow.'
              : 'Solemn, unwavering, measuring every action against ancient customs.'),
          behavior:
            dc.visual_description ||
            runtimeMatch?.behavior ||
            runtimeMatch?.observed_behavior ||
            'Stands silently near the threshold; listens to the sound of rainfall on weathered tiles.',
          emotions: {
            trust: trustVal,
            fear: fearVal,
            affection: affectionVal,
            suspicion: suspicionVal,
          },
          traits: dc.traits || null,
          fears: dc.fears?.length ? dc.fears : ['The breaking of the sacred threshold seals'],
          secrets: dc.secrets?.length ? dc.secrets : ['Holds an unspoken vow connected to this mountain.'],
          kanji: dc.role?.includes('Maiden') || dc.role?.includes('Archivist') ? '信' : '護',
        }
      })
    }

    const runtimeEntries = Object.entries(characters || {})

    if (runtimeEntries.length > 0) {
      return runtimeEntries.map(([id, c]) => {
        const dbMatch = dbCharacters.find(
          (dc) => String(dc.id) === String(id) || dc.name?.toLowerCase() === c.name?.toLowerCase()
        )

        const trustVal = c.emotions?.trust ?? (c.trust ?? 55)
        const fearVal = c.emotions?.fear ?? (c.fear ?? 35)
        const affectionVal = c.emotions?.affection ?? (c.affection ?? 60)
        const suspicionVal = c.emotions?.suspicion ?? (c.suspicion ?? 30)

        // Derive authentic status description from numbers
        let statusTag = 'Watchful & Reserved'
        if (fearVal >= 55 && trustVal < 45) statusTag = 'Fearful & Guarded'
        else if (trustVal >= 65 && fearVal < 40) statusTag = 'Trusting & Allied'
        else if (suspicionVal >= 60) statusTag = 'Guarded & Calculating'
        else if (fearVal >= 60) statusTag = 'Trembling in Silence'

        return {
          id,
          dbId: dbMatch?.id || (typeof id === 'number' ? id : null),
          name: c.name || `Character ${id}`,
          role: c.role || dbMatch?.role || 'Inhabitant of Mayoiga',
          statusTag,
          background:
            dbMatch?.background ||
            c.background ||
            'A presence that has lingered in this mountain estate since before the lanterns were first kindled.',
          visual_description: dbMatch?.visual_description || c.visual_description,
          visual_prompt_anchor: dbMatch?.visual_prompt_anchor || c.visual_prompt_anchor,
          portrait_image_url: dbMatch?.portrait_image_url || c.portrait_image_url,
          personality:
            c.personality ||
            (c.role?.includes('Companion')
              ? 'Intuitive, easily unsettled by shifting doors, bound by an old vow.'
              : 'Solemn, unwavering, counting keys that no longer open any doors.'),
          behavior:
            dbMatch?.visual_description ||
            c.behavior ||
            c.observed_behavior ||
            (c.role?.includes('Companion')
              ? 'Steps closer when the thunder cracks; avoids looking directly at the east corridor.'
              : 'Stands near the hearth embers; watches your hands whenever you examine old relics.'),
          emotions: {
            trust: trustVal,
            fear: fearVal,
            affection: affectionVal,
            suspicion: suspicionVal,
          },
          traits: dbMatch?.traits || null,
          fears: dbMatch?.fears || (c.role?.includes('Companion') ? ['Being left behind in the rain', 'The toll of the midnight bell'] : ['The breaking of the threshold seals']),
          secrets: dbMatch?.secrets || (c.role?.includes('Companion') ? ['Remembers a promise you made at the flooded shrine steps.'] : ['Holds the bronze key to the subterranean room.']),
          kanji: c.role?.includes('Companion') ? '信' : '護',
        }
      })
    }

    // Default atmospheric characters if runtime is empty
    return [
      {
        id: 'companion',
        name: 'Aiko',
        role: 'Companion · Keeper of Whispers',
        statusTag: 'Fearful & Guarded',
        background: 'Found sitting on the steps of the rain-soaked shrine holding an unaddressed wax-sealed letter.',
        personality: 'Quiet, intuitive, easily startled by sudden sounds, bound by an ancient vow.',
        behavior: 'Stands near doorways; avoids direct eye contact when fear increases; steps closer when the thunder roars.',
        emotions: { trust: 72, fear: 58, affection: 80, suspicion: 22 },
        traits: { openness: 75, agreeableness: 80, neuroticism: 65, conscientiousness: 70, extraversion: 40 },
        fears: ['Being abandoned in the rain', 'The seventh bell toll'],
        secrets: ['Remembers your hesitation at the flooded shrine steps.'],
        kanji: '信',
      },
      {
        id: 'guardian',
        name: 'The Caretaker',
        role: 'Master of Mayoiga · Threshold Guardian',
        statusTag: 'Vigilant & Calculating',
        background: 'An ageless figure tending the hearth fire in the cedar room, keeping count of every soul who crosses the estate gate.',
        personality: 'Strict, solemn, measuring every word against the estate’s unwritten laws.',
        behavior: 'Watches the hearth fire; counts the heavy bronze keys on his iron ring whenever footsteps approach.',
        emotions: { trust: 35, fear: 12, affection: 15, suspicion: 84 },
        traits: { openness: 30, agreeableness: 45, neuroticism: 25, conscientiousness: 95, extraversion: 20 },
        fears: ['The breaking of the sacred threshold seals'],
        secrets: ['Saw you inspect the forbidden cedar ledger in the corridor.'],
        kanji: '護',
      },
    ]
  }, [characters, dbCharacters])

  if (!isOpen) return null

  const current = characterList[selectedIndex] || characterList[0]

  // Filter memories relevant to this specific character
  const relevantMemories = characterMemories.filter(
    (m) => String(m.character_id) === String(current.id) || m.event?.includes(current.name)
  )

  // Extract relationship data relevant to this character
  const relevantRelationships = Object.entries(relationships || {}).filter(
    ([pair]) => pair.includes(String(current.id)) || pair.toLowerCase().includes(current.name?.toLowerCase())
  )

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 animate-fadeIn">
      {/* Dark Ambient Backdrop */}
      <div
        onClick={onClose}
        className="fixed inset-0 bg-black/85 backdrop-blur-md transition-opacity"
      />

      {/* Main Archival Dossier Panel */}
      <div className="relative z-10 w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden rounded-2xl border border-white/15 bg-[#14191E] text-[#F1EEE8] shadow-2xl">
        {/* ─────────────────────────────────────────────────────────
            1. DOSSIER TOP BANNER & EMBLEM
        ───────────────────────────────────────────────────────── */}
        <div className="flex items-center justify-between border-b border-white/10 px-6 py-4 bg-[#101317]">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-[#C4AD88]/40 bg-[#1B2228] text-[#C4AD88]">
              <span className="font-cinematic text-lg font-bold">{current.kanji || '調'}</span>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-[10px] uppercase font-mono tracking-widest text-[#C4AD88]">
                  Archival Intelligence Dossier
                </span>
                <span className="text-[10px] text-[#858A8D] font-mono">
                  · REF: SOUL-0{selectedIndex + 1}
                </span>
              </div>
              <h2 className="font-cinematic text-xl font-semibold tracking-wide text-[#F1EEE8]">
                Character Dossier · 人物調書
              </h2>
            </div>
          </div>

          <button
            onClick={onClose}
            className="rounded-lg border border-white/10 p-2 text-[#858A8D] hover:border-white/20 hover:text-white transition"
            title="Close dossier"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* ─────────────────────────────────────────────────────────
            2. CHARACTER SWITCHER TABS
        ───────────────────────────────────────────────────────── */}
        <div className="flex border-b border-white/10 bg-[#101317]/60 px-6 overflow-x-auto">
          {characterList.map((char, index) => {
            const isSelected = selectedIndex === index
            return (
              <button
                key={char.id || index}
                type="button"
                onClick={() => setSelectedIndex(index)}
                className={`flex items-center gap-2.5 border-b-2 px-5 py-3.5 text-xs font-medium transition whitespace-nowrap ${
                  isSelected
                    ? 'border-[#C4AD88] text-[#C4AD88] bg-white/[0.02]'
                    : 'border-transparent text-[#858A8D] hover:text-[#D7DCE0]'
                }`}
              >
                <span
                  className={`h-2 w-2 rounded-full ${
                    isSelected ? 'bg-[#A33B42] animate-pulse' : 'bg-white/20'
                  }`}
                />
                <span className="font-cinematic text-sm">{char.name}</span>
                <span className="text-[10px] text-[#858A8D] font-mono">({char.role?.split('·')[0].trim()})</span>
              </button>
            )
          })}
        </div>

        {/* ─────────────────────────────────────────────────────────
            3. TWO-COLUMN ARCHIVAL DOSSIER BODY
        ───────────────────────────────────────────────────────── */}
        <div className="flex-1 overflow-y-auto p-6 sm:p-8">
          <div className="grid gap-8 lg:grid-cols-12 items-start">
            {/* ─── LEFT COLUMN: Identity, Background & Observations (Col 1-5) ─── */}
            <div className="lg:col-span-5 space-y-6">
              {/* Character Portrait Card */}
              <div className="relative rounded-2xl border border-white/10 bg-[#101317] p-4 shadow-xl overflow-hidden group">
                <div className="relative h-64 w-full rounded-xl overflow-hidden bg-[#171C21] border border-white/5 flex items-center justify-center">
                  {current.portrait_image_url && !portraitImgError ? (
                    <img
                      src={current.portrait_image_url}
                      alt={current.name}
                      className="h-full w-full object-cover object-top transition-transform duration-700 group-hover:scale-105 filter brightness-95 contrast-110"
                      onError={() => setPortraitImgError(true)}
                    />
                  ) : (
                    <div className="flex flex-col items-center justify-center text-center p-6 space-y-3">
                      <div className="flex h-16 w-16 items-center justify-center rounded-full border border-[#C4AD88]/30 bg-[#C4AD88]/10 text-2xl font-cinematic text-[#C4AD88]">
                        {current.kanji || '画'}
                      </div>
                      <div className="space-y-1">
                        <p className="text-xs font-cinematic text-[#F1EEE8] tracking-wide">
                          {current.visual_prompt_anchor || `${current.name} · ${current.role}`}
                        </p>
                        <p className="text-[10px] text-[#858A8D] font-mono">
                          Portrait not yet inscribed in the archive.
                        </p>
                      </div>
                    </div>
                  )}

                  {/* Gradient vignette */}
                  <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-black/20 pointer-events-none" />

                  {/* Kanji Seal Badge in Corner */}
                  <div className="absolute top-3 left-3 flex items-center gap-1.5 rounded bg-black/60 backdrop-blur-md px-2 py-0.5 border border-white/10 text-[10px] font-mono text-[#C4AD88]">
                    <span>{current.kanji || '印'}</span>
                    <span>{current.role?.split('·')[0].trim()}</span>
                  </div>

                  {/* On-Demand Manifest Button */}
                  <div className="absolute bottom-3 right-3 z-10">
                    <button
                      type="button"
                      disabled={generatingPortrait || !storyId || !current.dbId}
                      onClick={() => handleGeneratePortrait(current.dbId || current.id)}
                      className="inline-flex items-center gap-1.5 rounded-lg border border-[#A33B42] bg-[#A33B42]/90 hover:bg-[#702B34] px-3 py-1.5 text-[11px] font-semibold text-[#F1EEE8] transition shadow-lg backdrop-blur-sm disabled:opacity-50"
                    >
                      {generatingPortrait ? (
                        <>
                          <span className="inline-block h-2.5 w-2.5 animate-spin rounded-full border-2 border-white border-t-transparent" />
                          <span>Inscribing…</span>
                        </>
                      ) : (
                        <>
                          <span>✨</span>
                          <span>{current.portrait_image_url ? 'Repaint' : 'Manifest Portrait'}</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>

                {portraitError && (
                  <p className="mt-2 text-[10px] text-[#A33B42] text-center font-mono">
                    {portraitError}
                  </p>
                )}
              </div>

              {/* Identity Box */}
              <div className="rounded-2xl border border-white/10 bg-[#101317] p-6 shadow-inner relative overflow-hidden">
                <div className="absolute top-0 right-0 w-24 h-24 bg-gradient-to-bl from-[#C4AD88]/10 via-transparent to-transparent pointer-events-none" />

                <div className="flex items-start justify-between">
                  <div>
                    <span className="text-[10px] uppercase font-mono tracking-widest text-[#C4AD88] block">
                      {current.role}
                    </span>
                    <h3 className="font-cinematic text-3xl font-semibold text-[#F1EEE8] mt-1">
                      {current.name}
                    </h3>
                  </div>

                  <span className="rounded-full border border-[#A33B42]/50 bg-[#A33B42]/20 px-3 py-1 text-[11px] font-semibold text-[#F1EEE8] shrink-0">
                    {current.statusTag}
                  </span>
                </div>

                <p className="mt-4 font-cinematic text-sm italic text-[#D7DCE0] leading-relaxed border-l-2 border-[#C4AD88]/40 pl-3">
                  "{current.personality}"
                </p>

                <p className="mt-4 text-xs text-[#858A8D] leading-relaxed">
                  {current.background}
                </p>
              </div>

              {/* Observed Physical Nuance & Visual Profile */}
              <div className="rounded-xl border border-white/10 bg-[#101317] p-5 space-y-3">
                <div className="flex items-center gap-2">
                  <span className="text-xs text-[#C4AD88]">👁</span>
                  <span className="text-[10px] uppercase font-mono tracking-wider text-[#858A8D]">
                    Visual Nuance & Attire
                  </span>
                </div>
                <p className="text-xs text-[#D7DCE0] leading-relaxed">
                  {current.visual_description || current.behavior}
                </p>
                {current.visual_prompt_anchor && (
                  <p className="text-[10px] font-mono text-[#858A8D] border-t border-white/5 pt-2">
                    <span className="text-[#C4AD88]">Visual Anchor:</span> {current.visual_prompt_anchor}
                  </p>
                )}
              </div>

              {/* Fears & Secrets (from backend) */}
              <div className="rounded-xl border border-white/10 bg-[#101317] p-5 space-y-3">
                <span className="text-[10px] uppercase font-mono tracking-wider text-[#A33B42] block">
                  Discovered Psychological Vulnerabilities
                </span>

                {current.fears?.length > 0 && (
                  <div className="text-xs">
                    <span className="text-[#858A8D] block text-[10px] font-mono">Deepest Fear</span>
                    <span className="text-[#D7DCE0] mt-0.5 block">{current.fears[0]}</span>
                  </div>
                )}

                {current.secrets?.length > 0 && (
                  <div className="text-xs border-t border-white/5 pt-2">
                    <span className="text-[#858A8D] block text-[10px] font-mono">Known Secret</span>
                    <span className="font-cinematic italic text-xs text-[#C4AD88] mt-0.5 block">
                      "{current.secrets[0]}"
                    </span>
                  </div>
                )}
              </div>

              {/* Relationship Connections */}
              {relevantRelationships.length > 0 && (
                <div className="rounded-xl border border-white/10 bg-[#101317] p-5 space-y-3">
                  <span className="text-[10px] uppercase font-mono tracking-wider text-[#C4AD88] block">
                    Relationship Dynamics
                  </span>
                  <div className="space-y-2">
                    {relevantRelationships.map(([pair, rel]) => (
                      <div key={pair} className="text-xs rounded border border-white/5 bg-[#1B2228]/50 p-2.5">
                        <span className="text-[#858A8D] font-mono block text-[10px]">{pair.replace('->', ' → ')}</span>
                        <div className="mt-1 flex flex-wrap gap-2 text-[10px] font-mono text-[#D7DCE0]">
                          <span>Trust: {rel.trust}%</span>
                          <span>·</span>
                          <span>Suspicion: {rel.suspicion}%</span>
                          <span>·</span>
                          <span>Fear: {rel.fear}%</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* ─── RIGHT COLUMN: Emotion Meters & Memory Archive (Col 6-12) ─── */}
            <div className="lg:col-span-7 space-y-6">
              {/* Emotional State Gauges */}
              <div className="rounded-2xl border border-white/10 bg-[#101317] p-6 sm:p-7 shadow-inner space-y-5">
                <div className="flex items-center justify-between border-b border-white/[0.08] pb-3">
                  <div>
                    <span className="text-[10px] uppercase font-mono tracking-widest text-[#C4AD88]">
                      Psychological Resonance
                    </span>
                    <h4 className="font-cinematic text-xl font-semibold text-[#F1EEE8] mt-0.5">
                      Emotional Matrix Values
                    </h4>
                  </div>
                  <span className="text-[10px] font-mono text-[#858A8D]">Real-Time State</span>
                </div>

                {/* 4 Core Meters */}
                <div className="space-y-4">
                  {/* Trust */}
                  <div className="rounded-xl border border-white/5 bg-[#171C21] p-3.5">
                    <div className="flex justify-between items-center text-xs mb-1.5">
                      <div className="flex items-center gap-2">
                        <span className="h-2 w-2 rounded-full bg-[#C4AD88]" />
                        <span className="font-medium text-[#F1EEE8]">Trust in Wanderer</span>
                      </div>
                      <span className="font-mono text-sm font-semibold text-[#C4AD88]">
                        {current.emotions.trust}%
                      </span>
                    </div>
                    <div className="h-2 w-full rounded-full bg-white/5 overflow-hidden">
                      <div
                        className="h-full rounded-full bg-[#C4AD88] transition-all duration-700"
                        style={{ width: `${Math.min(100, Math.max(0, current.emotions.trust))}%` }}
                      />
                    </div>
                    <span className="text-[10px] text-[#858A8D] mt-1.5 block">
                      Determines willingness to share hidden keys and secret pathways.
                    </span>
                  </div>

                  {/* Fear */}
                  <div className="rounded-xl border border-white/5 bg-[#171C21] p-3.5">
                    <div className="flex justify-between items-center text-xs mb-1.5">
                      <div className="flex items-center gap-2">
                        <span className="h-2 w-2 rounded-full bg-[#A33B42]" />
                        <span className="font-medium text-[#F1EEE8]">Fear of the Unknown</span>
                      </div>
                      <span className="font-mono text-sm font-semibold text-[#A33B42]">
                        {current.emotions.fear}%
                      </span>
                    </div>
                    <div className="h-2 w-full rounded-full bg-white/5 overflow-hidden">
                      <div
                        className="h-full rounded-full bg-[#A33B42] transition-all duration-700"
                        style={{ width: `${Math.min(100, Math.max(0, current.emotions.fear))}%` }}
                      />
                    </div>
                    <span className="text-[10px] text-[#858A8D] mt-1.5 block">
                      High fear causes hesitation at closed doors and speech in whispers.
                    </span>
                  </div>

                  {/* Affection */}
                  <div className="rounded-xl border border-white/5 bg-[#171C21] p-3.5">
                    <div className="flex justify-between items-center text-xs mb-1.5">
                      <div className="flex items-center gap-2">
                        <span className="h-2 w-2 rounded-full bg-[#D7DCE0]" />
                        <span className="font-medium text-[#F1EEE8]">Affection / Nostalgia</span>
                      </div>
                      <span className="font-mono text-sm font-semibold text-[#D7DCE0]">
                        {current.emotions.affection}%
                      </span>
                    </div>
                    <div className="h-2 w-full rounded-full bg-white/5 overflow-hidden">
                      <div
                        className="h-full rounded-full bg-[#D7DCE0] transition-all duration-700"
                        style={{ width: `${Math.min(100, Math.max(0, current.emotions.affection))}%` }}
                      />
                    </div>
                    <span className="text-[10px] text-[#858A8D] mt-1.5 block">
                      Emotional resonance connecting the character to your forgotten promises.
                    </span>
                  </div>

                  {/* Suspicion */}
                  <div className="rounded-xl border border-white/5 bg-[#171C21] p-3.5">
                    <div className="flex justify-between items-center text-xs mb-1.5">
                      <div className="flex items-center gap-2">
                        <span className="h-2 w-2 rounded-full bg-[#702B34]" />
                        <span className="font-medium text-[#F1EEE8]">Suspicion of Motives</span>
                      </div>
                      <span className="font-mono text-sm font-semibold text-[#C4AD88]">
                        {current.emotions.suspicion}%
                      </span>
                    </div>
                    <div className="h-2 w-full rounded-full bg-white/5 overflow-hidden">
                      <div
                        className="h-full rounded-full bg-[#702B34] transition-all duration-700"
                        style={{ width: `${Math.min(100, Math.max(0, current.emotions.suspicion))}%` }}
                      />
                    </div>
                    <span className="text-[10px] text-[#858A8D] mt-1.5 block">
                      Increases when examining locked chests or lingering after bells ring.
                    </span>
                  </div>
                </div>
              </div>

              {/* Character-Linked Memory Timeline */}
              <div className="rounded-2xl border border-white/10 bg-[#101317] p-6 shadow-inner space-y-4">
                <div className="flex items-center justify-between border-b border-white/[0.08] pb-3">
                  <div className="flex items-center gap-2">
                    <span className="text-[#C4AD88] font-cinematic text-sm">✦</span>
                    <h4 className="font-cinematic text-xl font-semibold text-[#F1EEE8]">
                      Memory Engravings
                    </h4>
                  </div>
                  <span className="text-[10px] font-mono text-[#858A8D]">
                    {relevantMemories.length} Impressions
                  </span>
                </div>

                {relevantMemories.length > 0 ? (
                  <div className="space-y-3">
                    {relevantMemories.map((mem) => {
                      const isCritical = (mem.importance ?? 0) >= 80
                      return (
                        <div
                          key={mem.id}
                          className="rounded-xl border border-white/5 bg-[#171C21] p-4 text-xs space-y-1.5"
                        >
                          <div className="flex items-center justify-between">
                            <span className="font-mono text-[10px] text-[#C4AD88]">
                              Turn {mem.created_turn ?? 1} · {mem.type || 'Observation'}
                            </span>
                            {isCritical ? (
                              <span className="rounded bg-[#A33B42]/20 border border-[#A33B42]/50 px-2 py-0.5 text-[9px] text-[#F1EEE8]">
                                Critical
                              </span>
                            ) : (
                              <span className="rounded bg-white/5 px-2 py-0.5 text-[9px] text-[#858A8D]">
                                Impression
                              </span>
                            )}
                          </div>
                          <p className="font-cinematic text-base italic text-[#F1EEE8]">
                            “{mem.event}”
                          </p>
                        </div>
                      )
                    })}
                  </div>
                ) : (
                  <div className="py-6 text-center text-xs text-[#858A8D] border border-dashed border-white/5 rounded-xl">
                    <p className="font-cinematic text-base italic text-[#D7DCE0]">
                      “The quiet waters have not yet rippled for this soul.”
                    </p>
                    <p className="mt-1 text-[11px] text-[#858A8D]">
                      Advance through decisions in the story to engrave permanent memories with {current.name}.
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* ─────────────────────────────────────────────────────────
            4. DOSSIER FOOTER
        ───────────────────────────────────────────────────────── */}
        <div className="flex items-center justify-between border-t border-white/10 bg-[#101317] px-6 py-4 text-xs text-[#858A8D]">
          <span className="font-mono text-[11px]">
            Archival Record Complete · Yūgen Intelligence Matrix
          </span>
          <button
            onClick={onClose}
            className="rounded-lg border border-white/10 bg-[#1B2228] px-5 py-2 text-xs font-semibold text-[#F1EEE8] hover:border-white/20 hover:bg-white/10 transition"
          >
            Close Dossier
          </button>
        </div>
      </div>
    </div>
  )
}
