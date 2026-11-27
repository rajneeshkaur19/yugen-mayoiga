import React, { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { storiesApi, scenesApi, choicesApi, stateApi, actionApi, aiApi } from '../api/client'
import { useToast } from '../context/ToastContext'
import { useLanguage } from '../context/LanguageContext'

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
  const { t } = useLanguage()

  const [story, setStory] = useState(null)
  const [scenes, setScenes] = useState([])
  const [choices, setChoices] = useState([])
  const [runtime, setRuntime] = useState(null)
  const [currentSceneId, setCurrentSceneId] = useState(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  // AI-mediated state (Phase 5)
  const [dynamicChoices, setDynamicChoices] = useState([])
  const [loadingDynamic, setLoadingDynamic] = useState(false)
  const [freeText, setFreeText] = useState('')
  const [clarificationMessage, setClarificationMessage] = useState(null)
  const [validationError, setValidationError] = useState(null)
  const [aiNarrative, setAiNarrative] = useState(null)
  const [narrativeLoading, setNarrativeLoading] = useState(false)

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

  // Fetch dynamic AI choices for the current scene (Phase 5)
  useEffect(() => {
    let active = true

    async function loadDynamicChoices() {
      if (!currentSceneId) {
        setDynamicChoices([])
        return
      }
      setLoadingDynamic(true)
      try {
        const data = await aiApi.getDynamicChoices(storyId)
        if (active) {
          if (data && data.generation_status === 'success' && Array.isArray(data.choices)) {
            // Filter strictly to current scene choices
            const validSceneChoices = data.choices.filter(
              (c) => !c.scene_id || String(c.scene_id) === String(currentSceneId)
            )
            setDynamicChoices(validSceneChoices)
          } else {
            setDynamicChoices([])
          }
        }
      } catch {
        if (active) setDynamicChoices([])
      } finally {
        if (active) setLoadingDynamic(false)
      }
    }

    loadDynamicChoices()
    return () => { active = false }
  }, [storyId, currentSceneId, runtime?.turn_number])

  // Track scenes already attempted for image generation to prevent repeat calls
  const imageGeneratedRef = React.useRef(new Set())
  const [sceneImageLoading, setSceneImageLoading] = useState(false)
  const [sceneImageError, setSceneImageError] = useState(false)

  // On-demand scene image generation: fires once per scene, non-blocking
  useEffect(() => {
    if (!currentSceneId || !story) return
    const currentScene = scenes.find((s) => String(s.id) === String(currentSceneId))
    if (!currentScene) return

    // Already has a persisted image — no generation needed
    if (currentScene.scene_image_url) {
      setSceneImageError(false)
      return
    }

    // Already attempted for this scene in this session — skip
    if (imageGeneratedRef.current.has(String(currentSceneId))) return
    imageGeneratedRef.current.add(String(currentSceneId))

    // Non-blocking: generate in background, do not block story progression
    setSceneImageLoading(true)
    setSceneImageError(false)
    scenesApi.generateImage(storyId, currentSceneId)
      .then((updatedScene) => {
        if (updatedScene && updatedScene.scene_image_url) {
          setScenes((prev) =>
            prev.map((s) =>
              String(s.id) === String(currentSceneId) ? { ...s, ...updatedScene } : s
            )
          )
        }
      })
      .catch(() => {
        // Generation failure must NEVER block gameplay — silent degradation
      })
      .finally(() => {
        setSceneImageLoading(false)
      })
  }, [currentSceneId, storyId, story]) // eslint-disable-line react-hooks/exhaustive-deps

  // Reset scene image error state and transient AI state on scene transition
  useEffect(() => {
    setSceneImageError(false)
    setAiNarrative(null)
    setClarificationMessage(null)
    setValidationError(null)
  }, [currentSceneId])

  async function triggerNarrativeContinuation(inputContext) {
    setNarrativeLoading(true)
    setAiNarrative(null)
    try {
      const res = await aiApi.generateNarrative(storyId, inputContext)
      if (res && res.status === 'success' && res.narrative) {
        setAiNarrative(res.narrative)
      } else {
        setAiNarrative(null)
      }
    } catch {
      // Graceful degradation: failure never breaks narrative gameplay
      setAiNarrative(null)
    } finally {
      setNarrativeLoading(false)
    }
  }

  async function followChoice(choice) {
    if (busy) return
    setBusy(true)
    setClarificationMessage(null)
    setValidationError(null)
    try {
      const result = await actionApi.submitChoice(storyId, {
        choice_id: choice.id,
      })

      const [storyData, state, sceneData] = await Promise.all([
        storiesApi.get(storyId),
        stateApi.get(storyId),
        scenesApi.list(storyId),
      ])

      setStory(storyData)
      setRuntime(state)
      setScenes(getList(sceneData))
      const nextSceneId = result.current_scene_id || state.current_scene_id
      setCurrentSceneId(nextSceneId)
      showToast('Your choice has shaped the story.', 'success')

      // Post-action AI narrative continuation
      triggerNarrativeContinuation({ choice_text: choice.choice_text })
    } catch (err) {
      showToast(err.message || 'Unable to apply this choice.', 'error')
    } finally {
      setBusy(false)
    }
  }

  async function followDynamicChoice(dynamicChoice) {
    if (busy) return
    setBusy(true)
    setClarificationMessage(null)
    setValidationError(null)
    try {
      const res = await actionApi.submitAiAction(storyId, {
        dynamic_choice: dynamicChoice,
      })

      if (res.status === 'executed') {
        const [storyData, state, sceneData] = await Promise.all([
          storiesApi.get(storyId),
          stateApi.get(storyId),
          scenesApi.list(storyId),
        ])

        setStory(storyData)
        setRuntime(state)
        setScenes(getList(sceneData))
        const nextSceneId = res.story_action_result?.current_scene_id || state.current_scene_id
        setCurrentSceneId(nextSceneId)
        showToast('The story responds to your action.', 'success')

        // Post-action AI narrative continuation
        triggerNarrativeContinuation({ choice_text: dynamicChoice.choice_text })
      } else if (res.status === 'rejected') {
        setValidationError(res.validation_error || 'That action was rejected by the story rules.')
        showToast(res.validation_error || 'Action rejected.', 'error')
      } else if (res.status === 'ambiguous') {
        setClarificationMessage(res.clarification_needed || 'The action is ambiguous.')
      } else if (res.status === 'unavailable') {
        setValidationError('AI action interpretation is temporarily unavailable.')
        showToast('AI service temporarily unavailable.', 'error')
      }
    } catch (err) {
      setValidationError(err.message || 'Unable to apply this dynamic path.')
      showToast(err.message || 'Unable to apply dynamic path.', 'error')
    } finally {
      setBusy(false)
    }
  }

  async function handleFreeTextSubmit(e) {
    if (e) e.preventDefault()
    const trimmed = freeText.trim()
    if (!trimmed || busy) return

    setBusy(true)
    setClarificationMessage(null)
    setValidationError(null)
    try {
      const res = await actionApi.submitAiAction(storyId, {
        free_text: trimmed,
      })

      if (res.status === 'executed') {
        setFreeText('')
        const [storyData, state, sceneData] = await Promise.all([
          storiesApi.get(storyId),
          stateApi.get(storyId),
          scenesApi.list(storyId),
        ])

        setStory(storyData)
        setRuntime(state)
        setScenes(getList(sceneData))
        const nextSceneId = res.story_action_result?.current_scene_id || state.current_scene_id
        setCurrentSceneId(nextSceneId)
        showToast('Your action unfolds in the world.', 'success')

        // Post-action AI narrative continuation
        triggerNarrativeContinuation({ free_text: trimmed })
      } else if (res.status === 'ambiguous') {
        setClarificationMessage(res.clarification_needed || 'Please clarify your intended action.')
      } else if (res.status === 'rejected') {
        setValidationError(res.validation_error || 'That action cannot be taken in this scene.')
        showToast(res.validation_error || 'Action rejected.', 'error')
      } else if (res.status === 'unavailable') {
        setValidationError('AI interpretation is currently unavailable. You may select an established choice.')
        showToast('AI interpretation unavailable.', 'error')
      }
    } catch (err) {
      setValidationError(err.message || 'Unable to process your action.')
      showToast(err.message || 'Action failed.', 'error')
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

  // Priority chain: scene dynamic image → story cover image → static resolver
  const resolvedBackground = (() => {
    if (currentScene?.scene_image_url && !sceneImageError) {
      return currentScene.scene_image_url
    }
    if (story?.cover_image_url) {
      return story.cover_image_url
    }
    return getSceneBackground(currentScene?.location)
  })()

  return (
    <div className="relative min-h-screen w-full bg-[#101317] text-[#F1EEE8] font-sans selection:bg-[#A33B42] selection:text-white overflow-x-hidden">
      {/* ─────────────────────────────────────────────────────────────
          1. FULLSCREEN CINEMATIC ENVIRONMENTAL BACKGROUND
      ───────────────────────────────────────────────────────────── */}
      <div
        className="fixed inset-0 bg-cover bg-center bg-no-repeat transition-all duration-1000 scale-105 filter brightness-90 contrast-120"
        style={{
          backgroundImage: `url('${resolvedBackground}')`,
        }}
        onError={() => setSceneImageError(true)}
      />

      {/* Scene image generating indicator — non-blocking, unobtrusive */}
      {sceneImageLoading && (
        <div className="fixed bottom-24 right-4 z-30 flex items-center gap-1.5 rounded-lg border border-white/10 bg-[#101317]/80 px-3 py-1.5 text-[10px] text-[#858A8D] backdrop-blur-sm">
          <span className="inline-block h-2 w-2 animate-spin rounded-full border border-[#C4AD88] border-t-transparent" />
          {t.reader.paintingScene}
        </div>
      )}

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
                {t.reader.returnDashboard}
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
              <span className="hidden sm:inline">{t.reader.menu}</span>
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

                {/* AI Narrative Continuation (Phase 5) */}
                {aiNarrative && (
                  <div className="mt-8 pt-6 border-t border-[#C4AD88]/20 space-y-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="text-[#C4AD88] text-xs">◈</span>
                        <span className="font-mono text-[10px] uppercase tracking-widest text-[#C4AD88]">
                          Atmospheric Echo · 余韻
                        </span>
                      </div>
                      {aiNarrative.scene_mood && (
                        <span className="text-[10px] font-mono text-[#858A8D] bg-[#171C21] px-2 py-0.5 rounded border border-white/5">
                          {aiNarrative.scene_mood}
                        </span>
                      )}
                    </div>

                    {aiNarrative.dialogue && aiNarrative.dialogue.length > 0 && (
                      <div className="space-y-2 my-3">
                        {aiNarrative.dialogue.map((d, i) => (
                          <div key={i} className="rounded-xl border border-[#C4AD88]/20 bg-[#1B2228]/60 p-4">
                            <span className="rounded bg-[#C4AD88]/20 border border-[#C4AD88]/40 px-2 py-0.5 text-[9px] font-semibold text-[#C4AD88] uppercase tracking-wider block w-fit mb-1">
                              {d.character_name}
                            </span>
                            <p className="font-cinematic text-lg italic text-[#F1EEE8]">
                              “{d.dialogue}”
                            </p>
                          </div>
                        ))}
                      </div>
                    )}

                    <div className="font-cinematic text-lg sm:text-xl leading-relaxed text-[#D7DCE0] whitespace-pre-line space-y-3">
                      {aiNarrative.narrative_text}
                    </div>
                  </div>
                )}

                {/* Narrative Weaving Shimmer */}
                {narrativeLoading && (
                  <div className="mt-6 flex items-center gap-2.5 rounded-lg border border-[#C4AD88]/20 bg-[#C4AD88]/5 py-2.5 px-4 text-xs text-[#C4AD88] animate-pulse">
                    <div className="h-1.5 w-1.5 rounded-full bg-[#C4AD88]" />
                    <span>The unseen chronicle weaves continuation...</span>
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
                    {choices.length + (dynamicChoices.length > 0 ? dynamicChoices.length : 0)} options
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

                {/* Dynamic Choices Loading State */}
                {loadingDynamic && (
                  <div className="mt-4 space-y-2">
                    <div className="flex items-center gap-2 text-xs text-[#C4AD88]/80 font-mono tracking-wider">
                      <span className="inline-block h-1.5 w-1.5 rounded-full bg-[#C4AD88] animate-ping" />
                      <span>Consulting the unseen threads...</span>
                    </div>
                    <div className="h-14 rounded-xl border border-[#C4AD88]/20 bg-[#C4AD88]/5 animate-pulse" />
                  </div>
                )}

                {/* Dynamic AI Choices */}
                {dynamicChoices.length > 0 && (
                  <div className="mt-5 pt-4 border-t border-white/[0.08] space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-1.5 text-xs font-mono uppercase tracking-wider text-[#C4AD88]">
                        <span>✦</span>
                        <span>Emergent Paths</span>
                      </div>
                      <span className="text-[10px] text-[#858A8D] font-mono">Dynamic AI</span>
                    </div>
                    <div className="space-y-2.5">
                      {dynamicChoices.map((dChoice, idx) => (
                        <button
                          key={dChoice.id || `dynamic-${idx}`}
                          disabled={busy}
                          onClick={() => followDynamicChoice(dChoice)}
                          className="group flex w-full flex-col gap-1.5 rounded-xl border border-[#C4AD88]/30 bg-[#1B2228]/90 p-4 text-left transition-all hover:border-[#C4AD88] hover:bg-[#C4AD88]/10 hover:shadow-[0_0_20px_rgba(196,173,136,0.15)] disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          <div className="flex items-start justify-between gap-3 w-full">
                            <div className="flex items-start gap-2.5">
                              <span className="font-mono text-xs text-[#C4AD88] mt-0.5 shrink-0">
                                ✦ ›
                              </span>
                              <span className="font-cinematic text-base sm:text-lg leading-relaxed text-[#F1EEE8] group-hover:text-white transition">
                                {dChoice.choice_text}
                              </span>
                            </div>
                            <span className="text-[#C4AD88] transition-transform duration-300 group-hover:translate-x-1 shrink-0 mt-0.5">
                              →
                            </span>
                          </div>
                          {(dChoice.consequence_hint || dChoice.risk_level) && (
                            <div className="flex items-center gap-2 pl-6 text-[11px] text-[#858A8D] group-hover:text-[#C4AD88]/90 transition">
                              {dChoice.risk_level && (
                                <span className="capitalize font-mono text-[10px] px-1.5 py-0.5 rounded border border-white/10 bg-black/20 text-[#C4AD88]">
                                  {dChoice.risk_level} risk
                                </span>
                              )}
                              {dChoice.consequence_hint && (
                                <span className="italic truncate">{dChoice.consequence_hint}</span>
                              )}
                            </div>
                          )}
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* Inline Clarification Callout */}
                {clarificationMessage && (
                  <div className="mt-4 rounded-xl border border-[#C4AD88]/40 bg-[#C4AD88]/10 p-4 text-xs text-[#F1EEE8] space-y-1.5">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-1.5 font-semibold text-[#C4AD88]">
                        <span>✦</span>
                        <span>The mist clouds your intent:</span>
                      </div>
                      <button
                        onClick={() => setClarificationMessage(null)}
                        className="text-[#858A8D] hover:text-white transition text-sm"
                        title="Dismiss"
                      >
                        ×
                      </button>
                    </div>
                    <p className="leading-relaxed text-[#D7DCE0]">{clarificationMessage}</p>
                    <p className="text-[11px] text-[#858A8D] italic">
                      Refine your action below and try again.
                    </p>
                  </div>
                )}

                {/* Inline Validation Error Callout */}
                {validationError && (
                  <div className="mt-4 rounded-xl border border-[#A33B42]/40 bg-[#A33B42]/10 p-4 text-xs text-[#F1EEE8] space-y-1.5">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-1.5 font-semibold text-[#E58288]">
                        <span>⚠</span>
                        <span>Action Unfulfilled</span>
                      </div>
                      <button
                        onClick={() => setValidationError(null)}
                        className="text-[#858A8D] hover:text-white transition text-sm"
                        title="Dismiss"
                      >
                        ×
                      </button>
                    </div>
                    <p className="leading-relaxed text-[#D7DCE0]">{validationError}</p>
                  </div>
                )}

                {/* Free-Text Action Input Dock */}
                <div className="mt-5 pt-4 border-t border-white/[0.08]">
                  <form onSubmit={handleFreeTextSubmit} className="space-y-2">
                    <label htmlFor="free-action-input" className="block text-xs font-mono uppercase tracking-wider text-[#858A8D]">
                      Forge Your Own Path
                    </label>
                    <div className="relative flex items-center">
                      <input
                        id="free-action-input"
                        type="text"
                        disabled={busy}
                        value={freeText}
                        onChange={(e) => setFreeText(e.target.value)}
                        maxLength={300}
                        placeholder="What do you do? (e.g. Inspect the photograph carefully)"
                        className="w-full rounded-xl border border-white/10 bg-[#1B2228]/90 py-3 pl-4 pr-24 text-sm text-[#F1EEE8] placeholder:text-[#858A8D]/60 focus:border-[#C4AD88] focus:bg-[#101317] focus:outline-none transition shadow-inner disabled:opacity-50"
                      >
                      </input>
                      <button
                        type="submit"
                        disabled={busy || !freeText.trim()}
                        className="absolute right-1.5 rounded-lg bg-[#A33B42] hover:bg-[#8B263E] text-white px-3.5 py-1.5 text-xs font-medium transition disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1 shadow-md"
                      >
                        <span>Act</span>
                        <span className="text-[10px]">↵</span>
                      </button>
                    </div>
                    <div className="flex items-center justify-between text-[10px] text-[#858A8D] px-1">
                      <span>Natural language actions interpreted by AI & verified by story rules</span>
                      <span>{freeText.length}/300</span>
                    </div>
                  </form>
                </div>

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
              <span>{t.reader.dossier}</span>
            </button>

            {/* 2. Memories */}
            <button
              onClick={() => setMemoriesModalOpen(true)}
              className="flex items-center gap-2 rounded-lg px-3 py-1.5 text-xs text-[#D7DCE0] hover:bg-white/5 hover:text-[#C4AD88] transition"
            >
              <svg className="h-4 w-4 text-[#A33B42]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
              </svg>
              <span>{t.reader.memories}</span>
            </button>

            {/* 3. Timeline */}
            <button
              onClick={() => setTimelineModalOpen(true)}
              className="flex items-center gap-2 rounded-lg px-3 py-1.5 text-xs text-[#D7DCE0] hover:bg-white/5 hover:text-[#C4AD88] transition"
            >
              <svg className="h-4 w-4 text-[#C4AD88]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span>{t.reader.timeline}</span>
            </button>

            {/* 4. World State */}
            <button
              onClick={() => setWorldModalOpen(true)}
              className="flex items-center gap-2 rounded-lg px-3 py-1.5 text-xs text-[#D7DCE0] hover:bg-white/5 hover:text-[#C4AD88] transition"
            >
              <svg className="h-4 w-4 text-[#D7DCE0]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span>{t.reader.worldState}</span>
            </button>

            {/* 5. Story Graph */}
            <button
              onClick={() => setGraphModalOpen(true)}
              className="flex items-center gap-2 rounded-lg px-3 py-1.5 text-xs text-[#D7DCE0] hover:bg-white/5 hover:text-[#C4AD88] transition"
            >
              <svg className="h-4 w-4 text-[#A33B42]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4" />
              </svg>
              <span>{t.reader.storyGraph}</span>
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
