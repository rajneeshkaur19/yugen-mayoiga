import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { useLanguage } from '../../context/LanguageContext'
import { feedbackApi } from '../../api/client'
import './landing.css'

export default function LandingPage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const { langCode, setLanguageCode, languages, t } = useLanguage()
  const selectedLanguage = langCode
  const setSelectedLanguage = setLanguageCode
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [langMenuOpen, setLangMenuOpen] = useState(false)
  const [activeStoryPreview, setActiveStoryPreview] = useState(0)

  // Feedback form state
  const [feedbackType, setFeedbackType] = useState('Suggestion')
  const [feedbackSubject, setFeedbackSubject] = useState('')
  const [feedbackMessage, setFeedbackMessage] = useState('')
  const [feedbackName, setFeedbackName] = useState('')
  const [feedbackEmail, setFeedbackEmail] = useState('')
  const [feedbackStatus, setFeedbackStatus] = useState('')
  const [feedbackSubmitting, setFeedbackSubmitting] = useState(false)

  // If already authenticated and visits, give convenient jump or auto redirect
  useEffect(() => {
    if (user) {
      // Let user access dashboard if already authenticated
      navigate('/dashboard', { replace: true })
    }
  }, [user, navigate])

  const storyPreviews = [
    {
      title: 'The Abandoned House',
      kanji: '迷い家',
      genre: 'Mystery',
      setting: 'Autumn · Mountain Pass · Heavy Rain',
      tagline: 'A lantern still burns on the porch. The doors are unlatched.',
      description:
        'A secluded mountain dwelling glowing with soft amber warmth despite being uninhabited for thirty years. Every room stores objects that shift when unobserved.',
      image: '/assets/story-covers/cover-abandoned-house.png',
      status: 'Active Chronicle',
    },
    {
      title: 'The Silent Station',
      kanji: '無人駅',
      genre: 'Psychological Thriller',
      setting: 'Winter · Platform Four · Thick Fog',
      tagline: 'The timetable lists arrivals from dates that have not yet occurred.',
      description:
        'Rain falls endlessly over a rusted railway platform. On the cedar bench rests an unopened letter bearing your name in handwriting you cannot identify.',
      image: '/assets/story-covers/cover-silent-station.png',
      status: 'Archived Story',
    },
    {
      title: 'The Forgotten Village',
      kanji: '隠れ里',
      genre: 'Dark Fantasy',
      setting: 'Twilight · Cedar Grove · Drifting Ash',
      tagline: 'Where moss covers the stone lanterns and the bell tolls once.',
      description:
        'Streets paved in wet cobblestone and cedar needles where shadows linger after the lanterns pass. A promise made here in childhood begins to surface.',
      image: '/assets/story-covers/cover-lost-village.png',
      status: 'New Journey',
    },
  ]

  async function handleFeedbackSubmit(e) {
    e.preventDefault()
    if (feedbackSubmitting) return
    if (!feedbackSubject.trim() || feedbackSubject.trim().length < 2) {
      setFeedbackStatus('error_empty')
      return
    }
    if (!feedbackMessage.trim() || feedbackMessage.trim().length < 5) {
      setFeedbackStatus('error_empty')
      return
    }
    setFeedbackSubmitting(true)
    setFeedbackStatus('')
    try {
      await feedbackApi.submit({
        feedback_type: feedbackType,
        subject: feedbackSubject.trim(),
        message: feedbackMessage.trim(),
        name: feedbackName.trim() || undefined,
        email: feedbackEmail.trim() || undefined,
      })
      setFeedbackStatus('success')
      setFeedbackSubject('')
      setFeedbackMessage('')
      setFeedbackName('')
      setFeedbackEmail('')
    } catch (err) {
      const msg = err.message || ''
      if (msg.includes('429') || msg.toLowerCase().includes('rate limit') || msg.toLowerCase().includes('too many')) {
        setFeedbackStatus('rate_limit')
      } else {
        setFeedbackStatus('error')
      }
    } finally {
      setFeedbackSubmitting(false)
    }
  }

  return (
    <div className="landing-container min-h-screen bg-[#101317] text-[#F1EEE8] font-sans-ui selection:bg-[#A33B42] selection:text-white">
      {/* ─────────────────────────────────────────────────────────────
          1. NAVBAR
      ───────────────────────────────────────────────────────────── */}
      <header className="fixed top-0 left-0 right-0 z-50 border-b border-white/[0.08] bg-[#101317]/85 backdrop-blur-md transition-all">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          {/* Logo & Torii Emblem */}
          <Link to="/" className="group flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-[#C4AD88]/30 bg-[#1B2228] transition-all group-hover:border-[#C4AD88]/80 group-hover:shadow-[0_0_15px_rgba(196,173,136,0.3)]">
              {/* Torii Gate SVG Symbol */}
              <svg className="h-6 w-6 text-[#A33B42] transition group-hover:text-[#C4AD88]" viewBox="0 0 24 24" fill="currentColor">
                <path d="M2 5h20v2H2V5zm3 3h14v2H5V8zm2 3h2v11H7V11zm8 0h2v11h-2V11zM1 3h22v2H1V3z" />
              </svg>
            </div>
            <div>
              <span className="font-cinematic text-xl font-bold tracking-[0.2em] text-[#F1EEE8] group-hover:text-[#C4AD88] transition">
                YŪGEN MAYOIGA
              </span>
              <span className="block text-[10px] tracking-[0.3em] uppercase text-[#858A8D] font-sans-ui">
                幽玄 · 迷い家
              </span>
            </div>
          </Link>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center gap-8 text-sm font-medium text-[#B5B2AC]">
            <a href="#about" className="transition hover:text-[#C4AD88]">
              {t.nav.about}
            </a>
            <a href="#choices" className="transition hover:text-[#C4AD88]">
              {t.nav.features}
            </a>
            <a href="#explore" className="transition hover:text-[#C4AD88]">
              {t.nav.themes}
            </a>
            <a href="#feedback" className="transition hover:text-[#C4AD88]">
              {t.nav.feedback}
            </a>
          </nav>

          {/* Action Links & Language Selector */}
          <div className="hidden md:flex items-center gap-4">
            {/* Language Selector Dropdown */}
            <div className="relative">
              <button
                type="button"
                onClick={() => setLangMenuOpen((v) => !v)}
                className="flex items-center gap-1.5 rounded-md border border-white/10 bg-[#1B2228]/80 px-3 py-1.5 text-xs text-[#B5B2AC] hover:border-[#C4AD88]/40 hover:text-[#F1EEE8] transition"
              >
                <span className="text-[11px] text-[#C4AD88]">語</span>
                <span>{selectedLanguage}</span>
                <svg className={`h-3 w-3 transition ${langMenuOpen ? 'rotate-180' : ''}`} viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
                </svg>
              </button>

              {langMenuOpen && (
                <div className="absolute right-0 mt-2 w-36 rounded-lg border border-white/10 bg-[#1B2228] py-2 shadow-2xl backdrop-blur-xl z-50">
                  {languages.map((l) => (
                    <button
                      key={l.code}
                      type="button"
                      onClick={() => {
                        setSelectedLanguage(l.code)
                        setLangMenuOpen(false)
                      }}
                      className={`flex w-full items-center justify-between px-3 py-1.5 text-left text-xs transition ${
                        selectedLanguage === l.code ? 'bg-[#A33B42]/20 text-[#C4AD88]' : 'text-[#B5B2AC] hover:bg-white/5 hover:text-[#F1EEE8]'
                      }`}
                    >
                      <span>{l.label}</span>
                      <span className="text-[10px] text-[#858A8D]">{l.native}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Login Link */}
            <Link
              to="/login"
              className="text-sm font-medium text-[#D7DCE0] transition hover:text-[#C4AD88] px-3 py-1.5"
            >
              {t.nav.signIn}
            </Link>

            {/* Primary Get Started CTA */}
            <Link
              to="/register"
              className="rounded-lg border border-[#A33B42]/50 bg-[#A33B42] px-5 py-2 text-sm font-semibold text-[#F1EEE8] transition-all hover:bg-[#702B34] hover:shadow-[0_0_20px_rgba(163,59,66,0.5)]"
            >
              {t.nav.createStory}
            </Link>
          </div>

          {/* Mobile Menu Button */}
          <div className="flex md:hidden items-center gap-2">
            <button
              type="button"
              onClick={() => setMobileMenuOpen((v) => !v)}
              className="rounded-lg border border-white/10 p-2 text-[#B5B2AC] hover:text-[#F1EEE8]"
              aria-label="Toggle navigation menu"
            >
              {mobileMenuOpen ? (
                <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              ) : (
                <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              )}
            </button>
          </div>
        </div>

        {/* Mobile Dropdown Menu */}
        {mobileMenuOpen && (
          <div className="border-b border-white/10 bg-[#171C21] px-6 py-5 md:hidden space-y-4">
            <nav className="flex flex-col space-y-3 text-sm text-[#B5B2AC]">
              <a href="#about" onClick={() => setMobileMenuOpen(false)} className="hover:text-[#C4AD88]">About</a>
              <a href="#choices" onClick={() => setMobileMenuOpen(false)} className="hover:text-[#C4AD88]">Branching</a>
              <a href="#characters" onClick={() => setMobileMenuOpen(false)} className="hover:text-[#C4AD88]">Characters</a>
              <a href="#world" onClick={() => setMobileMenuOpen(false)} className="hover:text-[#C4AD88]">World State</a>
              <a href="#explore" onClick={() => setMobileMenuOpen(false)} className="hover:text-[#C4AD88]">Explore</a>
            </nav>
            <div className="pt-4 border-t border-white/10 flex flex-col gap-3">
              <Link
                to="/login"
                className="w-full text-center py-2 text-sm text-[#D7DCE0] hover:text-[#C4AD88]"
              >
                Sign In
              </Link>
              <Link
                to="/register"
                className="w-full text-center rounded-lg bg-[#A33B42] py-2.5 text-sm font-semibold text-white shadow"
              >
                Begin Your Story
              </Link>
            </div>
          </div>
        )}
      </header>

      {/* ─────────────────────────────────────────────────────────────
          2. HERO SECTION (FULL SCREEN)
      ───────────────────────────────────────────────────────────── */}
      <section className="relative flex min-h-screen items-center justify-center overflow-hidden pt-20">
        {/* Background Image with Layered Overlays */}
        <div
          className="absolute inset-0 bg-cover bg-center bg-no-repeat transition-transform duration-1000 scale-105 filter brightness-95 contrast-120"
          style={{
            backgroundImage: "url('/assets/backgrounds/landing-hero.png')",
          }}
        />

        {/* Cinematic Darkness & Vignette Gradients */}
        <div className="absolute inset-0 bg-gradient-to-t from-[#101317] via-[#101317]/40 to-transparent" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,transparent_30%,#101317_90%)]" />

        {/* Ambient Mist Drift Overlay */}
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top,rgba(196,173,136,0.08),transparent_70%)] animate-ambient-glow" />

        {/* Hero Content */}
        <div className="relative z-10 mx-auto max-w-4xl px-6 py-24 text-center">
          {/* Subtle Torii / Kanji Banner */}
          <div className="mb-6 inline-flex items-center gap-3 rounded-full border border-[#C4AD88]/30 bg-[#101317]/80 px-4 py-1.5 backdrop-blur-md">
            <span className="h-1.5 w-1.5 rounded-full bg-[#A33B42] animate-pulse" />
            <span className="font-sans-ui text-xs tracking-[0.3em] uppercase text-[#C4AD88]">
              {t.hero.eyebrow}
            </span>
            <span className="text-xs text-[#858A8D]">· 幽玄 迷い家</span>
          </div>

          {/* Main Title */}
          <h1 className="font-cinematic text-5xl font-semibold tracking-wider text-[#F1EEE8] sm:text-7xl lg:text-8xl drop-shadow-[0_4px_30px_rgba(0,0,0,0.8)]">
            {t.hero.title}
          </h1>

          {/* Atmospheric Tagline */}
          <p className="mx-auto mt-6 max-w-2xl font-cinematic text-xl italic tracking-wide text-[#D7DCE0] sm:text-2xl">
            “{t.footer.tagline}”
          </p>

          <p className="mx-auto mt-4 max-w-xl text-sm leading-relaxed text-[#B5B2AC]">
            {t.hero.subtitle}
          </p>

          {/* Action Buttons */}
          <div className="mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row">
            <Link
              to="/register"
              className="group flex w-full sm:w-auto items-center justify-center gap-3 rounded-lg border border-[#A33B42] bg-[#A33B42] px-8 py-3.5 text-base font-semibold text-[#F1EEE8] transition-all hover:bg-[#702B34] hover:shadow-[0_0_25px_rgba(163,59,66,0.6)]"
            >
              <span>{t.hero.primaryCta}</span>
              <span className="text-[#C4AD88] transition-transform group-hover:translate-x-1">→</span>
            </Link>

            <a
              href="#about"
              className="flex w-full sm:w-auto items-center justify-center gap-2 rounded-lg border border-white/15 bg-[#1B2228]/60 px-7 py-3.5 text-base font-medium text-[#D7DCE0] backdrop-blur-sm transition hover:border-[#C4AD88]/50 hover:bg-[#1B2228] hover:text-[#F1EEE8]"
            >
              <span>{t.hero.secondaryCta}</span>
              <span className="text-xs text-[#858A8D]">↓</span>
            </a>
          </div>

          {/* Bottom Atmosphere Metadata */}
          <div className="mt-16 flex items-center justify-center gap-8 text-xs text-[#858A8D] font-mono">
            <div>
              <span className="text-[#C4AD88]">Atmosphere</span>: Night Village
            </div>
            <div className="hidden sm:block">·</div>
            <div className="hidden sm:block">
              <span className="text-[#C4AD88]">Engine</span>: Living Narrative Matrix
            </div>
            <div>·</div>
            <div>
              <span className="text-[#C4AD88]">Script</span>: English · 日本語
            </div>
          </div>
        </div>

        {/* Scroll down indicator */}
        <div className="absolute bottom-6 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2 text-xs text-[#858A8D] opacity-75">
          <span className="tracking-[0.25em] uppercase text-[10px]">Descend</span>
          <div className="h-8 w-4 rounded-full border border-white/20 p-1 flex justify-center">
            <div className="h-1.5 w-1 rounded-full bg-[#C4AD88] animate-bounce" />
          </div>
        </div>
      </section>

      {/* ─────────────────────────────────────────────────────────────
          3. SECTION 1 — WHAT IS YŪGEN MAYOIGA?
      ───────────────────────────────────────────────────────────── */}
      <section id="about" className="relative border-t border-white/[0.08] bg-[#101317] px-6 py-28">
        <div className="mx-auto max-w-7xl">
          {/* Section Header */}
          <div className="max-w-2xl">
            <p className="text-xs uppercase tracking-[0.3em] text-[#C4AD88]">The Sanctuary</p>
            <h2 className="mt-3 font-cinematic text-4xl font-semibold tracking-wide sm:text-5xl text-[#F1EEE8]">
              What is Yūgen Mayoiga?
            </h2>
            <p className="mt-4 text-base leading-relaxed text-[#B5B2AC]">
              In Japanese folklore, the <em className="text-[#C4AD88] not-italic">Mayoiga</em> is an abandoned estate hidden deep in mist-shrouded peaks, appearing only to travelers who have lost their path. Those who enter leave with treasures of fortune—or curses of their own making.
            </p>
          </div>

          {/* Pillars Grid */}
          <div className="mt-16 grid gap-8 md:grid-cols-3">
            {/* Pillar 1 */}
            <div className="group rounded-2xl border border-white/[0.08] bg-[#171C21] p-8 transition-all hover:border-[#C4AD88]/40 hover:bg-[#1B2228] hover:shadow-[0_10px_30px_rgba(0,0,0,0.5)]">
              <div className="flex h-12 w-12 items-center justify-center rounded-lg border border-[#C4AD88]/30 bg-[#101317] text-[#C4AD88]">
                <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                </svg>
              </div>
              <h3 className="mt-6 font-cinematic text-2xl font-semibold text-[#F1EEE8] group-hover:text-[#C4AD88] transition">
                Interactive Branching Narrative
              </h3>
              <p className="mt-3 text-sm leading-relaxed text-[#858A8D]">
                Every scene offers decisive crossroads. Stories do not simply diverge; choices echo across turns, altering dialogue tone, locked rooms, and historical secrets.
              </p>
            </div>

            {/* Pillar 2 */}
            <div className="group rounded-2xl border border-white/[0.08] bg-[#171C21] p-8 transition-all hover:border-[#C4AD88]/40 hover:bg-[#1B2228] hover:shadow-[0_10px_30px_rgba(0,0,0,0.5)]">
              <div className="flex h-12 w-12 items-center justify-center rounded-lg border border-[#C4AD88]/30 bg-[#101317] text-[#A33B42]">
                <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
                </svg>
              </div>
              <h3 className="mt-6 font-cinematic text-2xl font-semibold text-[#F1EEE8] group-hover:text-[#C4AD88] transition">
                Living Emotional Matrix
              </h3>
              <p className="mt-3 text-sm leading-relaxed text-[#858A8D]">
                Characters are governed by psychological engines tracking Trust, Fear, Affection, and Suspicion. A companion who fears you will withhold vital clues when the night falls.
              </p>
            </div>

            {/* Pillar 3 */}
            <div className="group rounded-2xl border border-white/[0.08] bg-[#171C21] p-8 transition-all hover:border-[#C4AD88]/40 hover:bg-[#1B2228] hover:shadow-[0_10px_30px_rgba(0,0,0,0.5)]">
              <div className="flex h-12 w-12 items-center justify-center rounded-lg border border-[#C4AD88]/30 bg-[#101317] text-[#D7DCE0]">
                <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
                </svg>
              </div>
              <h3 className="mt-6 font-cinematic text-2xl font-semibold text-[#F1EEE8] group-hover:text-[#C4AD88] transition">
                Atmospheric World State
              </h3>
              <p className="mt-3 text-sm leading-relaxed text-[#858A8D]">
                The world responds to your actions. Lanterns burn out, rain swells mountain streams, and the Yūgen Meter measures the boundary between reality and the supernatural.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ─────────────────────────────────────────────────────────────
          4. SECTION 2 — YOUR CHOICES SHAPE THE STORY
      ───────────────────────────────────────────────────────────── */}
      <section id="choices" className="relative border-t border-white/[0.08] bg-[#171C21] px-6 py-28 overflow-hidden">
        {/* Subtle background glow */}
        <div className="pointer-events-none absolute right-0 top-1/2 -translate-y-1/2 w-96 h-96 rounded-full bg-[#A33B42]/10 blur-[120px]" />

        <div className="mx-auto max-w-7xl">
          <div className="grid gap-14 lg:grid-cols-2 lg:items-center">
            {/* Left Narrative Text */}
            <div>
              <p className="text-xs uppercase tracking-[0.3em] text-[#A33B42]">Branching Architecture</p>
              <h2 className="mt-3 font-cinematic text-4xl font-semibold tracking-wide sm:text-5xl text-[#F1EEE8]">
                Your Choices Shape the Story
              </h2>
              <p className="mt-5 text-base leading-relaxed text-[#B5B2AC]">
                Unlike linear visual novels, Yūgen Mayoiga models decisions as structural nodes within an interconnected world graph. Every choice triggers secondary reactions across characters and world parameters.
              </p>

              <div className="mt-8 space-y-4">
                <div className="flex items-start gap-4 rounded-xl border border-white/5 bg-[#101317]/60 p-4">
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-[#A33B42]/20 text-[#A33B42] font-semibold text-xs">
                    01
                  </div>
                  <div>
                    <h4 className="font-cinematic text-lg font-medium text-[#F1EEE8]">Irreversible Consequences</h4>
                    <p className="text-xs text-[#858A8D] mt-1">Doors locked behind you remain sealed. Broken relics cannot be repaired.</p>
                  </div>
                </div>

                <div className="flex items-start gap-4 rounded-xl border border-white/5 bg-[#101317]/60 p-4">
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-[#C4AD88]/20 text-[#C4AD88] font-semibold text-xs">
                    02
                  </div>
                  <div>
                    <h4 className="font-cinematic text-lg font-medium text-[#F1EEE8]">Divergent Endings</h4>
                    <p className="text-xs text-[#858A8D] mt-1">Multiple authentic resolutions determined by accumulated memory and character trust.</p>
                  </div>
                </div>

                <div className="flex items-start gap-4 rounded-xl border border-white/5 bg-[#101317]/60 p-4">
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-[#D7DCE0]/20 text-[#D7DCE0] font-semibold text-xs">
                    03
                  </div>
                  <div>
                    <h4 className="font-cinematic text-lg font-medium text-[#F1EEE8]">Branching Replayability</h4>
                    <p className="text-xs text-[#858A8D] mt-1">Return to your story archive to inspect the branching tree and uncover unexplored paths.</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Right Visual Branching Diagram (Stylized UI graph representation) */}
            <div className="rounded-2xl border border-white/[0.08] bg-[#101317] p-8 shadow-2xl relative">
              <div className="flex items-center justify-between border-b border-white/[0.08] pb-4">
                <div className="flex items-center gap-2">
                  <span className="h-2.5 w-2.5 rounded-full bg-[#A33B42]" />
                  <span className="text-xs font-mono uppercase tracking-wider text-[#C4AD88]">Story Graph Visualization</span>
                </div>
                <span className="rounded-full bg-white/5 px-2.5 py-1 text-[10px] text-[#858A8D]">Live Tree</span>
              </div>

              {/* Node Graph Mockup */}
              <div className="mt-8 space-y-6">
                {/* Node Root */}
                <div className="flex items-center gap-4">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-[#C4AD88]/50 bg-[#1B2228] text-xs font-mono text-[#C4AD88]">
                    01
                  </div>
                  <div className="flex-1 rounded-lg border border-white/10 bg-[#1B2228]/80 p-3">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-[#F1EEE8]">The Silent Platform</span>
                      <span className="text-[10px] text-[#C4AD88]">Visited</span>
                    </div>
                    <p className="text-[11px] text-[#858A8D] mt-0.5">A letter is found on the rain-soaked bench.</p>
                  </div>
                </div>

                {/* Branches Connector */}
                <div className="ml-5 border-l-2 border-dashed border-[#C4AD88]/30 pl-8 space-y-5">
                  {/* Branch A (Chosen) */}
                  <div className="flex items-center gap-4">
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-[#A33B42] bg-[#A33B42]/20 text-xs font-mono text-[#A33B42]">
                      02a
                    </div>
                    <div className="flex-1 rounded-lg border border-[#A33B42]/40 bg-[#1B2228] p-3 shadow-[0_0_15px_rgba(163,59,66,0.15)]">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold text-[#F1EEE8]">Follow the Distant Bell</span>
                        <span className="text-[10px] text-[#A33B42]">Active Path</span>
                      </div>
                      <p className="text-[11px] text-[#B5B2AC] mt-0.5">Descend into the forgotten subway shrine.</p>
                    </div>
                  </div>

                  {/* Branch B (Locked / Alternative) */}
                  <div className="flex items-center gap-4 opacity-50">
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-white/10 bg-[#101317] text-xs font-mono text-[#858A8D]">
                      02b
                    </div>
                    <div className="flex-1 rounded-lg border border-white/5 bg-[#171C21] p-3">
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-[#858A8D]">Unfold the Wax Letter</span>
                        <span className="text-[10px] text-[#858A8D]">Alternate Branch</span>
                      </div>
                      <p className="text-[11px] text-[#858A8D] mt-0.5">Unlocks memory: "The Vow of Rain".</p>
                    </div>
                  </div>

                  {/* Sub Branch Resolution */}
                  <div className="ml-4 border-l border-white/10 pl-6">
                    <div className="flex items-center gap-3">
                      <div className="h-2 w-2 rounded-full bg-[#C4AD88]" />
                      <span className="text-xs font-cinematic italic text-[#C4AD88]">
                        Outcome: The Gilded Pact — Character Fear +20%, Trust +15%
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ─────────────────────────────────────────────────────────────
          5. SECTION 3 — CHARACTERS REMEMBER (NO ANIME PORTRAITS)
      ───────────────────────────────────────────────────────────── */}
      <section id="characters" className="relative border-t border-white/[0.08] bg-[#101317] px-6 py-28">
        <div className="mx-auto max-w-7xl">
          <div className="text-center max-w-3xl mx-auto">
            <p className="text-xs uppercase tracking-[0.3em] text-[#C4AD88]">Psychological Dossier</p>
            <h2 className="mt-3 font-cinematic text-4xl font-semibold tracking-wide sm:text-5xl text-[#F1EEE8]">
              Characters Remember
            </h2>
            <p className="mt-4 text-base leading-relaxed text-[#B5B2AC]">
              No character in Mayoiga is a passive prop. Their internal emotional states evolve with every sentence spoken and every hesitation observed.
            </p>
          </div>

          {/* Character Intelligence Cards — Clean, Elegant Data Visualizations (Zero Anime/Face Portraits) */}
          <div className="mt-16 grid gap-8 md:grid-cols-2">
            {/* Character Dossier 1: Aiko */}
            <div className="rounded-2xl border border-white/[0.08] bg-[#171C21] p-8 transition hover:border-[#C4AD88]/30">
              <div className="flex items-start justify-between border-b border-white/[0.08] pb-5">
                <div>
                  <span className="text-[10px] uppercase tracking-[0.25em] text-[#C4AD88]">Companion Entity</span>
                  <h3 className="font-cinematic text-3xl font-semibold text-[#F1EEE8] mt-1">Aiko</h3>
                  <p className="text-xs text-[#858A8D] mt-0.5">The Keeper of Whispers · Role: Companion</p>
                </div>
                <span className="rounded-full border border-[#A33B42]/50 bg-[#A33B42]/20 px-3 py-1 text-xs font-medium text-[#F1EEE8]">
                  Fearful & Guarded
                </span>
              </div>

              {/* Emotion Metrics */}
              <div className="mt-6 space-y-4">
                <div>
                  <div className="flex justify-between text-xs mb-1.5">
                    <span className="text-[#B5B2AC]">Trust Level</span>
                    <span className="font-mono text-[#C4AD88]">72%</span>
                  </div>
                  <div className="h-1.5 w-full rounded-full bg-white/5 overflow-hidden">
                    <div className="h-full rounded-full bg-[#C4AD88] transition-all" style={{ width: '72%' }} />
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-xs mb-1.5">
                    <span className="text-[#B5B2AC]">Fear Indicator</span>
                    <span className="font-mono text-[#A33B42]">58%</span>
                  </div>
                  <div className="h-1.5 w-full rounded-full bg-white/5 overflow-hidden">
                    <div className="h-full rounded-full bg-[#A33B42] transition-all" style={{ width: '58%' }} />
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-xs mb-1.5">
                    <span className="text-[#B5B2AC]">Affection</span>
                    <span className="font-mono text-[#D7DCE0]">80%</span>
                  </div>
                  <div className="h-1.5 w-full rounded-full bg-white/5 overflow-hidden">
                    <div className="h-full rounded-full bg-[#D7DCE0] transition-all" style={{ width: '80%' }} />
                  </div>
                </div>
              </div>

              {/* Behavior & Memories */}
              <div className="mt-6 border-t border-white/[0.08] pt-5 space-y-3">
                <div className="text-xs">
                  <span className="text-[#858A8D] block text-[10px] uppercase tracking-wider">Observed Behavior</span>
                  <span className="text-[#D7DCE0] mt-1 block">
                    Avoids the east corridor; steps closer when the thunder roars.
                  </span>
                </div>
                <div className="text-xs">
                  <span className="text-[#858A8D] block text-[10px] uppercase tracking-wider">Relevant Stored Memory</span>
                  <span className="text-[#C4AD88] mt-1 block italic font-cinematic text-sm">
                    “The Vow in the Rain: Remembers you refused to abandon the bell tower.”
                  </span>
                </div>
              </div>
            </div>

            {/* Character Dossier 2: The Caretaker */}
            <div className="rounded-2xl border border-white/[0.08] bg-[#171C21] p-8 transition hover:border-[#C4AD88]/30">
              <div className="flex items-start justify-between border-b border-white/[0.08] pb-5">
                <div>
                  <span className="text-[10px] uppercase tracking-[0.25em] text-[#C4AD88]">Guardian Presence</span>
                  <h3 className="font-cinematic text-3xl font-semibold text-[#F1EEE8] mt-1">The Caretaker</h3>
                  <p className="text-xs text-[#858A8D] mt-0.5">Master of Mayoiga · Role: Threshold Guardian</p>
                </div>
                <span className="rounded-full border border-white/20 bg-white/5 px-3 py-1 text-xs font-medium text-[#D7DCE0]">
                  Vigilant & Calculating
                </span>
              </div>

              {/* Emotion Metrics */}
              <div className="mt-6 space-y-4">
                <div>
                  <div className="flex justify-between text-xs mb-1.5">
                    <span className="text-[#B5B2AC]">Trust Level</span>
                    <span className="font-mono text-[#C4AD88]">35%</span>
                  </div>
                  <div className="h-1.5 w-full rounded-full bg-white/5 overflow-hidden">
                    <div className="h-full rounded-full bg-[#C4AD88] transition-all" style={{ width: '35%' }} />
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-xs mb-1.5">
                    <span className="text-[#B5B2AC]">Suspicion</span>
                    <span className="font-mono text-[#A33B42]">84%</span>
                  </div>
                  <div className="h-1.5 w-full rounded-full bg-white/5 overflow-hidden">
                    <div className="h-full rounded-full bg-[#A33B42] transition-all" style={{ width: '84%' }} />
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-xs mb-1.5">
                    <span className="text-[#B5B2AC]">Affection</span>
                    <span className="font-mono text-[#D7DCE0]">15%</span>
                  </div>
                  <div className="h-1.5 w-full rounded-full bg-white/5 overflow-hidden">
                    <div className="h-full rounded-full bg-[#D7DCE0] transition-all" style={{ width: '15%' }} />
                  </div>
                </div>
              </div>

              {/* Behavior & Memories */}
              <div className="mt-6 border-t border-white/[0.08] pt-5 space-y-3">
                <div className="text-xs">
                  <span className="text-[#858A8D] block text-[10px] uppercase tracking-wider">Observed Behavior</span>
                  <span className="text-[#D7DCE0] mt-1 block">
                    Watches the hearth fire; counts the bronze keys on his iron ring.
                  </span>
                </div>
                <div className="text-xs">
                  <span className="text-[#858A8D] block text-[10px] uppercase tracking-wider">Relevant Stored Memory</span>
                  <span className="text-[#C4AD88] mt-1 block italic font-cinematic text-sm">
                    “The Broken Wax Seal: Saw you inspect the forbidden cedar ledger.”
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ─────────────────────────────────────────────────────────────
          6. SECTION 4 — A WORLD THAT CHANGES
      ───────────────────────────────────────────────────────────── */}
      <section id="world" className="relative border-t border-white/[0.08] bg-[#171C21] px-6 py-28">
        <div className="mx-auto max-w-7xl">
          <div className="max-w-3xl">
            <p className="text-xs uppercase tracking-[0.3em] text-[#C4AD88]">Living Universe</p>
            <h2 className="mt-3 font-cinematic text-4xl font-semibold tracking-wide sm:text-5xl text-[#F1EEE8]">
              A World That Changes
            </h2>
            <p className="mt-4 text-base leading-relaxed text-[#B5B2AC]">
              Mayoiga is not a fixed backdrop. Events, choices, world states, memories, and timeline anchors form a continuously evaluating systemic engine.
            </p>
          </div>

          {/* Interconnected Systemic Matrix Grid */}
          <div className="mt-16 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {/* Box 1: Dynamic Events */}
            <div className="rounded-xl border border-white/[0.08] bg-[#101317] p-6 hover:border-[#C4AD88]/30 transition">
              <div className="text-[#C4AD88] font-mono text-xs uppercase tracking-wider">01 · Events</div>
              <h4 className="mt-3 font-cinematic text-xl font-medium text-[#F1EEE8]">Reactive Triggers</h4>
              <p className="mt-2 text-xs leading-relaxed text-[#858A8D]">
                The midnight bell rings only if the shrine gate was left unlatched. Random elements are bound to causal story logic.
              </p>
              <div className="mt-4 rounded bg-[#1B2228] p-2.5 text-[11px] font-mono text-[#D7DCE0]">
                trigger: <span className="text-[#C4AD88]">bell_toll_midnight</span>
              </div>
            </div>

            {/* Box 2: World State */}
            <div className="rounded-xl border border-white/[0.08] bg-[#101317] p-6 hover:border-[#C4AD88]/30 transition">
              <div className="text-[#A33B42] font-mono text-xs uppercase tracking-wider">02 · State</div>
              <h4 className="mt-3 font-cinematic text-xl font-medium text-[#F1EEE8]">Environmental Variables</h4>
              <p className="mt-2 text-xs leading-relaxed text-[#858A8D]">
                Weather cycles from damp mist to violent tempest; lanterns extinguish as time slips beyond midnight.
              </p>
              <div className="mt-4 rounded bg-[#1B2228] p-2.5 text-[11px] font-mono text-[#D7DCE0]">
                weather: <span className="text-[#A33B42]">torrential_rain</span>
              </div>
            </div>

            {/* Box 3: Memories */}
            <div className="rounded-xl border border-white/[0.08] bg-[#101317] p-6 hover:border-[#C4AD88]/30 transition">
              <div className="text-[#D7DCE0] font-mono text-xs uppercase tracking-wider">03 · Memories</div>
              <h4 className="mt-3 font-cinematic text-xl font-medium text-[#F1EEE8]">Permanent Impressions</h4>
              <p className="mt-2 text-xs leading-relaxed text-[#858A8D]">
                Key narrative breakthroughs are saved as memories, unlocking hidden dialogue and revelation branches later.
              </p>
              <div className="mt-4 rounded bg-[#1B2228] p-2.5 text-[11px] font-mono text-[#D7DCE0]">
                memory: <span className="text-[#D7DCE0]">the_brass_key</span>
              </div>
            </div>

            {/* Box 4: Timeline */}
            <div className="rounded-xl border border-white/[0.08] bg-[#101317] p-6 hover:border-[#C4AD88]/30 transition">
              <div className="text-[#C4AD88] font-mono text-xs uppercase tracking-wider">04 · Timeline</div>
              <h4 className="mt-3 font-cinematic text-xl font-medium text-[#F1EEE8]">Temporal Progression</h4>
              <p className="mt-2 text-xs leading-relaxed text-[#858A8D]">
                Track the turn-by-turn evolution of your journey. Review past choices and view how the branches were reached.
              </p>
              <div className="mt-4 rounded bg-[#1B2228] p-2.5 text-[11px] font-mono text-[#D7DCE0]">
                turn: <span className="text-[#C4AD88]">chapter_03_active</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ─────────────────────────────────────────────────────────────
          7. SECTION 5 — DISCOVER YOUR STORY (ENVIRONMENTAL COVERS)
      ───────────────────────────────────────────────────────────── */}
      <section id="explore" className="relative border-t border-white/[0.08] bg-[#101317] px-6 py-28">
        <div className="mx-auto max-w-7xl">
          <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 border-b border-white/[0.08] pb-8">
            <div>
              <p className="text-xs uppercase tracking-[0.3em] text-[#C4AD88]">Atmospheric Chronicles</p>
              <h2 className="mt-3 font-cinematic text-4xl font-semibold tracking-wide sm:text-5xl text-[#F1EEE8]">
                Discover Your Story
              </h2>
              <p className="mt-3 text-sm text-[#858A8D]">
                Select an environmental setting and begin your personalized journey into the forgotten estate.
              </p>
            </div>
            <Link
              to="/register"
              className="inline-flex items-center gap-2 text-sm font-semibold text-[#C4AD88] hover:text-[#D9C9A8] transition"
            >
              <span>Explore full library</span>
              <span>→</span>
            </Link>
          </div>

          {/* Environmental Story Cards */}
          <div className="mt-12 grid gap-8 md:grid-cols-3">
            {storyPreviews.map((story, index) => (
              <div
                key={story.title}
                className="group flex flex-col justify-between overflow-hidden rounded-2xl border border-white/[0.08] bg-[#171C21] transition-all hover:border-[#C4AD88]/40 hover:shadow-[0_15px_35px_rgba(0,0,0,0.6)]"
              >
                {/* Environmental Image Header */}
                <div className="relative h-56 w-full overflow-hidden bg-[#101317]">
                  <img
                    src={story.image}
                    alt={story.title}
                    className="h-full w-full object-cover transition-transform duration-700 group-hover:scale-105"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-[#171C21] via-transparent to-black/40" />

                  {/* Japanese Kanji Stamp */}
                  <span className="absolute top-4 right-4 rounded-md border border-white/20 bg-black/60 px-2 py-1 font-cinematic text-xs text-[#C4AD88] backdrop-blur-sm">
                    {story.kanji}
                  </span>

                  {/* Genre Tag */}
                  <span className="absolute bottom-3 left-4 rounded-full bg-[#A33B42] px-3 py-0.5 text-[11px] font-semibold text-white">
                    {story.genre}
                  </span>
                </div>

                {/* Card Body */}
                <div className="flex flex-1 flex-col justify-between p-6">
                  <div>
                    <span className="text-[10px] uppercase tracking-wider text-[#858A8D]">{story.setting}</span>
                    <h3 className="font-cinematic text-2xl font-semibold text-[#F1EEE8] group-hover:text-[#C4AD88] transition mt-1">
                      {story.title}
                    </h3>
                    <p className="mt-2 font-cinematic text-sm italic text-[#D7DCE0]">
                      "{story.tagline}"
                    </p>
                    <p className="mt-3 text-xs leading-relaxed text-[#858A8D]">
                      {story.description}
                    </p>
                  </div>

                  {/* Card Action */}
                  <div className="mt-6 pt-4 border-t border-white/[0.08]">
                    <Link
                      to="/register"
                      className="flex items-center justify-between text-xs font-semibold text-[#F1EEE8] group-hover:text-[#C4AD88] transition"
                    >
                      <span>Begin This Journey</span>
                      <span>→</span>
                    </Link>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ─────────────────────────────────────────────────────────────
          8. FINAL CALL TO ACTION (CINEMATIC)
      ───────────────────────────────────────────────────────────── */}
      <section className="relative border-t border-white/[0.08] overflow-hidden py-32 px-6 text-center">
        {/* Background Image with Dark Vignette */}
        <div
          className="absolute inset-0 bg-cover bg-center bg-no-repeat opacity-30"
          style={{ backgroundImage: "url('/assets/backgrounds/landing-hero.png')" }}
        />
        <div className="absolute inset-0 bg-gradient-to-t from-[#101317] via-[#101317]/90 to-[#101317]" />

        <div className="relative z-10 mx-auto max-w-3xl">
          <div className="mb-6 inline-flex h-12 w-12 items-center justify-center rounded-full border border-[#C4AD88]/30 bg-[#1B2228] text-[#C4AD88]">
            <svg className="h-6 w-6" viewBox="0 0 24 24" fill="currentColor">
              <path d="M2 5h20v2H2V5zm3 3h14v2H5V8zm2 3h2v11H7V11zm8 0h2v11h-2V11zM1 3h22v2H1V3z" />
            </svg>
          </div>

          <h2 className="font-cinematic text-4xl font-semibold tracking-wide text-[#F1EEE8] sm:text-6xl">
            Every choice leaves something behind.
          </h2>

          <p className="mx-auto mt-6 max-w-xl text-base leading-relaxed text-[#B5B2AC]">
            The estate does not reveal itself twice in the same manner. Step through the gate and discover what waits in the silence.
          </p>

          <div className="mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row">
            <Link
              to="/register"
              className="rounded-lg border border-[#A33B42] bg-[#A33B42] px-9 py-4 text-base font-semibold text-[#F1EEE8] transition-all hover:bg-[#702B34] hover:shadow-[0_0_30px_rgba(163,59,66,0.6)]"
            >
              Begin Your Story
            </Link>

            <Link
              to="/login"
              className="rounded-lg border border-white/15 bg-[#1B2228]/80 px-8 py-4 text-base font-medium text-[#D7DCE0] hover:border-[#C4AD88]/50 hover:text-[#F1EEE8] transition"
            >
              Return to Sanctuary (Sign In)
            </Link>
          </div>
        </div>
      </section>

      {/* ─────────────────────────────────────────────────────────────
          8b. FEEDBACK FORM
      ───────────────────────────────────────────────────────────── */}
      <section id="feedback" className="py-24 px-6 bg-[#13181E]">
        <div className="mx-auto max-w-2xl">
          <div className="text-center mb-10">
            <div className="text-xs uppercase tracking-[0.3em] text-[#A33B42] mb-3 font-sans-ui">幽玄 · 感想</div>
            <h2 className="font-cinematic text-3xl font-bold tracking-wide text-[#F1EEE8] mb-4">{t.feedback.heading}</h2>
            <p className="text-sm text-[#858A8D] leading-relaxed">
              {t.feedback.subtitle}
            </p>
          </div>

          {feedbackStatus === 'success' && (
            <div className="mb-6 rounded-lg border border-[#C4AD88]/30 bg-[#C4AD88]/10 px-5 py-4 text-sm text-[#C4AD88] text-center">
              {t.feedback.success}
            </div>
          )}
          {feedbackStatus === 'rate_limit' && (
            <div className="mb-6 rounded-lg border border-[#A33B42]/30 bg-[#A33B42]/10 px-5 py-4 text-sm text-[#E8A0A5] text-center">
              {t.feedback.errorRate}
            </div>
          )}
          {(feedbackStatus === 'error' || feedbackStatus === 'error_empty') && (
            <div className="mb-6 rounded-lg border border-[#A33B42]/30 bg-[#A33B42]/10 px-5 py-4 text-sm text-[#E8A0A5] text-center">
              {feedbackStatus === 'error_empty' ? t.feedback.errorEmpty : 'Failed to submit. Please try again.'}
            </div>
          )}

          <form onSubmit={handleFeedbackSubmit} className="space-y-5">
            <div>
              <label className="block text-xs uppercase tracking-wider text-[#858A8D] mb-2">{t.feedback.typeLabel}</label>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                {[
                  { value: 'Bug Report', label: t.feedback.types[0] },
                  { value: 'Technical Issue', label: t.feedback.types[1] },
                  { value: 'Suggestion', label: t.feedback.types[2] },
                  { value: 'Other', label: t.feedback.types[3] },
                ].map((opt) => (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => setFeedbackType(opt.value)}
                    className={`rounded border px-3 py-2 text-xs transition text-left ${
                      feedbackType === opt.value
                        ? 'border-[#A33B42] bg-[#A33B42]/20 text-[#F1EEE8]'
                        : 'border-white/10 text-[#858A8D] hover:border-white/20 hover:text-[#B5B2AC]'
                    }`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-xs uppercase tracking-wider text-[#858A8D] mb-2">{t.feedback.subjectLabel} *</label>
              <input
                type="text"
                value={feedbackSubject}
                onChange={(e) => setFeedbackSubject(e.target.value)}
                placeholder={t.feedback.subjectPlaceholder}
                className="w-full rounded-lg border border-white/10 bg-[#1B2228] px-4 py-2.5 text-sm text-[#F1EEE8] placeholder:text-[#555B61] focus:border-[#C4AD88]/40 focus:outline-none focus:ring-1 focus:ring-[#C4AD88]/20 transition"
              />
            </div>

            <div>
              <label className="block text-xs uppercase tracking-wider text-[#858A8D] mb-2">{t.feedback.messageLabel} *</label>
              <textarea
                value={feedbackMessage}
                onChange={(e) => setFeedbackMessage(e.target.value)}
                placeholder={t.feedback.messagePlaceholder}
                rows={4}
                className="w-full rounded-lg border border-white/10 bg-[#1B2228] px-4 py-2.5 text-sm text-[#F1EEE8] placeholder:text-[#555B61] focus:border-[#C4AD88]/40 focus:outline-none focus:ring-1 focus:ring-[#C4AD88]/20 transition resize-none"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs uppercase tracking-wider text-[#858A8D] mb-2">{t.feedback.nameLabel}</label>
                <input
                  type="text"
                  value={feedbackName}
                  onChange={(e) => setFeedbackName(e.target.value)}
                  placeholder={t.feedback.namePlaceholder}
                  className="w-full rounded-lg border border-white/10 bg-[#1B2228] px-4 py-2.5 text-sm text-[#F1EEE8] placeholder:text-[#555B61] focus:border-[#C4AD88]/40 focus:outline-none transition"
                />
              </div>
              <div>
                <label className="block text-xs uppercase tracking-wider text-[#858A8D] mb-2">{t.feedback.emailLabel}</label>
                <input
                  type="email"
                  value={feedbackEmail}
                  onChange={(e) => setFeedbackEmail(e.target.value)}
                  placeholder={t.feedback.emailPlaceholder}
                  className="w-full rounded-lg border border-white/10 bg-[#1B2228] px-4 py-2.5 text-sm text-[#F1EEE8] placeholder:text-[#555B61] focus:border-[#C4AD88]/40 focus:outline-none transition"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={feedbackSubmitting}
              className="w-full rounded-lg border border-[#A33B42]/50 bg-[#A33B42] px-6 py-3 text-sm font-semibold text-[#F1EEE8] transition-all hover:bg-[#702B34] hover:shadow-[0_0_20px_rgba(163,59,66,0.4)] disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {feedbackSubmitting ? t.feedback.submitting : t.feedback.submit}
            </button>
          </form>
        </div>
      </section>

      {/* ─────────────────────────────────────────────────────────────
          9. FOOTER
      ───────────────────────────────────────────────────────────── */}
      <footer className="border-t border-white/[0.08] bg-[#0c0e11] px-6 py-16 text-sm text-[#858A8D]">
        <div className="mx-auto max-w-7xl">
          <div className="grid gap-12 sm:grid-cols-2 lg:grid-cols-5">
            {/* Brand Column */}
            <div className="lg:col-span-2 space-y-4">
              <div className="flex items-center gap-3">
                <div className="flex h-8 w-8 items-center justify-center rounded border border-[#C4AD88]/30 bg-[#1B2228] text-[#C4AD88]">
                  <svg className="h-5 w-5" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M2 5h20v2H2V5zm3 3h14v2H5V8zm2 3h2v11H7V11zm8 0h2v11h-2V11zM1 3h22v2H1V3z" />
                  </svg>
                </div>
                <span className="font-cinematic text-lg font-bold tracking-[0.2em] text-[#F1EEE8]">
                  YŪGEN MAYOIGA
                </span>
              </div>
              <p className="max-w-sm text-xs leading-relaxed text-[#858A8D]">
                A psychological branching narrative sanctuary where environmental atmosphere and character memory shape your fate.
              </p>
              <p className="text-[11px] font-mono text-[#C4AD88]/70">
                幽玄 (Yūgen) · Deep grace & subtlety
              </p>
            </div>

            {/* Navigation Column */}
            <div className="space-y-3">
              <h5 className="text-xs uppercase tracking-wider text-[#F1EEE8] font-semibold">Narrative</h5>
              <ul className="space-y-2 text-xs">
                <li><a href="#about" className="hover:text-[#C4AD88] transition">About the Estate</a></li>
                <li><a href="#choices" className="hover:text-[#C4AD88] transition">Branching Graph</a></li>
                <li><a href="#characters" className="hover:text-[#C4AD88] transition">Character Dossiers</a></li>
                <li><a href="#world" className="hover:text-[#C4AD88] transition">Living World State</a></li>
                <li><a href="#explore" className="hover:text-[#C4AD88] transition">Chronicles</a></li>
              </ul>
            </div>

            {/* Access & Auth Column */}
            <div className="space-y-3">
              <h5 className="text-xs uppercase tracking-wider text-[#F1EEE8] font-semibold">Sanctuary</h5>
              <ul className="space-y-2 text-xs">
                <li><Link to="/login" className="hover:text-[#C4AD88] transition">Sign In</Link></li>
                <li><Link to="/register" className="hover:text-[#C4AD88] transition">Create Account</Link></li>
                <li><Link to="/forgot-password" className="hover:text-[#C4AD88] transition">Password Recovery</Link></li>
                <li><Link to="/dashboard" className="hover:text-[#C4AD88] transition">Story Library</Link></li>
              </ul>
            </div>

            {/* Language Selection Column */}
            <div className="space-y-3">
              <h5 className="text-xs uppercase tracking-wider text-[#F1EEE8] font-semibold">Language / 言語</h5>
              <div className="grid grid-cols-2 gap-2 text-xs">
                {languages.map((l) => (
                  <button
                    key={l.code}
                    type="button"
                    onClick={() => setSelectedLanguage(l.code)}
                    className={`rounded border px-2.5 py-1.5 text-left transition ${
                      selectedLanguage === l.code
                        ? 'border-[#C4AD88] bg-[#C4AD88]/10 text-[#C4AD88]'
                        : 'border-white/10 hover:border-white/20 text-[#858A8D]'
                    }`}
                  >
                    <div>{l.code}</div>
                    <div className="text-[10px] text-gray-500">{l.native}</div>
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Bottom Copyright */}
          <div className="mt-14 border-t border-white/[0.08] pt-6 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs">
            <p>© 2026 Yūgen Mayoiga. All rights reserved.</p>
            <p className="font-cinematic italic text-[#C4AD88]">Every journey leaves something behind.</p>
          </div>
        </div>
      </footer>
    </div>
  )
}
