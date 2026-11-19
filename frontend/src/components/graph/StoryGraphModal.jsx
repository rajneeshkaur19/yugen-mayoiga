import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { choicesApi } from '../../api/client'

// ─── Status classification ──────────────────────────────────────────────────
function getNodeStatus(scene, currentIndex, sceneIndex) {
  if (scene.is_ending) return 'ending'
  if (currentIndex === -1) return sceneIndex === 0 ? 'current' : 'upcoming'
  if (sceneIndex < currentIndex) return 'visited'
  if (sceneIndex === currentIndex) return 'current'
  return 'upcoming'
}

// ─── Color styles per status ────────────────────────────────────────────────
const STATUS_COLORS = {
  start: {
    stroke: '#C4AD88',
    fill: '#1B2228',
    glow: 'rgba(196, 173, 136, 0.4)',
    text: '#C4AD88',
    badge: 'Origin · 起',
    badgeCls: 'border-[#C4AD88]/50 bg-[#C4AD88]/15 text-[#C4AD88]',
  },
  current: {
    stroke: '#A33B42',
    fill: '#1E1418',
    glow: 'rgba(163, 59, 66, 0.7)',
    text: '#F1EEE8',
    badge: 'Current Position · 現',
    badgeCls: 'border-[#A33B42]/60 bg-[#A33B42]/20 text-[#F1EEE8]',
  },
  visited: {
    stroke: '#C4AD88',
    fill: '#14191E',
    glow: 'rgba(196, 173, 136, 0.2)',
    text: '#D7DCE0',
    badge: 'Traversed · 過',
    badgeCls: 'border-[#C4AD88]/30 bg-[#C4AD88]/10 text-[#C4AD88]',
  },
  ending: {
    stroke: '#C4AD88',
    fill: '#201618',
    glow: 'rgba(196, 173, 136, 0.5)',
    text: '#F1EEE8',
    badge: 'Narrative Climax · 結',
    badgeCls: 'border-[#C4AD88]/50 bg-[#C4AD88]/15 text-[#C4AD88]',
  },
  upcoming: {
    stroke: 'rgba(255, 255, 255, 0.15)',
    fill: '#101317',
    glow: 'transparent',
    text: '#858A8D',
    badge: 'Uncharted · 未',
    badgeCls: 'border-white/10 bg-white/5 text-[#5A5F63]',
  },
}

export default function StoryGraphModal({
  isOpen,
  onClose,
  scenes = [],
  currentSceneId,
  storyId,
  storyTitle = '',
}) {
  const [selectedScene, setSelectedScene] = useState(null)
  const [choicesMap, setChoicesMap] = useState({})
  const [loadingChoices, setLoadingChoices] = useState(false)

  // Pan & Zoom state
  const [zoom, setZoom] = useState(1)
  const [pan, setPan] = useState({ x: 0, y: 0 })
  const [isDragging, setIsDragging] = useState(false)
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 })

  const svgContainerRef = useRef(null)

  // Sort scenes by scene_number
  const sortedScenes = useMemo(
    () => [...scenes].sort((a, b) => (a.scene_number || 0) - (b.scene_number || 0)),
    [scenes]
  )

  const currentIndex = useMemo(
    () => sortedScenes.findIndex((s) => String(s.id) === String(currentSceneId)),
    [sortedScenes, currentSceneId]
  )

  // Load choices for all scenes when modal opens
  useEffect(() => {
    if (!isOpen || !storyId || !sortedScenes.length) return
    let active = true
    setLoadingChoices(true)

    async function fetchAllChoices() {
      try {
        const results = await Promise.all(
          sortedScenes.map(async (sc) => {
            try {
              const res = await choicesApi.list(storyId, sc.id)
              const list = Array.isArray(res) ? res : Array.isArray(res?.items) ? res.items : []
              return { sceneId: sc.id, choices: list }
            } catch {
              return { sceneId: sc.id, choices: [] }
            }
          })
        )
        if (active) {
          const map = {}
          results.forEach(({ sceneId, choices }) => {
            map[sceneId] = choices
          })
          setChoicesMap(map)
        }
      } finally {
        if (active) setLoadingChoices(false)
      }
    }

    fetchAllChoices()
    return () => {
      active = false
    }
  }, [isOpen, storyId, sortedScenes])

  // Select current scene by default when opened
  useEffect(() => {
    if (isOpen && sortedScenes.length && !selectedScene) {
      const active = sortedScenes.find((s) => String(s.id) === String(currentSceneId))
      setSelectedScene(active || sortedScenes[0])
    }
  }, [isOpen, sortedScenes, currentSceneId, selectedScene])

  // ─── Layout calculation ──────────────────────────────────────────────────
  // Compute positions for each node in a horizontal flowing ink graph
  const { nodePositions, edges, canvasWidth, canvasHeight } = useMemo(() => {
    if (!sortedScenes.length) {
      return { nodePositions: {}, edges: [], canvasWidth: 800, canvasHeight: 400 }
    }

    const positions = {}
    const computedEdges = []

    // Horizontal spacing parameters
    const nodeWidth = 240
    const nodeHeight = 84
    const horizontalGap = 130
    const startX = 80
    const centerY = 240

    // Assign positions based on scene index with alternate vertical staggering for branches
    sortedScenes.forEach((sc, idx) => {
      const x = startX + idx * (nodeWidth + horizontalGap)
      // Slight atmospheric wave for narrative topography
      const wave = Math.sin(idx * 0.8) * 35
      const y = centerY + wave

      positions[sc.id] = {
        x,
        y,
        width: nodeWidth,
        height: nodeHeight,
        scene: sc,
        index: idx,
      }
    })

    // Compute edges based on actual choices where available, or sequential transitions
    sortedScenes.forEach((sc, idx) => {
      const choices = choicesMap[sc.id] || []
      const explicitBranches = choices.filter((c) => c.next_scene_id && positions[c.next_scene_id])

      if (explicitBranches.length > 0) {
        explicitBranches.forEach((ch) => {
          computedEdges.push({
            id: `edge-${sc.id}-${ch.next_scene_id}-${ch.id}`,
            from: positions[sc.id],
            to: positions[ch.next_scene_id],
            label: ch.choice_text,
            isTraversed: idx < currentIndex,
            isCurrent: idx === currentIndex,
          })
        })
      } else if (idx < sortedScenes.length - 1) {
        // Linear fallback connection between verified sequential scenes
        const nextScene = sortedScenes[idx + 1]
        if (positions[nextScene.id]) {
          computedEdges.push({
            id: `edge-${sc.id}-${nextScene.id}`,
            from: positions[sc.id],
            to: positions[nextScene.id],
            label: null,
            isTraversed: idx < currentIndex,
            isCurrent: idx === currentIndex,
          })
        }
      }
    })

    const totalWidth = Math.max(900, startX + sortedScenes.length * (nodeWidth + horizontalGap) + 120)
    const totalHeight = 480

    return {
      nodePositions: positions,
      edges: computedEdges,
      canvasWidth: totalWidth,
      canvasHeight: totalHeight,
    }
  }, [sortedScenes, choicesMap, currentIndex])

  // Center pan on the current active node
  const focusOnCurrentNode = useCallback(() => {
    const activePos = currentSceneId ? nodePositions[currentSceneId] : null
    if (activePos && svgContainerRef.current) {
      const containerWidth = svgContainerRef.current.clientWidth || 800
      const containerHeight = svgContainerRef.current.clientHeight || 450
      setPan({
        x: containerWidth / 2 - (activePos.x + activePos.width / 2) * zoom,
        y: containerHeight / 2 - (activePos.y + activePos.height / 2) * zoom,
      })
    }
  }, [currentSceneId, nodePositions, zoom])

  // Reset view to origin
  const handleResetView = useCallback(() => {
    setZoom(1)
    setPan({ x: 40, y: 0 })
  }, [])

  // Zoom controls
  const handleZoomIn = () => setZoom((z) => Math.min(2.0, Number((z + 0.2).toFixed(2))))
  const handleZoomOut = () => setZoom((z) => Math.max(0.4, Number((z - 0.2).toFixed(2))))

  // Mouse pan event handlers
  const handleMouseDown = (e) => {
    // Only pan if left clicked directly on canvas background
    if (e.button !== 0) return
    setIsDragging(true)
    setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y })
  }

  const handleMouseMove = (e) => {
    if (!isDragging) return
    setPan({
      x: e.clientX - dragStart.x,
      y: e.clientY - dragStart.y,
    })
  }

  const handleMouseUp = () => setIsDragging(false)

  // Touch pan event handlers for mobile
  const handleTouchStart = (e) => {
    if (e.touches.length === 1) {
      setIsDragging(true)
      setDragStart({
        x: e.touches[0].clientX - pan.x,
        y: e.touches[0].clientY - pan.y,
      })
    }
  }

  const handleTouchMove = (e) => {
    if (!isDragging || e.touches.length !== 1) return
    setPan({
      x: e.touches[0].clientX - dragStart.x,
      y: e.touches[0].clientY - dragStart.y,
    })
  }

  const handleTouchEnd = () => setIsDragging(false)

  if (!isOpen) return null

  // Stats
  const visitedCount = currentIndex !== -1 ? currentIndex + 1 : 1
  const totalNodes = sortedScenes.length
  const branchCount = Object.values(choicesMap).reduce((acc, list) => acc + (list?.length || 0), 0)

  // Selected node details
  const selectedChoices = selectedScene ? choicesMap[selectedScene.id] || [] : []
  const selectedIndex = selectedScene
    ? sortedScenes.findIndex((s) => String(s.id) === String(selectedScene.id))
    : -1
  const selectedStatus = selectedScene
    ? selectedIndex === 0
      ? 'start'
      : getNodeStatus(selectedScene, currentIndex, selectedIndex)
    : 'upcoming'
  const selectedStatusCfg = STATUS_COLORS[selectedStatus]

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-2 sm:p-5">
      {/* Dark Ambient Backdrop */}
      <div onClick={onClose} className="fixed inset-0 bg-black/85 backdrop-blur-md" />

      {/* Main Modal Window */}
      <div className="relative z-10 flex flex-col w-full max-w-6xl h-[92vh] rounded-2xl overflow-hidden border border-white/[0.08] bg-[#101317] text-[#F1EEE8] shadow-2xl">
        {/* Top Gold Horizon Accent */}
        <div className="h-px w-full bg-gradient-to-r from-transparent via-[#C4AD88]/40 to-transparent" />

        {/* ─────────────── HEADER ─────────────── */}
        <div className="shrink-0 px-6 py-4 bg-[#101317] border-b border-white/[0.07] flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            {/* Japanese Seal Emblem */}
            <div className="relative shrink-0">
              <div className="flex h-11 w-11 items-center justify-center rounded-full border border-[#C4AD88]/30 bg-[#1B2228] shadow-inner">
                <span className="font-cinematic text-lg text-[#C4AD88]" style={{ fontFamily: 'serif' }}>
                  岐
                </span>
              </div>
              <div className="absolute inset-0 rounded-full border border-[#C4AD88]/10 scale-110" />
            </div>

            <div>
              <div className="flex items-center gap-2 mb-0.5">
                <p className="text-[9px] font-mono uppercase tracking-[0.3em] text-[#858A8D]">
                  BRANCHING NARRATIVE MAP · 運命の糸
                </p>
                {storyTitle && (
                  <>
                    <span className="text-[9px] text-[#5A5F63]">·</span>
                    <span className="text-[9px] font-mono text-[#C4AD88] tracking-wider truncate max-w-xs">
                      {storyTitle}
                    </span>
                  </>
                )}
              </div>
              <h2 className="font-cinematic text-2xl font-semibold tracking-wide text-[#F1EEE8]">
                The Threads of Fate
              </h2>
              <p className="text-[11px] text-[#858A8D] font-mono">
                Every path begins with a choice.
              </p>
            </div>
          </div>

          {/* Stats & Legend Pills */}
          <div className="hidden lg:flex items-center gap-3 text-[10px] font-mono">
            <div className="flex items-center gap-1.5 rounded-full border border-[#A33B42]/40 bg-[#1B2228] px-3 py-1 text-[#F1EEE8]">
              <span className="h-2 w-2 rounded-full bg-[#A33B42] animate-ping" />
              <span>Current Scene</span>
            </div>
            <div className="flex items-center gap-1.5 rounded-full border border-[#C4AD88]/30 bg-[#1B2228] px-3 py-1 text-[#C4AD88]">
              <span className="h-1.5 w-1.5 rounded-full bg-[#C4AD88]" />
              <span>{visitedCount}/{totalNodes} Nodes Traversed</span>
            </div>
            {branchCount > 0 && (
              <div className="flex items-center gap-1.5 rounded-full border border-white/10 bg-[#1B2228] px-3 py-1 text-[#858A8D]">
                <span>{branchCount} Branch Choices</span>
              </div>
            )}
          </div>

          {/* Close button */}
          <button
            onClick={onClose}
            className="shrink-0 rounded-lg border border-white/10 p-2 text-[#858A8D] hover:border-white/20 hover:text-[#F1EEE8] transition"
            aria-label="Close Story Graph"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* ─────────────── GRAPH WORKSPACE ─────────────── */}
        <div className="relative flex-1 overflow-hidden bg-[#0C0F12]">
          {/* Subtle Japanese ink grid lines */}
          <div
            className="absolute inset-0 opacity-[0.03] pointer-events-none"
            style={{
              backgroundImage:
                'radial-gradient(circle at 1px 1px, #C4AD88 1px, transparent 0)',
              backgroundSize: '24px 24px',
            }}
          />

          {/* Floating Graph Tool Bar (Zoom & Pan Controls) */}
          <div className="absolute top-4 left-4 z-20 flex items-center gap-1.5 rounded-xl border border-white/10 bg-[#101317]/90 backdrop-blur-md p-1.5 shadow-xl">
            {/* Zoom In */}
            <button
              type="button"
              onClick={handleZoomIn}
              className="flex h-8 w-8 items-center justify-center rounded-lg border border-white/5 text-[#D7DCE0] hover:border-[#C4AD88]/50 hover:bg-[#1B2228] hover:text-[#C4AD88] transition text-sm font-mono"
              title="Zoom In (+)"
            >
              +
            </button>

            {/* Zoom Out */}
            <button
              type="button"
              onClick={handleZoomOut}
              className="flex h-8 w-8 items-center justify-center rounded-lg border border-white/5 text-[#D7DCE0] hover:border-[#C4AD88]/50 hover:bg-[#1B2228] hover:text-[#C4AD88] transition text-sm font-mono"
              title="Zoom Out (-)"
            >
              −
            </button>

            {/* Zoom Scale Display */}
            <span className="px-2 text-[10px] font-mono text-[#858A8D] select-none">
              {Math.round(zoom * 100)}%
            </span>

            {/* Divider */}
            <div className="h-4 w-px bg-white/10 mx-0.5" />

            {/* Center / Focus on Current Node */}
            <button
              type="button"
              onClick={focusOnCurrentNode}
              className="flex h-8 w-8 items-center justify-center rounded-lg border border-white/5 text-[#D7DCE0] hover:border-[#A33B42]/50 hover:bg-[#1B2228] hover:text-[#A33B42] transition"
              title="Focus on Current Scene"
            >
              <span className="text-xs">◎</span>
            </button>

            {/* Reset View */}
            <button
              type="button"
              onClick={handleResetView}
              className="flex h-8 w-8 items-center justify-center rounded-lg border border-white/5 text-[#D7DCE0] hover:border-[#C4AD88]/50 hover:bg-[#1B2228] hover:text-[#C4AD88] transition"
              title="Reset View"
            >
              <span className="text-xs">↺</span>
            </button>
          </div>

          {/* Interactive Graph Canvas */}
          <div
            ref={svgContainerRef}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onTouchStart={handleTouchStart}
            onTouchMove={handleTouchMove}
            onTouchEnd={handleTouchEnd}
            className={`w-full h-full select-none ${
              isDragging ? 'cursor-grabbing' : 'cursor-grab'
            }`}
          >
            <svg
              width="100%"
              height="100%"
              className="overflow-visible"
              style={{
                transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
                transformOrigin: '0 0',
                transition: isDragging ? 'none' : 'transform 0.15s ease-out',
              }}
            >
              <defs>
                {/* Arrow markers */}
                <marker
                  id="arrow-traversed"
                  viewBox="0 0 10 10"
                  refX="6"
                  refY="5"
                  markerWidth="6"
                  markerHeight="6"
                  orient="auto-start-reverse"
                >
                  <path d="M 0 1 L 8 5 L 0 9 z" fill="#C4AD88" />
                </marker>
                <marker
                  id="arrow-muted"
                  viewBox="0 0 10 10"
                  refX="6"
                  refY="5"
                  markerWidth="6"
                  markerHeight="6"
                  orient="auto-start-reverse"
                >
                  <path d="M 0 1 L 8 5 L 0 9 z" fill="rgba(255, 255, 255, 0.2)" />
                </marker>

                {/* Glow filter */}
                <filter id="glow-crimson" x="-20%" y="-20%" width="140%" height="140%">
                  <feGaussianBlur stdDeviation="4" result="blur" />
                  <feComposite in="SourceGraphic" in2="blur" operator="over" />
                </filter>
              </defs>

              {/* ─── 1. RENDER EDGES (BEZIER PATHS) ─── */}
              {edges.map((edge) => {
                const startX = edge.from.x + edge.from.width
                const startY = edge.from.y + edge.from.height / 2
                const endX = edge.to.x
                const endY = edge.to.y + edge.to.height / 2

                const dx = (endX - startX) * 0.5
                const pathD = `M ${startX} ${startY} C ${startX + dx} ${startY}, ${endX - dx} ${endY}, ${endX} ${endY}`

                const isTraversed = edge.isTraversed
                const isCurrent = edge.isCurrent

                return (
                  <g key={edge.id} className="transition-all">
                    {/* Background wider hit path */}
                    <path
                      d={pathD}
                      fill="none"
                      stroke={
                        isCurrent
                          ? '#A33B42'
                          : isTraversed
                          ? '#C4AD88'
                          : 'rgba(255, 255, 255, 0.15)'
                      }
                      strokeWidth={isCurrent ? 2.5 : isTraversed ? 2 : 1.2}
                      strokeDasharray={isTraversed || isCurrent ? 'none' : '4 4'}
                      markerEnd={isTraversed ? 'url(#arrow-traversed)' : 'url(#arrow-muted)'}
                      className="transition-all"
                    />

                    {/* Choice label on edge if available */}
                    {edge.label && (
                      <g
                        transform={`translate(${(startX + endX) / 2}, ${(startY + endY) / 2 - 12})`}
                      >
                        <rect
                          x={-Math.min(90, edge.label.length * 3.5)}
                          y="-10"
                          width={Math.min(180, edge.label.length * 7)}
                          height="18"
                          rx="4"
                          fill="#101317"
                          stroke={isTraversed ? 'rgba(196, 173, 136, 0.4)' : 'rgba(255, 255, 255, 0.1)'}
                          strokeWidth="1"
                        />
                        <text
                          textAnchor="middle"
                          fill={isTraversed ? '#C4AD88' : '#858A8D'}
                          fontSize="9"
                          fontFamily="monospace"
                          dy="2"
                        >
                          {edge.label.length > 24 ? edge.label.slice(0, 24) + '…' : edge.label}
                        </text>
                      </g>
                    )}
                  </g>
                )
              })}

              {/* ─── 2. RENDER NODES ─── */}
              {Object.values(nodePositions).map((pos) => {
                const sc = pos.scene
                const idx = pos.index
                const isCurrent = String(sc.id) === String(currentSceneId)
                const isSelected = selectedScene && String(selectedScene.id) === String(sc.id)
                const status = idx === 0 ? 'start' : getNodeStatus(sc, currentIndex, idx)
                const cfg = STATUS_COLORS[status]

                return (
                  <g
                    key={sc.id}
                    transform={`translate(${pos.x}, ${pos.y})`}
                    onClick={(e) => {
                      e.stopPropagation()
                      setSelectedScene(sc)
                    }}
                    className="cursor-pointer group"
                  >
                    {/* Node Aura Glow for Current Scene */}
                    {isCurrent && (
                      <rect
                        x="-4"
                        y="-4"
                        width={pos.width + 8}
                        height={pos.height + 8}
                        rx="16"
                        fill="none"
                        stroke="#A33B42"
                        strokeWidth="2"
                        opacity="0.4"
                        className="animate-pulse"
                      />
                    )}

                    {/* Node Container Card */}
                    <rect
                      x="0"
                      y="0"
                      width={pos.width}
                      height={pos.height}
                      rx="12"
                      fill={cfg.fill}
                      stroke={
                        isSelected
                          ? '#F1EEE8'
                          : isCurrent
                          ? '#A33B42'
                          : cfg.stroke
                      }
                      strokeWidth={isSelected ? 2 : isCurrent ? 2 : 1}
                      filter={isCurrent ? 'url(#glow-crimson)' : 'none'}
                      className="transition-all duration-200"
                    />

                    {/* Number Badge Pill */}
                    <g transform="translate(14, 16)">
                      <circle
                        cx="12"
                        cy="12"
                        r="12"
                        fill={isCurrent ? '#A33B42' : 'rgba(255, 255, 255, 0.05)'}
                        stroke={cfg.stroke}
                        strokeWidth="1"
                      />
                      <text
                        x="12"
                        y="16"
                        textAnchor="middle"
                        fill={isCurrent ? '#F1EEE8' : cfg.text}
                        fontSize="11"
                        fontFamily="monospace"
                        fontWeight="bold"
                      >
                        {String(idx + 1).padStart(2, '0')}
                      </text>
                    </g>

                    {/* Location Title */}
                    <text
                      x="46"
                      y="26"
                      fill="#F1EEE8"
                      fontSize="14"
                      fontFamily="Cormorant Garamond, serif"
                      fontWeight="600"
                    >
                      {sc.location.length > 20 ? sc.location.slice(0, 19) + '…' : sc.location}
                    </text>

                    {/* Mood / Status Subtitle */}
                    <text
                      x="46"
                      y="42"
                      fill="#858A8D"
                      fontSize="10"
                      fontFamily="monospace"
                    >
                      {sc.mood ? sc.mood.slice(0, 24) : 'Quiet mist'}
                    </text>

                    {/* Status Pill Tag */}
                    <g transform={`translate(${pos.width - 75}, 54)`}>
                      <rect
                        x="0"
                        y="0"
                        width="65"
                        height="18"
                        rx="9"
                        fill={isCurrent ? 'rgba(163, 59, 66, 0.25)' : 'rgba(255, 255, 255, 0.05)'}
                        stroke={cfg.stroke}
                        strokeWidth="0.8"
                      />
                      <text
                        x="32"
                        y="12"
                        textAnchor="middle"
                        fill={cfg.text}
                        fontSize="9"
                        fontFamily="sans-serif"
                        fontWeight="bold"
                      >
                        {sc.is_ending ? 'Ending ✦' : isCurrent ? 'Active' : idx === 0 ? 'Start' : 'Passed'}
                      </text>
                    </g>
                  </g>
                )
              })}
            </svg>
          </div>

          {/* ─────────────── CONTEXTUAL NODE DETAILS PANEL (DRAWER) ─────────────── */}
          {selectedScene && (
            <div className="absolute right-4 top-4 bottom-4 z-30 w-80 sm:w-96 rounded-2xl border border-white/10 bg-[#14191E]/95 backdrop-blur-xl p-5 shadow-2xl flex flex-col justify-between overflow-y-auto animate-in slide-in-from-right duration-200">
              <div className="space-y-4">
                {/* Panel Header */}
                <div className="flex items-start justify-between border-b border-white/[0.08] pb-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs text-[#C4AD88]">
                        Node #{String(selectedIndex + 1).padStart(2, '0')}
                      </span>
                      <span className={`rounded-full border px-2 py-0.5 text-[9px] font-semibold uppercase ${selectedStatusCfg.badgeCls}`}>
                        {selectedStatusCfg.badge}
                      </span>
                    </div>
                    <h3 className="font-cinematic text-2xl font-semibold text-[#F1EEE8] mt-1">
                      {selectedScene.location}
                    </h3>
                  </div>

                  <button
                    onClick={() => setSelectedScene(null)}
                    className="rounded-lg border border-white/10 p-1.5 text-[#858A8D] hover:text-[#F1EEE8] hover:border-white/20 transition"
                  >
                    <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>

                {/* Mood Tag */}
                <div className="rounded-lg border border-white/5 bg-[#1B2228]/60 p-3">
                  <span className="text-[10px] uppercase font-mono tracking-wider text-[#858A8D] block">
                    Scene Atmosphere
                  </span>
                  <p className="font-cinematic text-base italic text-[#C4AD88] mt-0.5">
                    {selectedScene.mood || 'Veiled and solemn'}
                  </p>
                </div>

                {/* Narrative Excerpt */}
                {selectedScene.content && (
                  <div>
                    <span className="text-[10px] uppercase font-mono tracking-wider text-[#858A8D] block mb-1">
                      Narrative Fragment
                    </span>
                    <p className="font-cinematic text-sm leading-relaxed text-[#D7DCE0]/80 italic bg-[#101317]/50 rounded-lg p-3 border border-white/5 max-h-36 overflow-y-auto">
                      “{selectedScene.content}”
                    </p>
                  </div>
                )}

                {/* Haiku Callout */}
                {selectedScene.haiku && (
                  <div className="border-l-2 border-[#C4AD88]/50 pl-3 py-1">
                    <span className="text-[9px] uppercase font-mono tracking-widest text-[#C4AD88] block mb-0.5">
                      俳句 · Reflection
                    </span>
                    <p className="font-cinematic italic text-xs text-[#C4AD88]/90 whitespace-pre-line leading-relaxed">
                      {selectedScene.haiku}
                    </p>
                  </div>
                )}

                {/* Branching Options Stemming From Here */}
                <div className="pt-2">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[10px] uppercase font-mono tracking-wider text-[#858A8D]">
                      Diverging Choices ({selectedChoices.length})
                    </span>
                    {loadingChoices && (
                      <span className="text-[9px] text-[#C4AD88] animate-pulse">Reading fate...</span>
                    )}
                  </div>

                  {selectedChoices.length === 0 ? (
                    <p className="text-xs text-[#5A5F63] font-mono italic">
                      {selectedScene.is_ending
                        ? 'This path reaches the end of the chronicle.'
                        : 'Single forward path through the sanctuary.'}
                    </p>
                  ) : (
                    <div className="space-y-2 max-h-44 overflow-y-auto pr-1">
                      {selectedChoices.map((ch, idx) => (
                        <div
                          key={ch.id || idx}
                          className="rounded-lg border border-white/10 bg-[#1B2228]/80 p-2.5 text-left text-xs transition hover:border-[#C4AD88]/40"
                        >
                          <div className="flex items-start gap-2">
                            <span className="text-[#C4AD88] font-mono mt-0.5 shrink-0">
                              {idx + 1}›
                            </span>
                            <span className="font-cinematic text-sm text-[#F1EEE8]">
                              {ch.choice_text}
                            </span>
                          </div>
                          {ch.next_scene_id && (
                            <span className="block mt-1 text-[9px] font-mono text-[#858A8D]">
                              Leads to Node #{ch.next_scene_id}
                            </span>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Panel Footer Action */}
              <div className="mt-4 pt-3 border-t border-white/[0.08] flex items-center justify-between text-[11px] font-mono text-[#858A8D]">
                <span>Status: {selectedStatus.toUpperCase()}</span>
                <button
                  type="button"
                  onClick={() => setSelectedScene(null)}
                  className="rounded border border-white/10 px-3 py-1 text-xs text-[#F1EEE8] hover:bg-white/5 transition"
                >
                  Dismiss
                </button>
              </div>
            </div>
          )}
        </div>

        {/* ─────────────── FOOTER ─────────────── */}
        <div className="shrink-0 flex items-center justify-between border-t border-white/[0.07] bg-[#101317] px-6 py-3.5">
          <div className="flex items-center gap-2 text-[10px] text-[#5A5F63] font-mono">
            <span className="font-cinematic text-sm text-[#C4AD88]/50" style={{ fontFamily: 'serif' }}>
              糸
            </span>
            <span>
              Pan: Click and drag canvas · Zoom: Controls top-left or mousewheel
            </span>
          </div>

          <button
            onClick={onClose}
            className="rounded-lg border border-white/10 bg-[#1B2228] px-5 py-2 text-xs font-semibold text-[#F1EEE8] hover:border-white/20 transition"
          >
            Close Graph
          </button>
        </div>
      </div>
    </div>
  )
}
