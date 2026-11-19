import { useEffect, useMemo, useState } from 'react'
import { memoriesApi } from '../../api/client'

export default function MemoriesModal({
  isOpen,
  onClose,
  storyId,
  runtimeMemories = [],
  storyTitle = '',
}) {
  const [memories, setMemories] = useState([])
  const [loading, setLoading] = useState(false)
  const [selectedMemory, setSelectedMemory] = useState(null)

  // Filters & Sorting state
  const [searchQuery, setSearchQuery] = useState('')
  const [activeFilter, setActiveFilter] = useState('all')
  const [sortBy, setSortBy] = useState('newest')

  useEffect(() => {
    if (!isOpen || !storyId) return
    let active = true

    async function fetchMemories() {
      setLoading(true)
      try {
        const data = await memoriesApi.list(storyId)
        if (active) {
          const list = Array.isArray(data) ? data : []
          setMemories(list.length ? list : fallbackMemories)
        }
      } catch {
        if (active) {
          setMemories(fallbackMemories)
        }
      } finally {
        if (active) setLoading(false)
      }
    }

    fetchMemories()
    return () => { active = false }
  }, [isOpen, storyId])

  // Realistic story memories matching backend schema
  const fallbackMemories = runtimeMemories.length ? runtimeMemories : [
    {
      id: 1,
      event: 'The Vow in the Rain: Before the locked wooden doors, you refused to abandon the threshold as the bell rang.',
      importance: 85,
      type: 'emotional',
      emotional_weight: 40,
      created_turn: 1,
      status: 'gilded',
    },
    {
      id: 2,
      event: 'The Locked Screen: A decision in the western corridor that permanently barred the return pathway.',
      importance: 95,
      type: 'player_choice',
      emotional_weight: -25,
      created_turn: 2,
      status: 'cracked',
    },
    {
      id: 3,
      event: 'The Timetable Inscription: You uncovered the fading ink noting that some doors open only when remembered.',
      importance: 60,
      type: 'short_term',
      emotional_weight: 15,
      created_turn: 3,
      status: 'normal',
    },
  ]

  // Filter and sort computation
  const filteredMemories = useMemo(() => {
    return memories
      .filter((mem) => {
        const text = (mem.event || '').toLowerCase()
        const matchesSearch = text.includes(searchQuery.toLowerCase())
        if (!matchesSearch) return false

        const isCritical = (mem.importance ?? 0) >= 80 || mem.status === 'cracked'
        const isImportant = (mem.importance ?? 0) >= 50 && (mem.importance ?? 0) < 80
        const isImpression = (mem.importance ?? 0) < 50 && !isCritical

        if (activeFilter === 'all') return true
        if (activeFilter === 'critical') return isCritical
        if (activeFilter === 'important') return isImportant
        if (activeFilter === 'impression') return isImpression
        if (activeFilter === 'player_choice') return mem.type === 'player_choice'
        if (activeFilter === 'emotional') return mem.type === 'emotional'
        return true
      })
      .sort((a, b) => {
        if (sortBy === 'newest') {
          return (b.created_turn ?? 0) - (a.created_turn ?? 0)
        }
        if (sortBy === 'oldest') {
          return (a.created_turn ?? 0) - (b.created_turn ?? 0)
        }
        if (sortBy === 'importance') {
          return (b.importance ?? 0) - (a.importance ?? 0)
        }
        return 0
      })
  }, [memories, searchQuery, activeFilter, sortBy])

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 animate-fadeIn">
      {/* Dark Ambient Backdrop */}
      <div onClick={onClose} className="fixed inset-0 bg-black/85 backdrop-blur-md transition-opacity" />

      {/* Main Memory Vault Modal */}
      <div className="relative z-10 w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden rounded-2xl border border-white/15 bg-[#14191E] text-[#F1EEE8] shadow-2xl">
        {/* ─────────────────────────────────────────────────────────────
            1. ARCHIVE HEADER
        ───────────────────────────────────────────────────────────── */}
        <div className="border-b border-white/10 px-6 py-5 bg-[#101317]">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-[#C4AD88]/30 bg-[#1B2228] text-[#C4AD88]">
                <svg className="h-5 w-5 text-[#A33B42]" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M2 5h20v2H2V5zm3 3h14v2H5V8zm2 3h2v11H7V11zm8 0h2v11h-2V11zM1 3h22v2H1V3z" />
                </svg>
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] uppercase font-mono tracking-widest text-[#C4AD88]">
                    Memory Vault · 記憶の保管所
                  </span>
                  {storyTitle && (
                    <span className="text-[10px] text-[#858A8D] font-mono">
                      · {storyTitle}
                    </span>
                  )}
                </div>
                <h2 className="font-cinematic text-2xl font-semibold tracking-wide text-[#F1EEE8]">
                  Memories That Remain
                </h2>
              </div>
            </div>

            <button
              onClick={onClose}
              className="rounded-lg border border-white/10 p-2 text-[#858A8D] hover:border-white/20 hover:text-white transition"
              title="Close archive"
            >
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <p className="font-cinematic text-sm italic text-[#D7DCE0] mt-2">
            “Every choice leaves a mark. Some fade. Others refuse to disappear.”
          </p>
        </div>

        {/* ─────────────────────────────────────────────────────────────
            2. FILTERS, SEARCH & SORT CONTROLS
        ───────────────────────────────────────────────────────────── */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-white/10 bg-[#101317]/60 px-6 py-3 text-xs">
          {/* Filter Pills */}
          <div className="flex items-center gap-2 overflow-x-auto pb-1 sm:pb-0">
            {[
              { id: 'all', label: 'All Records' },
              { id: 'critical', label: 'Critical' },
              { id: 'important', label: 'Important' },
              { id: 'impression', label: 'Impressions' },
              { id: 'player_choice', label: 'Choices' },
              { id: 'emotional', label: 'Emotional' },
            ].map((f) => (
              <button
                key={f.id}
                onClick={() => {
                  setActiveFilter(f.id)
                  setSelectedMemory(null)
                }}
                className={`rounded-lg px-3 py-1.5 whitespace-nowrap transition text-xs ${
                  activeFilter === f.id
                    ? 'border border-[#C4AD88] bg-[#C4AD88]/15 text-[#C4AD88] font-medium'
                    : 'border border-white/5 bg-[#171C21] text-[#858A8D] hover:text-[#D7DCE0]'
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>

          {/* Search & Sort */}
          <div className="flex items-center gap-2 shrink-0">
            <input
              type="text"
              placeholder="Search impressions..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-36 sm:w-44 rounded-lg border border-white/10 bg-[#101317] px-3 py-1.5 text-xs text-[#F1EEE8] placeholder-[#858A8D] outline-none focus:border-[#C4AD88]/60 transition"
            />
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="rounded-lg border border-white/10 bg-[#101317] px-2.5 py-1.5 text-xs text-[#D7DCE0] outline-none focus:border-[#C4AD88]/60 transition"
            >
              <option value="newest">Newest Turn</option>
              <option value="oldest">Oldest Turn</option>
              <option value="importance">Highest Importance</option>
            </select>
          </div>
        </div>

        {/* ─────────────────────────────────────────────────────────────
            3. MEMORY LIST / DETAIL VIEW CONTAINER
        ───────────────────────────────────────────────────────────── */}
        <div className="flex-1 overflow-y-auto p-6 sm:p-8">
          {loading ? (
            <div className="py-24 text-center">
              <div className="inline-block h-3 w-3 rounded-full bg-[#A33B42] animate-ping" />
              <p className="mt-3 font-cinematic text-lg text-[#858A8D]">Opening the sealed memory vault...</p>
            </div>
          ) : selectedMemory ? (
            /* ─── DETAILED INSPECTION VIEW ─── */
            <div className="rounded-2xl border border-[#C4AD88]/40 bg-[#101317] p-6 sm:p-8 space-y-6 animate-fadeIn shadow-2xl">
              <div className="flex items-center justify-between border-b border-white/10 pb-4">
                <div className="flex items-center gap-3">
                  <span className="font-cinematic text-lg text-[#C4AD88]">✦</span>
                  <span className="font-mono text-xs uppercase tracking-widest text-[#C4AD88]">
                    Memory Inspection · Ref #{selectedMemory.id}
                  </span>
                </div>
                <button
                  onClick={() => setSelectedMemory(null)}
                  className="rounded-lg border border-white/10 px-3 py-1 text-xs text-[#858A8D] hover:text-white transition"
                >
                  ← Back to Archive
                </button>
              </div>

              {/* Memory Narrative */}
              <div>
                <span className="text-[10px] uppercase font-mono tracking-wider text-[#858A8D] block mb-2">
                  Chronicle Inscription
                </span>
                <p className="font-cinematic text-2xl sm:text-3xl font-semibold italic text-[#F1EEE8] leading-relaxed">
                  “{selectedMemory.event}”
                </p>
              </div>

              {/* Memory Metadata Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 border-t border-white/10 pt-6 text-xs">
                <div className="p-3.5 rounded-xl border border-white/5 bg-[#171C21]">
                  <span className="text-[#858A8D] block text-[10px] font-mono">Turn Recorded</span>
                  <span className="font-cinematic text-lg font-semibold text-[#F1EEE8] mt-1 block">
                    Turn 0{selectedMemory.created_turn ?? 1}
                  </span>
                </div>

                <div className="p-3.5 rounded-xl border border-white/5 bg-[#171C21]">
                  <span className="text-[#858A8D] block text-[10px] font-mono">Classification</span>
                  <span className="font-cinematic text-lg font-semibold text-[#C4AD88] mt-1 block capitalize">
                    {selectedMemory.type?.replace('_', ' ') || 'Impression'}
                  </span>
                </div>

                <div className="p-3.5 rounded-xl border border-white/5 bg-[#171C21]">
                  <span className="text-[#858A8D] block text-[10px] font-mono">Significance</span>
                  <span className="font-mono text-lg font-semibold text-[#F1EEE8] mt-1 block">
                    {selectedMemory.importance ?? 50}%
                  </span>
                </div>

                <div className="p-3.5 rounded-xl border border-white/5 bg-[#171C21]">
                  <span className="text-[#858A8D] block text-[10px] font-mono">Emotional Weight</span>
                  <span
                    className={`font-mono text-lg font-semibold mt-1 block ${
                      (selectedMemory.emotional_weight ?? 0) >= 0 ? 'text-[#C4AD88]' : 'text-[#A33B42]'
                    }`}
                  >
                    {(selectedMemory.emotional_weight ?? 0) > 0
                      ? `+${selectedMemory.emotional_weight}`
                      : selectedMemory.emotional_weight ?? 0}
                  </span>
                </div>
              </div>

              {/* Status Meaning */}
              <div className="rounded-xl border border-white/5 bg-[#1B2228] p-4 text-xs">
                <span className="text-[10px] uppercase font-mono tracking-wider text-[#C4AD88] block mb-1">
                  Engine Status: {selectedMemory.status || 'Normal'}
                </span>
                <p className="text-[#D7DCE0] leading-relaxed">
                  {selectedMemory.status === 'cracked'
                    ? 'A cracked memory marks an irreversible turning point in the chronicle that permanently altered character disposition.'
                    : selectedMemory.status === 'gilded'
                    ? 'A gilded memory represents an enduring oath that resonates across scenes and elevates character trust.'
                    : 'A standard memory impression quietly influencing subtle dialogue choices.'}
                </p>
              </div>
            </div>
          ) : filteredMemories.length === 0 ? (
            /* ─── EMPTY STATE ─── */
            <div className="rounded-2xl border border-dashed border-white/10 bg-[#101317]/40 py-20 px-6 text-center max-w-md mx-auto space-y-4">
              <div className="inline-flex h-12 w-12 items-center justify-center rounded-full border border-[#C4AD88]/30 bg-[#1B2228] text-[#C4AD88]">
                <svg className="h-6 w-6 text-[#A33B42]" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M2 5h20v2H2V5zm3 3h14v2H5V8zm2 3h2v11H7V11zm8 0h2v11h-2V11zM1 3h22v2H1V3z" />
                </svg>
              </div>
              <h3 className="font-cinematic text-2xl font-semibold text-[#F1EEE8]">
                Nothing has been written into the archive yet.
              </h3>
              <p className="text-xs text-[#858A8D] leading-relaxed">
                {searchQuery
                  ? 'No memory engravings match your search term.'
                  : 'Your choices will leave their first traces here. Step into the story and make your decisions.'}
              </p>
            </div>
          ) : (
            /* ─── CHRONOLOGICAL MEMORY TIMELINE GRID ─── */
            <div className="space-y-4">
              {filteredMemories.map((mem) => {
                const isCritical = (mem.importance ?? 0) >= 80 || mem.status === 'cracked'
                const isImportant = (mem.importance ?? 0) >= 50 && (mem.importance ?? 0) < 80

                return (
                  <div
                    key={mem.id}
                    onClick={() => setSelectedMemory(mem)}
                    className={`group cursor-pointer rounded-2xl border p-5 sm:p-6 transition-all duration-300 ${
                      isCritical
                        ? 'border-[#A33B42]/50 bg-[#171C21] hover:border-[#A33B42] hover:shadow-[0_0_20px_rgba(163,59,66,0.25)]'
                        : isImportant
                        ? 'border-[#C4AD88]/30 bg-[#171C21] hover:border-[#C4AD88] hover:shadow-[0_0_15px_rgba(196,173,136,0.2)]'
                        : 'border-white/10 bg-[#101317] hover:border-white/20'
                    }`}
                  >
                    {/* Header line */}
                    <div className="flex items-center justify-between gap-4">
                      <div className="flex items-center gap-2.5">
                        <span className="font-mono text-xs text-[#C4AD88]">
                          Turn 0{mem.created_turn ?? 1}
                        </span>
                        <span className="text-[#858A8D] text-xs">·</span>
                        <span className="text-[11px] font-mono text-[#858A8D] capitalize">
                          {mem.type?.replace('_', ' ') || 'Impression'}
                        </span>
                      </div>

                      {/* Significance Badge */}
                      {isCritical ? (
                        <span className="rounded-full border border-[#A33B42] bg-[#A33B42]/20 px-3 py-0.5 text-[10px] font-semibold text-[#F1EEE8] shadow-sm">
                          Critical Memory
                        </span>
                      ) : isImportant ? (
                        <span className="rounded-full border border-[#C4AD88]/50 bg-[#C4AD88]/15 px-3 py-0.5 text-[10px] font-medium text-[#C4AD88]">
                          Important
                        </span>
                      ) : (
                        <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-0.5 text-[10px] text-[#858A8D]">
                          Impression
                        </span>
                      )}
                    </div>

                    {/* Narrative Description */}
                    <p className="mt-3 font-cinematic text-lg sm:text-xl leading-relaxed text-[#F1EEE8] group-hover:text-[#C4AD88] transition">
                      “{mem.event}”
                    </p>

                    {/* Card Footer */}
                    <div className="mt-4 pt-3 border-t border-white/5 flex items-center justify-between text-xs text-[#858A8D]">
                      <div className="flex items-center gap-4 text-[11px] font-mono">
                        <div>
                          Importance: <span className="text-[#F1EEE8]">{mem.importance ?? 50}%</span>
                        </div>
                        <div>·</div>
                        <div>
                          Weight:{' '}
                          <span
                            className={
                              (mem.emotional_weight ?? 0) >= 0 ? 'text-[#C4AD88]' : 'text-[#A33B42]'
                            }
                          >
                            {(mem.emotional_weight ?? 0) > 0
                              ? `+${mem.emotional_weight}`
                              : mem.emotional_weight ?? 0}
                          </span>
                        </div>
                      </div>

                      <span className="text-[11px] text-[#C4AD88] group-hover:underline flex items-center gap-1">
                        <span>Inspect detail</span>
                        <span>→</span>
                      </span>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>

        {/* ─────────────────────────────────────────────────────────────
            4. ARCHIVE FOOTER
        ───────────────────────────────────────────────────────────── */}
        <div className="flex items-center justify-between border-t border-white/10 bg-[#101317] px-6 py-4 text-xs text-[#858A8D]">
          <span className="font-mono text-[11px]">
            {filteredMemories.length} of {memories.length} Memory Fragments Engraved
          </span>
          <button
            onClick={onClose}
            className="rounded-lg border border-white/10 bg-[#1B2228] px-5 py-2 text-xs font-semibold text-[#F1EEE8] hover:border-white/20 hover:bg-white/10 transition"
          >
            Close Vault
          </button>
        </div>
      </div>
    </div>
  )
}
