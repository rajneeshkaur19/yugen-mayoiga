import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { useLanguage } from '../context/LanguageContext'

export default function LoginPage() {
  const { login } = useAuth()
  const { showToast } = useToast()
  const { t } = useLanguage()
  const navigate = useNavigate()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    setSubmitting(true)

    try {
      await login({ email: email.trim(), password })
      showToast('Welcome back to Mayoiga.', 'success')
      navigate('/dashboard', { replace: true })
    } catch (error) {
      showToast(error.message || 'Unable to sign in. Please verify your credentials.', 'error')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen w-full bg-[#101317] text-[#F1EEE8] font-sans selection:bg-[#A33B42] selection:text-white flex flex-col lg:grid lg:grid-cols-12">
      {/* ─────────────────────────────────────────────────────────────
          1. LEFT SECTION (CINEMATIC ENVIRONMENTAL ART — DESKTOP)
      ───────────────────────────────────────────────────────────── */}
      <div className="relative hidden lg:flex lg:col-span-6 xl:col-span-7 flex-col justify-between p-12 overflow-hidden bg-[#101317]">
        {/* Environmental Artwork Backdrop */}
        <div
          className="absolute inset-0 bg-cover bg-center bg-no-repeat transition-transform duration-1000 scale-105 filter contrast-115 brightness-95"
          style={{
            backgroundImage: "url('/assets/backgrounds/village-street-night.png')",
          }}
        />

        {/* Cinematic Gradient Overlays */}
        <div className="absolute inset-0 bg-gradient-to-t from-[#101317] via-[#101317]/30 to-transparent" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,transparent_35%,#101317_90%)]" />

        {/* Top Branding */}
        <div className="relative z-10">
          <Link to="/" className="group inline-flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-[#C4AD88]/30 bg-[#1B2228]/80 text-[#C4AD88] backdrop-blur-md transition group-hover:border-[#C4AD88]">
              <svg className="h-6 w-6 text-[#A33B42] transition group-hover:text-[#C4AD88]" viewBox="0 0 24 24" fill="currentColor">
                <path d="M2 5h20v2H2V5zm3 3h14v2H5V8zm2 3h2v11H7V11zm8 0h2v11h-2V11zM1 3h22v2H1V3z" />
              </svg>
            </div>
            <div>
              <span className="font-cinematic text-xl font-bold tracking-[0.2em] text-[#F1EEE8] group-hover:text-[#C4AD88] transition">
                YŪGEN MAYOIGA
              </span>
              <span className="block text-[10px] tracking-[0.3em] uppercase text-[#858A8D] font-mono">
                幽玄 · 迷い家
              </span>
            </div>
          </Link>
        </div>

        {/* Bottom Poetic Narrative & Torii Stamp */}
        <div className="relative z-10 max-w-lg space-y-4">
          <div className="inline-flex items-center gap-2 rounded-full border border-[#C4AD88]/30 bg-[#101317]/80 px-3.5 py-1 text-xs text-[#C4AD88] font-mono backdrop-blur-md">
            <span className="h-1.5 w-1.5 rounded-full bg-[#A33B42] animate-pulse" />
            <span>Threshold Entry</span>
            <span className="text-[#858A8D]">· 帰還</span>
          </div>

          <h2 className="font-cinematic text-4xl sm:text-5xl font-semibold leading-tight text-[#F1EEE8]">
            Some doors remember who entered.
          </h2>

          <p className="font-cinematic text-base italic text-[#D7DCE0] leading-relaxed">
            “The lantern still burns in the corridor where you left it. Every decision you carved into the estate waits in the silence.”
          </p>

          <div className="pt-2 flex items-center gap-6 text-[11px] text-[#858A8D] font-mono">
            <div>
              <span className="text-[#C4AD88]">Sanctuary</span>: Connected
            </div>
            <div>·</div>
            <div>
              <span className="text-[#C4AD88]">Memory Matrix</span>: Persistent
            </div>
          </div>
        </div>
      </div>

      {/* ─────────────────────────────────────────────────────────────
          2. RIGHT SECTION (AUTHENTICATION FORM)
      ───────────────────────────────────────────────────────────── */}
      <div className="relative flex-1 lg:col-span-6 xl:col-span-5 flex flex-col justify-center px-6 py-12 sm:px-12 md:px-16 bg-[#14191E] border-l border-white/[0.08] min-h-screen">
        {/* Subtle Mobile Environmental Backdrop */}
        <div
          className="lg:hidden absolute inset-0 bg-cover bg-center bg-no-repeat opacity-15 pointer-events-none"
          style={{ backgroundImage: "url('/assets/backgrounds/village-street-night.png')" }}
        />

        <div className="relative z-10 mx-auto w-full max-w-md space-y-8">
          {/* Top Link */}
          <div className="flex items-center justify-between">
            <Link
              to="/"
              className="group inline-flex items-center gap-2 text-xs font-mono text-[#858A8D] hover:text-[#C4AD88] transition"
            >
              <span className="transition-transform group-hover:-translate-x-1">←</span>
              <span>Return to Mayoiga</span>
            </Link>

            <span className="text-[10px] uppercase font-mono tracking-widest text-[#C4AD88]">
              Sanctuary Gate
            </span>
          </div>

          {/* Header */}
          <div>
            <div className="inline-block rounded-md border border-[#C4AD88]/20 bg-[#101317] px-2.5 py-0.5 text-[10px] font-mono uppercase tracking-wider text-[#C4AD88] mb-2">
              {t.auth.signInBtn}
            </div>
            <h1 className="font-cinematic text-4xl font-semibold text-[#F1EEE8]">
              {t.auth.signInTitle}
            </h1>
            <p className="mt-2 text-xs sm:text-sm text-[#858A8D] leading-relaxed">
              {t.auth.signInSubtitle}
            </p>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Email Address */}
            <div>
              <label htmlFor="email" className="block text-xs uppercase tracking-wider text-[#C4AD88] font-mono mb-2">
                {t.auth.email}
              </label>
              <input
                id="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="wanderer@mayoiga.jp"
                className="w-full rounded-xl border border-white/10 bg-[#101317] px-4 py-3.5 text-sm text-[#F1EEE8] placeholder-[#858A8D] outline-none focus:border-[#C4AD88]/60 transition"
              />
            </div>

            {/* Password */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label htmlFor="password" className="block text-xs uppercase tracking-wider text-[#C4AD88] font-mono">
                  {t.auth.password}
                </label>
                <Link
                  to="/forgot-password"
                  className="text-xs text-[#858A8D] hover:text-[#C4AD88] transition font-mono text-[11px]"
                >
                  {t.auth.forgotPassword}
                </Link>
              </div>

              <div className="relative flex items-center">
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="current-password"
                  required
                  minLength={8}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  className="w-full rounded-xl border border-white/10 bg-[#101317] px-4 py-3.5 pr-14 text-sm text-[#F1EEE8] placeholder-[#858A8D] outline-none focus:border-[#C4AD88]/60 transition"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  className="absolute right-3.5 px-2 py-1 text-xs text-[#858A8D] hover:text-[#C4AD88] transition font-mono text-[11px]"
                >
                  {showPassword ? 'Hide' : 'Show'}
                </button>
              </div>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={submitting}
              className="w-full inline-flex items-center justify-center gap-2.5 rounded-xl border border-[#A33B42] bg-[#A33B42] py-3.5 px-6 text-sm font-semibold text-[#F1EEE8] shadow-lg hover:bg-[#702B34] transition hover:shadow-[0_0_20px_rgba(163,59,66,0.5)] disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <span>{submitting ? 'Entering the Sanctuary...' : t.auth.signInBtn}</span>
              <span className="text-[#C4AD88]">→</span>
            </button>
          </form>

          {/* Switch to Register */}
          <div className="pt-4 border-t border-white/[0.08] text-center text-xs text-[#858A8D]">
            <span>{t.auth.noAccount} </span>
            <Link to="/register" className="font-semibold text-[#C4AD88] hover:text-[#D9C9A8] transition">
              {t.auth.registerBtn} →
            </Link>
          </div>

          <p className="text-center text-[10px] font-mono text-[#858A8D]/70 tracking-wider">
            Every choice leaves something behind.
          </p>
        </div>
      </div>
    </div>
  )
}
