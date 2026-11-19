import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { storiesApi, scenesApi, choicesApi, stateApi, actionApi } from '../api/client'
import { useToast } from '../context/ToastContext'

import CharacterDossierModal from '../components/character/CharacterDossierModal'
import MemoriesModal from '../components/memory/MemoriesModal'
import TimelineModal from '../components/story/TimelineModal'
import WorldStateModal from '../components/world/WorldStateModal'
import StoryGraphModal from '../components/graph/StoryGraphModal'
import InGameMenuModal from '../components/story/InGameMenuModal'
import EndingScreen from '../components/story/EndingScreen'

function getList(data) {
  if (Array.isArray(data)) return data
  if (Array.isArray(data?.items)) return data.items
  return []
}

function getSceneBackground(location = '') {
  const loc = location.toLowerCase()
  if (loc.includes('station') || loc.includes('platform')) return '/assets/backgrounds/landing-hero.png'
  if (loc.includes('shrine') || loc.includes('torii') || loc.includes('rain')) return '/assets/backgrounds/rain-soaked-shrine.png'
  if (loc.includes('village') || loc.includes('street') || loc.includes('crossing')) return '/assets/backgrounds/village-street-night.png'
  if (loc.includes('bamboo')) return '/assets/story-covers/cover-bamboo-forest.png'
  if (loc.includes('room') || loc.includes('chamber') || loc.includes('lantern') || loc.includes('letter')) return '/assets/backgrounds/midnight-engawa.png'
  return '/assets/backgrounds/mayoiga-estate-night.png'
}

/**
 * Parses raw scene content to cleanly separate dialogue from narration if present.
 */
function parseSceneContent(content = '') {
  if (!content) return { dialogue: null, narration: '' }

  // Check for lines with "Name: Dialogue" format
  const lines = content.split('\n')
  let speaker = null
  let dialogueText = null
  const narrationLines = []

  for (const line of lines) {
    const trimmed = line.trim()
    const match = trimmed.match(/^([A-Z][a-zA-Z\s]{1,20}):\s*["“']?(.*?)["”']?$/)
    if (match && !speaker) {
      speaker = match[1]
      dialogueText = match[2]
    } else {
      narrationLines.push(line)
    }
  }

  // If no explicit "Name: Dialogue" but contains quotes "..."
  if (!speaker) {
    const quoteMatch = content.match(/["“]([^"”]+)["”]/)
    if (quoteMatch) {
      dialogueText = quoteMatch[1]
    }
  }

  return {
    speaker,
    dialogue: dialogueText,
    narration: narrationLines.join('\n').trim() || content,
  }
}

export default function StoryReaderPage() {
  const { storyId } = useParams()
  const { showToast } = useToast()

  const [story, setStory] = useState(null)
  const [scenes, setScenes] = useState([])
  const [choices, setChoices] = useState([])
  const [runtime, setRuntime] = useState(null)
  const [currentSceneId, setCurrentSceneId] = useState(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  // Modal states for the 5 story tools + in-game menu
  const [characterModalOpen, setCharacterModalOpen] = useState(false)
  const [memoriesModalOpen, setMemoriesModalOpen] = useState(false)
  const [timelineModalOpen, setTimelineModalOpen] = useState(false)
  const [worldModalOpen, setWorldModalOpen] = useState(false)
  const [graphModalOpen, setGraphModalOpen] = useState(false)
  const [menuModalOpen, setMenuModalOpen] = useState(false)

  const currentScene = scenes.find(
    (scene) => String(scene.id) === String(currentSceneId)
  )

  const loadStory = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [storyData, sceneData] = await Promise.all([
        storiesApi.get(storyId),
        scenesApi.list(storyId),
      ])
      const sceneList = getList(sceneData)
      setStory(storyData)
      setScenes(sceneList)

      const state = await stateApi.get(storyId)
      setRuntime(state)
      setCurrentSceneId(
        state.current_scene_id || sceneList[0]?.id || null
      )
    } catch (err) {
      setError(err.message || 'Unable to open this story.')
    } finally {
      setLoading(false)
    }
  }, [storyId])

  useEffect(() => {
    loadStory()
  }, [loadStory])

  useEffect(() => {
    let active = true

    async function loadChoices() {
      if (!currentSceneId) {
        setChoices([])
        return
      }
      try {
        const data = await choicesApi.list(storyId, currentSceneId)
        if (active) setChoices(getList(data))
      } catch (err) {
        if (active) {
          setChoices([])
          showToast(err.message || 'Unable to load choices.', 'error')
        }
      }
    }

    loadChoices()
    return () => { active = false }
  }, [storyId, currentSceneId, showToast])

  async function followChoice(choice) {
    if (busy) return
    setBusy(true)
    try {
      const result = await actionApi.submitChoice(storyId, {
        choice_id: choice.id,
      })

      const [state, sceneData] = await Promise.all([
        stateApi.get(storyId),
        scenesApi.list(storyId),
      ])

      setRuntime(state)
      setScenes(getList(sceneData))
      setCurrentSceneId(
        result.current_scene_id || state.current_scene_id
      )
      showToast('Your choice has shaped the story.', 'success')
    } catch (err) {
      showToast(err.message || 'Unable to apply this choice.', 'error')
    } finally {
      setBusy(false)
    }
  }

  function handleQuickSave() {
    showToast('Chronicle progress saved.', 'success')
  }

  if (loading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#101317] text-[#858A8D]">
        <div className="flex flex-col items-center gap-4">
          <div className="h-3 w-3 rounded-full bg-[#A33B42] animate-ping" />
          <p className="font-cinematic text-lg text-[#F1EEE8]">Unfolding the manuscript...</p>
        </div>
      </main>
    )
  }

  if (error) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#101317] px-6 text-[#F1EEE8]">
        <div className="max-w-md rounded-2xl border border-white/10 bg-[#171C21] p-8 text-center shadow-2xl">
          <p className="text-sm text-[#A33B42] font-semibold">{error}</p>
          <div className="mt-6 flex justify-center gap-4">
            <button
              onClick={loadStory}
              className="rounded-lg bg-[#A33B42] px-5 py-2 text-xs font-semibold text-white hover:bg-[#702B34] transition"
            >
              Try Again
            </button>
            <Link
              to="/dashboard"
              className="rounded-lg border border-white/10 px-5 py-2 text-xs text-[#858A8D] hover:text-white transition"
            >
              Return to Archive
            </Link>
          </div>
        </div>
      </main>
    )
  }

  const { speaker, dialogue, narration } = parseSceneContent(currentScene?.content)
  const isEnding = Boolean(currentScene?.is_ending)

  return (
    <div className="relative min-h-screen w-full bg-[#101317] text-[#F1EEE8] font-sans selection:bg-[#A33B42] selection:text-white overflow-x-hidden">
      {/* ─────────────────────────────────────────────────────────────
          1. FULLSCREEN CINEMATIC ENVIRONMENTAL BACKGROUND
      ───────────────────────────────────────────────────────────── */}
      <div
        className="fixed inset-0 bg-cover bg-center bg-no-repeat transition-all duration-1000 scale-105 filter brightness-90 contrast-120"
        style={{
          backgroundImage: `url('${getSceneBackground(currentScene?.location)}')`,
        }}
      />

      {/* Layered Cinematic Darkness, Moonlight Mist & Vignette */}
      <div className="fixed inset-0 bg-gradient-to-t from-[#101317] via-[#101317]/40 to-transparent pointer-events-none" />
      <div className="fixed inset-0 bg-[radial-gradient(circle_at_center,transparent_35%,#101317_90%)] pointer-events-none" />

      {/* ─────────────────────────────────────────────────────────────
          2. TOP BAR
      ───────────────────────────────────────────────────────────── */}
      <header className="fixed top-0 left-0 right-0 z-40 border-b border-white/[0.08] bg-[#101317]/85 backdrop-blur-md">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-3.5">
          {/* Left: Back to Library */}
          <Link
            to="/dashboard"
            className="group flex items-center gap-3 text-xs text-[#B5B2AC] hover:text-[#C4AD88] transition"
          >
            <span className="flex h-7 w-7 items-center justify-center rounded border border-[#C4AD88]/30 bg-[#1B2228] text-[#C4AD88] group-hover:border-[#C4AD88]">
              ←
            </span>
            <div className="hidden sm:block">
              <span className="font-cinematic text-sm font-semibold tracking-wider text-[#F1EEE8] block group-hover:text-[#C4AD88]">
                YŪGEN MAYOIGA
              </span>
              <span className="text-[9px] uppercase tracking-widest text-[#858A8D] block font-mono">
                Return to Archive
              </span>
            </div>
          </Link>

          {/* Center: Story Title & Chapter Indicator */}
          <div className="text-center px-4">
            <h1 className="font-cinematic text-base sm:text-lg font-semibold tracking-wide text-[#F1EEE8] truncate max-w-xs sm:max-w-md">
              {story?.title}
            </h1>
            <span className="text-[10px] uppercase font-mono tracking-widest text-[#C4AD88]">
              {currentScene?.location || 'Sanctuary Interior'}
            </span>
          </div>

          {/* Right: Quick Save & Menu */}
          <div className="flex items-center gap-2.5">
            <button
              onClick={handleQuickSave}
              className="flex items-center gap-1.5 rounded-lg border border-white/10 bg-[#1B2228]/80 px-3 py-1.5 text-xs text-[#D7DCE0] hover:border-[#C4AD88]/50 hover:text-[#F1EEE8] transition"
              title="Save current progress"
            >
              <span className="text-[11px] text-[#C4AD88]">💾</span>
              <span className="hidden sm:inline">Save</span>
            </button>

            <button
              onClick={() => setMenuModalOpen(true)}
              className="flex items-center gap-1.5 rounded-lg border border-white/10 bg-[#1B2228]/80 px-3 py-1.5 text-xs text-[#D7DCE0] hover:border-[#C4AD88]/50 hover:text-[#F1EEE8] transition"
            >
              <svg className="h-3.5 w-3.5 text-[#C4AD88]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
              <span className="hidden sm:inline">Menu</span>
            </button>
          </div>
        </div>
      </header>

      {/* ─────────────────────────────────────────────────────────────
          3. MAIN GAMEPLAY / NARRATIVE & CHOICE AREA
      ───────────────────────────────────────────────────────────── */}
      <main className="relative z-10 mx-auto max-w-7xl min-h-screen px-6 pt-24 pb-28 flex flex-col justify-center">
        {isEnding ? (
          <EndingScreen
            story={story}
            currentScene={currentScene}
            runtime={runtime}
            scenes={scenes}
            onOpenTimeline={() => setTimelineModalOpen(true)}
            onOpenGraph={() => setGraphModalOpen(true)}
            onOpenMemories={() => setMemoriesModalOpen(true)}
          />
        ) : (
          /* ───────────────────────────────────────────────
              ACTIVE SCENE GAMEPLAY VIEW (Screen 6)
          ─────────────────────────────────────────────── */
          <div className="grid gap-8 lg:grid-cols-12 items-start my-auto">
            {/* Left / Center Narrative Card (Col 1-7) */}
            <div className="lg:col-span-7 flex flex-col gap-6">
              <div className="rounded-2xl border border-white/10 bg-[#101317]/85 backdrop-blur-xl p-6 sm:p-9 shadow-2xl">
                {/* Scene Mood & Location Bar */}
                <div className="flex items-center justify-between border-b border-white/[0.08] pb-4 mb-6">
                  <div className="flex items-center gap-2">
                    <span className="h-2 w-2 rounded-full bg-[#A33B42] animate-pulse" />
                    <span className="font-mono text-xs uppercase tracking-widest text-[#C4AD88]">
                      {currentScene?.location || 'Sanctuary'}
                    </span>
                  </div>
                  <span className="text-[11px] font-mono text-[#858A8D]">
                    Mood · {currentScene?.mood || 'Subtle & Mysterious'}
                  </span>
                </div>

                {/* Speaker Tag & Dialogue (if separated) */}
                {dialogue && (
                  <div className="mb-6 rounded-xl border border-[#A33B42]/30 bg-[#1B2228]/80 p-5 shadow-inner">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="rounded bg-[#A33B42] px-2 py-0.5 text-[10px] font-semibold text-white uppercase tracking-wider">
                        {speaker || 'Aiko'}
                      </span>
                    </div>
                    <p className="font-cinematic text-xl sm:text-2xl italic leading-relaxed text-[#F1EEE8]">
                      “{dialogue}”
                    </p>
                  </div>
                )}

                {/* Main Narration Body */}
                <div className="font-cinematic text-lg sm:text-xl leading-relaxed text-[#D7DCE0] whitespace-pre-line space-y-4">
                  {narration}
                </div>

                {/* Authentic Haiku Callout (if available) */}
                {currentScene?.haiku && (
                  <div className="mt-8 border-l-2 border-[#C4AD88]/60 bg-[#171C21]/60 py-3 px-5 rounded-r-lg">
                    <span className="text-[9px] uppercase font-mono tracking-widest text-[#C4AD88] block mb-1">
                      Poetic Reflection · 俳句
                    </span>
                    <p className="font-cinematic italic text-sm text-[#C4AD88] leading-relaxed whitespace-pre-line">
                      {currentScene.haiku}
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* Right Choices Panel (Col 8-12) */}
            <div className="lg:col-span-5 flex flex-col gap-4">
              <div className="rounded-2xl border border-white/10 bg-[#101317]/85 backdrop-blur-xl p-6 sm:p-7 shadow-2xl">
                <div className="flex items-center justify-between border-b border-white/[0.08] pb-3 mb-5">
                  <div className="flex items-center gap-2">
                    <span className="text-[#C4AD88] font-cinematic text-base">✦</span>
                    <h3 className="font-cinematic text-xl font-semibold tracking-wide text-[#F1EEE8]">
                      What will you choose?
                    </h3>
                  </div>
                  <span className="text-[10px] uppercase font-mono tracking-wider text-[#858A8D]">
                    {choices.length} options
                  </span>
                </div>

                {/* Choices Buttons */}
                {choices.length ? (
                  <div className="space-y-3">
                    {choices.map((choice, index) => (
                      <button
                        key={choice.id}
                        disabled={busy}
                        onClick={() => followChoice(choice)}
                        className="group flex w-full items-start justify-between gap-4 rounded-xl border border-white/10 bg-[#1B2228]/80 p-4 sm:p-5 text-left transition-all hover:border-[#A33B42]/80 hover:bg-[#A33B42]/15 hover:shadow-[0_0_20px_rgba(163,59,66,0.2)] disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        <div className="flex items-start gap-3">
                          <span className="font-mono text-xs text-[#C4AD88] mt-1 shrink-0 group-hover:text-white transition">
                            {String(index + 1).padStart(2, '0')} ›
                          </span>
                          <span className="font-cinematic text-base sm:text-lg leading-relaxed text-[#F1EEE8] group-hover:text-white transition">
                            {choice.choice_text}
                          </span>
                        </div>
                        <span className="text-[#C4AD88] transition-transform duration-300 group-hover:translate-x-1 group-hover:text-[#F1EEE8] shrink-0 mt-1">
                          →
                        </span>
                      </button>
                    ))}
                  </div>
                ) : (
                  <div className="py-8 text-center text-xs text-[#858A8D]">
                    No paths diverge from here. The mist lies still.
                  </div>
                )}

                {/* Turn Advancement Status */}
                {busy && (
                  <div className="mt-4 flex items-center justify-center gap-2.5 rounded-lg border border-[#A33B42]/40 bg-[#A33B42]/10 py-2.5 px-4 text-xs text-[#F1EEE8] animate-pulse">
                    <div className="h-1.5 w-1.5 rounded-full bg-[#A33B42]" />
                    <span>The story is unfolding...</span>
                  </div>
                )}
              </div>

              {/* Compact Atmosphere Preview Tag */}
              <div className="rounded-xl border border-white/5 bg-[#101317]/60 p-4 flex items-center justify-between text-xs text-[#858A8D]">
                <div className="flex items-center gap-2">
                  <span className="text-[#C4AD88]">Turn {runtime?.turn_number ?? 1}</span>
                  <span>·</span>
                  <span>{scenes.length} Scenes Encountered</span>
                </div>
                <button
                  onClick={() => setWorldModalOpen(true)}
                  className="text-[#C4AD88] hover:underline text-[11px]"
                >
                  View State →
                </button>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* ─────────────────────────────────────────────────────────────
          4. BOTTOM NAVIGATION DOCK (STORY TOOLS)
      ───────────────────────────────────────────────────────────── */}
      <footer className="fixed bottom-0 left-0 right-0 z-40 border-t border-white/[0.08] bg-[#101317]/90 backdrop-blur-md">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-2.5">
          {/* 5 Bottom Navigation Tool Buttons */}
          <div className="flex items-center gap-2 sm:gap-6 overflow-x-auto w-full justify-center">
            {/* 1. Characters */}
            <button
              onClick={() => setCharacterModalOpen(true)}
              className="flex items-center gap-2 rounded-lg px-3 py-1.5 text-xs text-[#D7DCE0] hover:bg-white/5 hover:text-[#C4AD88] transition"
            >
              <svg className="h-4 w-4 text-[#C4AD88]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
              </svg>
              <span>Characters</span>
            </button>

            {/* 2. Memories */}
            <button
              onClick={() => setMemoriesModalOpen(true)}
              className="flex items-center gap-2 rounded-lg px-3 py-1.5 text-xs text-[#D7DCE0] hover:bg-white/5 hover:text-[#C4AD88] transition"
            >
              <svg className="h-4 w-4 text-[#A33B42]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
              </svg>
              <span>Memories</span>
            </button>

            {/* 3. Timeline */}
            <button
              onClick={() => setTimelineModalOpen(true)}
              className="flex items-center gap-2 rounded-lg px-3 py-1.5 text-xs text-[#D7DCE0] hover:bg-white/5 hover:text-[#C4AD88] transition"
            >
              <svg className="h-4 w-4 text-[#C4AD88]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span>Timeline</span>
            </button>

            {/* 4. World State */}
            <button
              onClick={() => setWorldModalOpen(true)}
              className="flex items-center gap-2 rounded-lg px-3 py-1.5 text-xs text-[#D7DCE0] hover:bg-white/5 hover:text-[#C4AD88] transition"
            >
              <svg className="h-4 w-4 text-[#D7DCE0]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span>World</span>
            </button>

            {/* 5. Story Graph */}
            <button
              onClick={() => setGraphModalOpen(true)}
              className="flex items-center gap-2 rounded-lg px-3 py-1.5 text-xs text-[#D7DCE0] hover:bg-white/5 hover:text-[#C4AD88] transition"
            >
              <svg className="h-4 w-4 text-[#A33B42]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4" />
              </svg>
              <span>Story Graph</span>
            </button>

            {/* Subtle Yūgen Meter Pill */}
            <div
              onClick={() => setWorldModalOpen(true)}
              className="hidden md:flex items-center gap-2 rounded-full border border-white/10 bg-[#1B2228] px-3 py-1 text-xs cursor-pointer hover:border-[#C4AD88]/50 transition"
              title="Click to view full world state"
            >
              <span className="text-[10px] text-[#858A8D] font-mono">YŪGEN</span>
              <span className="font-mono text-[#C4AD88]">{runtime?.yugen_meter ?? 0}%</span>
              <div className="h-1.5 w-12 rounded-full bg-white/10 overflow-hidden">
                <div
                  className="h-full rounded-full bg-[#C4AD88]"
                  style={{ width: `${Math.min(100, Math.max(0, runtime?.yugen_meter || 0))}%` }}
                />
              </div>
            </div>
          </div>
        </div>
      </footer>

      {/* ─────────────────────────────────────────────────────────────
          5. MODAL DRAWERS FOR EACH TOOL
      ───────────────────────────────────────────────────────────── */}
      <CharacterDossierModal
        isOpen={characterModalOpen}
        onClose={() => setCharacterModalOpen(false)}
        characters={runtime?.characters}
        relationships={runtime?.relationships}
        storyId={storyId}
      />

      <MemoriesModal
        isOpen={memoriesModalOpen}
        onClose={() => setMemoriesModalOpen(false)}
        storyId={storyId}
        runtimeMemories={runtime?.world_state?.memories}
      />

      <TimelineModal
        isOpen={timelineModalOpen}
        onClose={() => setTimelineModalOpen(false)}
        scenes={scenes}
        currentSceneId={currentSceneId}
        turnNumber={runtime?.turn_number}
        storyTitle={story?.title}
      />

      <WorldStateModal
        isOpen={worldModalOpen}
        onClose={() => setWorldModalOpen(false)}
        runtime={runtime}
        currentScene={currentScene}
        scenes={scenes}
        storyTitle={story?.title}
      />

      <StoryGraphModal
        isOpen={graphModalOpen}
        onClose={() => setGraphModalOpen(false)}
        scenes={scenes}
        currentSceneId={currentSceneId}
        storyId={storyId}
        storyTitle={story?.title}
      />

      <InGameMenuModal
        isOpen={menuModalOpen}
        onClose={() => setMenuModalOpen(false)}
        story={story}
        onSave={handleQuickSave}
      />
    </div>
  )
}
