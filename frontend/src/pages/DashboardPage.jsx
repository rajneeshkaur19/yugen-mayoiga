import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { storiesApi } from '../api/client'

/**
 * Maps stories to relevant environmental cover artwork.
 */
function getStoryCover(story) {
  const title = (story?.title || '').toLowerCase()
  const genre = (story?.genre || '').toLowerCase()

  if (title.includes('abandoned') || title.includes('house') || title.includes('mayoiga')) {
    return '/assets/story-covers/cover-abandoned-house.png'
  }
  if (title.includes('station') || title.includes('train') || genre.includes('thriller')) {
    return '/assets/story-covers/cover-silent-station.png'
  }
  if (title.includes('letter') || title.includes('midnight') || genre.includes('romance')) {
    return '/assets/story-covers/cover-midnight-letters.png'
  }
  if (title.includes('shrine') || title.includes('rain') || genre.includes('horror')) {
    return '/assets/story-covers/cover-shrine-rain.png'
  }
  if (title.includes('bamboo') || title.includes('forest') || genre.includes('adventure')) {
    return '/assets/story-covers/cover-bamboo-forest.png'
  }
  return '/assets/story-covers/cover-lost-village.png'
}

/**
 * Returns an authentic thematic Kanji stamp for cards.
 */
function getStoryKanji(story) {
  const genre = (story?.genre || '').toLowerCase()
  if (genre.includes('mystery')) return '迷'
  if (genre.includes('thriller')) return '怖'
  if (genre.includes('fantasy')) return '幻'
  if (genre.includes('romance')) return '愛'
  if (genre.includes('horror')) return '怪'
  return '幽'
}

export default function DashboardPage() {
  const { user, logout } = useAuth()
  const { showToast } = useToast()
  const navigate = useNavigate()

  const [stories, setStories] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [deletingStory, setDeletingStory] = useState(null)
  const [isDeleting, setIsDeleting] = useState(false)

  // Navigation & Filter state
  const [activeTab, setActiveTab] = useState('library')
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedFilter, setSelectedFilter] = useState('all')
  const [sortBy, setSortBy] = useState('newest')
  const [mobileNavOpen, setMobileNavOpen] = useState(false)
  const [settingsModalOpen, setSettingsModalOpen] = useState(false)

  const loadStories = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await storiesApi.list()
      setStories(Array.isArray(data) ? data : [])
    } catch (err) {
      setError(err.message || 'Unable to open your sanctuary archive.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadStories()
  }, [loadStories])

  function handleLogout() {
    logout()
    showToast('You have departed from Mayoiga.', 'success')
    navigate('/', { replace: true })
  }

  async function confirmDelete() {
    if (!deletingStory) return
    setIsDeleting(true)
    try {
      await storiesApi.delete(deletingStory.id)
      setStories((current) => current.filter((item) => item.id !== deletingStory.id))
      showToast(`"${deletingStory.title}" has dissolved from the archive.`, 'success')
      setDeletingStory(null)
    } catch (err) {
      showToast(err.message || 'Unable to delete this story.', 'error')
    } finally {
      setIsDeleting(false)
    }
  }

  // Filter and sort computation
  const filteredStories = useMemo(() => {
    return stories
      .filter((story) => {
        const matchesSearch =
          (story.title || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
          (story.genre || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
          (story.theme || '').toLowerCase().includes(searchQuery.toLowerCase())

        if (!matchesSearch) return false

        if (selectedFilter === 'all') return true
        if (selectedFilter === 'in-progress') return story.status !== 'completed'
        if (selectedFilter === 'completed') return story.status === 'completed'
        return (story.genre || '').toLowerCase() === selectedFilter.toLowerCase()
      })
      .sort((a, b) => {
        if (sortBy === 'newest') {
          return new Date(b.created_at || 0) - new Date(a.created_at || 0)
        }
        if (sortBy === 'oldest') {
          return new Date(a.created_at || 0) - new Date(b.created_at || 0)
        }
        if (sortBy === 'title') {
          return (a.title || '').localeCompare(b.title || '')
        }
        return 0
      })
  }, [stories, searchQuery, selectedFilter, sortBy])

  // Identify featured story for prominent continue card
  const featuredStory = stories.length > 0 ? stories[0] : null

  return (
    <div className="flex min-h-screen bg-[#101317] text-[#F1EEE8] font-sans selection:bg-[#A33B42] selection:text-white">
      {/* ─────────────────────────────────────────────────────────────
          1. ELEGANT SIDEBAR (DESKTOP)
      ───────────────────────────────────────────────────────────── */}
      <aside className="hidden md:flex w-64 flex-col justify-between border-r border-white/[0.08] bg-[#14191E] p-6 shrink-0 sticky top-0 h-screen">
        <div>
          {/* Logo / Torii Branding */}
          <Link to="/dashboard" className="group flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-[#C4AD88]/30 bg-[#101317] text-[#C4AD88] transition group-hover:border-[#C4AD88] group-hover:shadow-[0_0_15px_rgba(196,173,136,0.3)]">
              <svg className="h-6 w-6 text-[#A33B42] transition group-hover:text-[#C4AD88]" viewBox="0 0 24 24" fill="currentColor">
                <path d="M2 5h20v2H2V5zm3 3h14v2H5V8zm2 3h2v11H7V11zm8 0h2v11h-2V11zM1 3h22v2H1V3z" />
              </svg>
            </div>
            <div>
              <span className="font-cinematic text-lg font-bold tracking-[0.2em] text-[#F1EEE8] block group-hover:text-[#C4AD88] transition">
                YŪGEN MAYOIGA
              </span>
              <span className="text-[10px] uppercase font-mono tracking-widest text-[#858A8D] block">
                Story Sanctuary
              </span>
            </div>
          </Link>

          {/* Navigation Links */}
          <nav className="mt-10 space-y-2">
            <button
              onClick={() => setActiveTab('library')}
              className={`flex w-full items-center gap-3 rounded-xl px-4 py-3 text-xs font-medium transition ${
                activeTab === 'library'
                  ? 'border border-[#C4AD88]/30 bg-[#1B2228] text-[#C4AD88] shadow-sm'
                  : 'text-[#858A8D] hover:bg-white/5 hover:text-[#D7DCE0]'
              }`}
            >
              <svg className="h-4 w-4 text-[#C4AD88]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
              </svg>
              <span>Chronicle Library</span>
            </button>

            <Link
              to="/stories/new"
              className="flex w-full items-center gap-3 rounded-xl px-4 py-3 text-xs font-medium text-[#D7DCE0] hover:bg-white/5 hover:text-[#C4AD88] transition"
            >
              <svg className="h-4 w-4 text-[#A33B42]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              <span>Create New Story</span>
            </Link>

            {featuredStory && (
              <Link
                to={`/stories/${featuredStory.id}`}
                className="flex w-full items-center gap-3 rounded-xl px-4 py-3 text-xs font-medium text-[#D7DCE0] hover:bg-white/5 hover:text-[#C4AD88] transition"
              >
                <svg className="h-4 w-4 text-[#C4AD88]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span>Continue Playing</span>
              </Link>
            )}

            <button
              onClick={() => setSettingsModalOpen(true)}
              className="flex w-full items-center gap-3 rounded-xl px-4 py-3 text-xs font-medium text-[#858A8D] hover:bg-white/5 hover:text-[#D7DCE0] transition"
            >
              <svg className="h-4 w-4 text-[#858A8D]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
              <span>Preferences</span>
            </button>
          </nav>
        </div>

        {/* User Profile & Sign Out */}
        <div className="border-t border-white/[0.08] pt-6 space-y-4">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-full border border-[#C4AD88]/30 bg-[#1B2228] font-cinematic text-sm font-semibold text-[#C4AD88]">
              {user?.username ? user.username.charAt(0).toUpperCase() : 'W'}
            </div>
            <div className="overflow-hidden">
              <span className="text-xs font-semibold text-[#F1EEE8] block truncate">
                {user?.username || 'Wanderer'}
              </span>
              <span className="text-[10px] text-[#858A8D] font-mono block">
                {stories.length} Chronicles Saved
              </span>
            </div>
          </div>

          <button
            onClick={handleLogout}
            className="flex w-full items-center justify-center gap-2 rounded-lg border border-white/10 bg-[#101317] py-2.5 text-xs font-medium text-[#858A8D] hover:border-[#A33B42]/50 hover:bg-[#A33B42]/10 hover:text-[#F1EEE8] transition"
          >
            <svg className="h-3.5 w-3.5 text-[#A33B42]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
            <span>Sign Out</span>
          </button>
        </div>
      </aside>

      {/* ─────────────────────────────────────────────────────────────
          2. MOBILE HEADER & NAVIGATION DRAWER
      ───────────────────────────────────────────────────────────── */}
      <div className="md:hidden fixed top-0 left-0 right-0 z-40 border-b border-white/[0.08] bg-[#14191E]/90 backdrop-blur-md px-6 py-3.5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-[#C4AD88]/30 bg-[#101317] text-[#C4AD88]">
            <svg className="h-5 w-5 text-[#A33B42]" viewBox="0 0 24 24" fill="currentColor">
              <path d="M2 5h20v2H2V5zm3 3h14v2H5V8zm2 3h2v11H7V11zm8 0h2v11h-2V11zM1 3h22v2H1V3z" />
            </svg>
          </div>
          <span className="font-cinematic text-lg font-bold tracking-widest text-[#F1EEE8]">
            YŪGEN MAYOIGA
          </span>
        </div>

        <button
          onClick={() => setMobileNavOpen((v) => !v)}
          className="rounded-lg border border-white/10 p-2 text-[#858A8D] hover:text-[#F1EEE8]"
        >
          {mobileNavOpen ? (
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          ) : (
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          )}
        </button>
      </div>

      {/* Mobile Drawer */}
      {mobileNavOpen && (
        <div className="md:hidden fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex flex-col justify-between p-6">
          <div className="space-y-6 pt-12">
            <div className="flex justify-between items-center border-b border-white/10 pb-4">
              <span className="font-cinematic text-2xl font-bold text-[#F1EEE8]">Yūgen Mayoiga</span>
              <button onClick={() => setMobileNavOpen(false)} className="text-xl text-[#858A8D]">✕</button>
            </div>
            <nav className="flex flex-col space-y-4 text-sm font-medium">
              <button
                onClick={() => {
                  setActiveTab('library')
                  setMobileNavOpen(false)
                }}
                className="text-left text-[#C4AD88]"
              >
                Chronicle Library
              </button>
              <Link to="/stories/new" onClick={() => setMobileNavOpen(false)} className="text-[#D7DCE0]">
                + Begin New Story
              </Link>
              {featuredStory && (
                <Link to={`/stories/${featuredStory.id}`} onClick={() => setMobileNavOpen(false)} className="text-[#D7DCE0]">
                  Continue Last Story
                </Link>
              )}
            </nav>
          </div>

          <div className="border-t border-white/10 pt-6 space-y-4">
            <div className="text-xs text-[#858A8D]">Logged in as {user?.username}</div>
            <button
              onClick={handleLogout}
              className="w-full rounded-lg border border-[#A33B42]/50 bg-[#A33B42]/20 py-2.5 text-xs text-[#F1EEE8]"
            >
              Sign Out
            </button>
          </div>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────
          3. MAIN CONTENT AREA
      ───────────────────────────────────────────────────────────── */}
      <main className="flex-1 overflow-y-auto px-6 py-8 pt-20 md:pt-10 max-w-7xl mx-auto w-full space-y-10">
        {/* Welcome / Sanctuary Hero Header */}
        <section className="relative overflow-hidden rounded-2xl border border-white/[0.08] bg-[#171C21] p-8 sm:p-12 shadow-2xl">
          {/* Atmospheric Environmental Backdrop with Gradient */}
          <div
            className="absolute inset-0 bg-cover bg-center bg-no-repeat opacity-55 filter brightness-95 contrast-125"
            style={{ backgroundImage: "url('/assets/backgrounds/mayoiga-estate-night.png')" }}
          />
          <div className="absolute inset-0 bg-gradient-to-r from-[#171C21] via-[#171C21]/70 to-transparent" />

          <div className="relative z-10 max-w-2xl">
            <div className="inline-flex items-center gap-2 rounded-full border border-[#C4AD88]/30 bg-[#101317]/80 px-3.5 py-1 text-xs text-[#C4AD88] font-mono mb-4">
              <span className="h-1.5 w-1.5 rounded-full bg-[#A33B42] animate-pulse" />
              <span>Sanctuary Archive</span>
              <span className="text-[#858A8D]">· 迷い家</span>
            </div>

            <h1 className="font-cinematic text-4xl sm:text-5xl font-semibold tracking-wide text-[#F1EEE8]">
              Welcome back, {user?.username || 'Wanderer'}.
            </h1>

            <p className="font-cinematic text-lg italic text-[#D7DCE0] mt-3">
              “Some stories remember the choices you have forgotten.”
            </p>

            <p className="text-xs sm:text-sm text-[#858A8D] mt-3 leading-relaxed">
              Step across the threshold to resume your journey, or manifest a new narrative into the mist.
            </p>

            <div className="mt-8 flex flex-wrap gap-4 items-center">
              <Link
                to="/stories/new"
                className="group flex items-center gap-2.5 rounded-lg border border-[#A33B42] bg-[#A33B42] px-6 py-3 text-xs sm:text-sm font-semibold text-[#F1EEE8] shadow-lg hover:bg-[#702B34] transition hover:shadow-[0_0_20px_rgba(163,59,66,0.5)]"
              >
                <span>＋ Begin a New Story</span>
                <span className="text-[#C4AD88] transition-transform group-hover:translate-x-1">→</span>
              </Link>

              {featuredStory && (
                <Link
                  to={`/stories/${featuredStory.id}`}
                  className="rounded-lg border border-white/15 bg-[#1B2228]/80 px-6 py-3 text-xs sm:text-sm font-medium text-[#D7DCE0] hover:border-[#C4AD88]/50 hover:text-white transition backdrop-blur-sm"
                >
                  Resume Active Journey
                </Link>
              )}
            </div>
          </div>
        </section>

        {/* ─────────────────────────────────────────────────────────────
            4. CONTINUE PLAYING (FEATURED ACTIVE STORY)
        ───────────────────────────────────────────────────────────── */}
        {featuredStory && (
          <section className="space-y-4">
            <div className="flex items-center justify-between border-b border-white/[0.08] pb-3">
              <div className="flex items-center gap-2">
                <span className="text-xs font-cinematic text-[#C4AD88]">✦</span>
                <h2 className="font-cinematic text-2xl font-semibold text-[#F1EEE8]">
                  Continue Your Journey
                </h2>
              </div>
              <span className="text-xs font-mono text-[#858A8D]">Active Chronicle</span>
            </div>

            <div className="group relative overflow-hidden rounded-2xl border border-white/[0.08] bg-[#171C21] transition hover:border-[#C4AD88]/40 hover:shadow-[0_15px_30px_rgba(0,0,0,0.5)]">
              <div className="grid md:grid-cols-12 items-stretch">
                {/* Environmental Art Preview (Col 1-5) */}
                <div className="md:col-span-5 relative h-64 md:h-auto overflow-hidden bg-[#101317]">
                  <img
                    src={getStoryCover(featuredStory)}
                    alt={featuredStory.title}
                    className="h-full w-full object-cover transition-transform duration-700 group-hover:scale-105"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t md:bg-gradient-to-r from-[#171C21] via-transparent to-black/30" />

                  {/* Japanese Kanji Stamp */}
                  <span className="absolute top-4 left-4 rounded-md border border-white/20 bg-black/60 px-2 py-1 font-cinematic text-xs text-[#C4AD88] backdrop-blur-sm">
                    {getStoryKanji(featuredStory)}
                  </span>
                </div>

                {/* Narrative Details (Col 6-12) */}
                <div className="md:col-span-7 p-6 sm:p-8 flex flex-col justify-between">
                  <div>
                    <div className="flex items-center gap-3">
                      <span className="rounded-full bg-[#A33B42] px-3 py-0.5 text-[10px] font-semibold text-white">
                        {featuredStory.genre || 'Mystery'}
                      </span>
                      <span className="text-xs text-[#858A8D] font-mono">
                        {featuredStory.season || 'Autumn'} · {featuredStory.tone || 'Melancholic'}
                      </span>
                    </div>

                    <h3 className="font-cinematic text-3xl font-semibold text-[#F1EEE8] group-hover:text-[#C4AD88] transition mt-2">
                      {featuredStory.title}
                    </h3>

                    <p className="mt-2 text-xs sm:text-sm text-[#858A8D] line-clamp-2 leading-relaxed">
                      {featuredStory.theme || 'A secluded mountain dwelling where every room stores secrets that shift when unobserved.'}
                    </p>
                  </div>

                  {/* Progress Bar & Actions */}
                  <div className="mt-6 pt-5 border-t border-white/[0.08] flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div className="space-y-1.5 flex-1 max-w-xs">
                      <div className="flex justify-between text-[11px] font-mono">
                        <span className="text-[#858A8D]">Manuscript State</span>
                        <span className="text-[#C4AD88]">In Progress</span>
                      </div>
                      <div className="h-1.5 w-full rounded-full bg-white/5 overflow-hidden">
                        <div className="h-full rounded-full bg-gradient-to-r from-[#A33B42] to-[#C4AD88] w-2/3" />
                      </div>
                    </div>

                    <Link
                      to={`/stories/${featuredStory.id}`}
                      className="inline-flex items-center justify-center gap-2 rounded-lg border border-[#A33B42] bg-[#A33B42] px-6 py-2.5 text-xs font-semibold text-[#F1EEE8] hover:bg-[#702B34] transition shadow-[0_0_15px_rgba(163,59,66,0.4)]"
                    >
                      <span>Continue Story</span>
                      <span>→</span>
                    </Link>
                  </div>
                </div>
              </div>
            </div>
          </section>
        )}

        {/* ─────────────────────────────────────────────────────────────
            5. STORY LIBRARY GRID WITH FILTERS & SEARCH
        ───────────────────────────────────────────────────────────── */}
        <section className="space-y-6">
          <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 border-b border-white/[0.08] pb-4">
            <div>
              <p className="text-xs uppercase tracking-widest text-[#C4AD88] font-mono">Archive Collection</p>
              <h2 className="font-cinematic text-3xl font-semibold text-[#F1EEE8] mt-1">
                Your Stories
              </h2>
            </div>

            {/* Search Input & Controls */}
            <div className="flex flex-wrap items-center gap-3">
              {/* Search */}
              <div className="relative">
                <input
                  type="text"
                  placeholder="Search chronicles..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-48 sm:w-60 rounded-lg border border-white/10 bg-[#101317] px-3.5 py-2 text-xs text-[#F1EEE8] placeholder-[#858A8D] outline-none focus:border-[#C4AD88]/50 transition"
                />
                {searchQuery && (
                  <button
                    onClick={() => setSearchQuery('')}
                    className="absolute right-2.5 top-2.5 text-xs text-[#858A8D] hover:text-white"
                  >
                    ✕
                  </button>
                )}
              </div>

              {/* Sort Dropdown */}
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
                className="rounded-lg border border-white/10 bg-[#101317] px-3 py-2 text-xs text-[#D7DCE0] outline-none focus:border-[#C4AD88]/50 transition"
              >
                <option value="newest">Newest First</option>
                <option value="oldest">Oldest First</option>
                <option value="title">Alphabetical (A-Z)</option>
              </select>
            </div>
          </div>

          {/* Filter Pills */}
          <div className="flex items-center gap-2 overflow-x-auto pb-2 text-xs">
            {['all', 'in-progress', 'completed', 'Mystery', 'Psychological Thriller', 'Dark Fantasy'].map((f) => (
              <button
                key={f}
                onClick={() => setSelectedFilter(f)}
                className={`rounded-lg px-3.5 py-1.5 capitalize transition whitespace-nowrap ${
                  selectedFilter.toLowerCase() === f.toLowerCase()
                    ? 'border border-[#C4AD88]/50 bg-[#C4AD88]/15 text-[#C4AD88]'
                    : 'border border-white/5 bg-[#171C21] text-[#858A8D] hover:text-[#D7DCE0]'
                }`}
              >
                {f === 'all' ? 'All Stories' : f.replaceAll('-', ' ')}
              </button>
            ))}
          </div>

          {/* Loading State */}
          {loading && (
            <div className="py-24 text-center">
              <div className="inline-block h-4 w-4 rounded-full bg-[#A33B42] animate-ping" />
              <p className="mt-4 font-cinematic text-xl text-[#858A8D]">Opening the sanctuary archive...</p>
            </div>
          )}

          {/* Error State */}
          {!loading && error && (
            <div className="rounded-2xl border border-[#A33B42]/30 bg-[#171C21] p-8 text-center space-y-4">
              <p className="text-sm text-[#A33B42]">{error}</p>
              <button
                onClick={loadStories}
                className="rounded-lg bg-[#A33B42] px-5 py-2 text-xs font-semibold text-white hover:bg-[#702B34] transition"
              >
                Reopen Sanctuary Archive
              </button>
            </div>
          )}

          {/* Empty State */}
          {!loading && !error && filteredStories.length === 0 && (
            <div className="rounded-2xl border border-dashed border-white/10 bg-[#171C21]/40 py-20 px-6 text-center max-w-xl mx-auto space-y-5">
              <div className="inline-flex h-12 w-12 items-center justify-center rounded-full border border-[#C4AD88]/30 bg-[#101317] text-[#C4AD88]">
                <svg className="h-6 w-6" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M2 5h20v2H2V5zm3 3h14v2H5V8zm2 3h2v11H7V11zm8 0h2v11h-2V11zM1 3h22v2H1V3z" />
                </svg>
              </div>
              <h3 className="font-cinematic text-3xl font-semibold text-[#F1EEE8]">
                An empty page is also a beginning.
              </h3>
              <p className="text-xs text-[#858A8D] leading-relaxed">
                {searchQuery
                  ? 'No stories match your current filter criteria.'
                  : 'No chronicles have been recorded in your sanctuary yet. Step across the threshold and shape your first world.'}
              </p>
              <div>
                <Link
                  to="/stories/new"
                  className="inline-flex items-center gap-2 rounded-lg border border-[#A33B42] bg-[#A33B42] px-6 py-2.5 text-xs font-semibold text-white shadow hover:bg-[#702B34] transition"
                >
                  <span>Begin Your First Story</span>
                  <span>→</span>
                </Link>
              </div>
            </div>
          )}

          {/* Stories Grid */}
          {!loading && !error && filteredStories.length > 0 && (
            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {filteredStories.map((story) => (
                <article
                  key={story.id}
                  className="group flex flex-col justify-between overflow-hidden rounded-2xl border border-white/[0.08] bg-[#171C21] transition hover:border-[#C4AD88]/40 hover:shadow-[0_15px_30px_rgba(0,0,0,0.6)]"
                >
                  {/* Environmental Image Header */}
                  <div className="relative h-48 w-full overflow-hidden bg-[#101317]">
                    <img
                      src={getStoryCover(story)}
                      alt={story.title}
                      className="h-full w-full object-cover transition-transform duration-700 group-hover:scale-105"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-[#171C21] via-transparent to-black/40" />

                    {/* Japanese Kanji Stamp */}
                    <span className="absolute top-3 right-3 rounded-md border border-white/20 bg-black/60 px-2 py-0.5 font-cinematic text-xs text-[#C4AD88] backdrop-blur-sm">
                      {getStoryKanji(story)}
                    </span>

                    {/* Genre Tag */}
                    <span className="absolute bottom-3 left-4 rounded-full bg-[#A33B42] px-2.5 py-0.5 text-[10px] font-semibold text-white">
                      {story.genre || 'Mystery'}
                    </span>
                  </div>

                  {/* Card Body */}
                  <div className="flex flex-1 flex-col justify-between p-6">
                    <div>
                      <div className="flex items-center justify-between text-[11px] text-[#858A8D] font-mono">
                        <span>{story.season || 'Autumn'} · {story.tone || 'Atmospheric'}</span>
                        <span className="capitalize text-[#C4AD88]">{story.status || 'Active'}</span>
                      </div>

                      <Link to={`/stories/${story.id}`}>
                        <h3 className="font-cinematic text-2xl font-semibold text-[#F1EEE8] group-hover:text-[#C4AD88] transition mt-2">
                          {story.title}
                        </h3>
                      </Link>

                      <p className="mt-2 text-xs text-[#858A8D] line-clamp-2 leading-relaxed">
                        {story.theme || 'Every choice leaves a trace in this chronicle.'}
                      </p>
                    </div>

                    {/* Footer Actions */}
                    <div className="mt-6 pt-4 border-t border-white/[0.08] flex items-center justify-between gap-3">
                      <Link
                        to={`/stories/${story.id}`}
                        className="inline-flex items-center gap-1.5 text-xs font-semibold text-[#F1EEE8] group-hover:text-[#C4AD88] transition"
                      >
                        <span>Open Story</span>
                        <span>→</span>
                      </Link>

                      <button
                        type="button"
                        onClick={() => setDeletingStory(story)}
                        className="rounded-lg border border-white/5 p-2 text-xs text-[#858A8D] hover:border-[#A33B42]/50 hover:bg-[#A33B42]/10 hover:text-[#A33B42] transition"
                        title="Delete story"
                      >
                        <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    </div>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>
      </main>

      {/* ─────────────────────────────────────────────────────────────
          6. MODALS: DELETE CONFIRMATION & SETTINGS
      ───────────────────────────────────────────────────────────── */}
      {/* Delete Confirmation Modal */}
      {deletingStory && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div onClick={() => setDeletingStory(null)} className="fixed inset-0 bg-black/80 backdrop-blur-md" />
          <div className="relative z-10 w-full max-w-md overflow-hidden rounded-2xl border border-white/10 bg-[#14191E] text-[#F1EEE8] shadow-2xl p-6 sm:p-8 space-y-6">
            <div className="flex items-center gap-3 text-[#A33B42]">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-[#A33B42]/20 border border-[#A33B42]/40">
                <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              </div>
              <h3 className="font-cinematic text-2xl font-semibold text-[#F1EEE8]">
                Dissolve Chronicle?
              </h3>
            </div>

            <p className="text-xs text-[#858A8D] leading-relaxed">
              Are you certain you wish to dissolve <strong className="text-[#F1EEE8]">"{deletingStory.title}"</strong>?
              All recorded turns, character trust, and memories will be permanently forgotten. This cannot be undone.
            </p>

            <div className="flex justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => setDeletingStory(null)}
                className="rounded-lg border border-white/10 px-4 py-2 text-xs text-[#858A8D] hover:text-white transition"
              >
                Keep Story
              </button>
              <button
                type="button"
                disabled={isDeleting}
                onClick={confirmDelete}
                className="rounded-lg border border-[#A33B42] bg-[#A33B42] px-5 py-2 text-xs font-semibold text-white hover:bg-[#702B34] transition disabled:opacity-50"
              >
                {isDeleting ? 'Dissolving...' : 'Permanently Delete'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Preferences / Settings Modal */}
      {settingsModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div onClick={() => setSettingsModalOpen(false)} className="fixed inset-0 bg-black/80 backdrop-blur-md" />
          <div className="relative z-10 w-full max-w-md overflow-hidden rounded-2xl border border-white/10 bg-[#14191E] text-[#F1EEE8] shadow-2xl p-6 sm:p-8 space-y-6">
            <div className="flex items-center justify-between border-b border-white/10 pb-4">
              <div>
                <h3 className="font-cinematic text-2xl font-semibold text-[#F1EEE8]">Sanctuary Settings</h3>
                <p className="text-xs text-[#858A8D] mt-0.5">Customization & Aesthetics</p>
              </div>
              <button onClick={() => setSettingsModalOpen(false)} className="text-[#858A8D] hover:text-white">✕</button>
            </div>

            <div className="space-y-4 text-xs">
              <div className="flex justify-between items-center p-3 rounded-lg border border-white/5 bg-[#101317]">
                <span className="text-[#D7DCE0]">Interface Aesthetic</span>
                <span className="font-mono text-[#C4AD88]">Obsidian Dark (Active)</span>
              </div>
              <div className="flex justify-between items-center p-3 rounded-lg border border-white/5 bg-[#101317]">
                <span className="text-[#D7DCE0]">Language Typography</span>
                <span className="font-mono text-[#C4AD88]">English · 日本語</span>
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <button
                onClick={() => setSettingsModalOpen(false)}
                className="rounded-lg border border-white/10 bg-[#1B2228] px-5 py-2 text-xs text-[#F1EEE8] hover:border-white/20 transition"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
