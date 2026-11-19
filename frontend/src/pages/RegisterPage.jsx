import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'

export default function RegisterPage() {
  const { register } = useAuth()
  const { showToast } = useToast()
  const navigate = useNavigate()

  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()

    if (password !== confirmPassword) {
      showToast('Passwords do not match.', 'error')
      return
    }

    if (!/^[A-Za-z0-9_]{3,50}$/.test(username.trim())) {
      showToast('Username must be 3-50 letters, numbers or underscores.', 'error')
      return
    }

    if (password.length < 8 || password.length > 128) {
      showToast('Password must be between 8 and 128 characters.', 'error')
      return
    }

    setSubmitting(true)

    try {
      await register({
        username: username.trim(),
        email: email.trim(),
        password,
      })

      showToast('Your sanctuary account has been created. Please sign in.', 'success')
      navigate('/login', { replace: true })
    } catch (error) {
      showToast(error.message || 'Unable to create your account.', 'error')
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
            backgroundImage: "url('/assets/story-covers/cover-shrine-rain.png')",
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
            <span>Sanctuary Initiation</span>
            <span className="text-[#858A8D]">· 創世</span>
          </div>

          <h2 className="font-cinematic text-4xl sm:text-5xl font-semibold leading-tight text-[#F1EEE8]">
            Leave the ordinary world behind.
          </h2>

          <p className="font-cinematic text-base italic text-[#D7DCE0] leading-relaxed">
            “Your name will be carved into the cedar ledger of Mayoiga. Here, your choices do not dissolve into the air; they build the world you inhabit.”
          </p>

          <div className="pt-2 flex items-center gap-6 text-[11px] text-[#858A8D] font-mono">
            <div>
              <span className="text-[#C4AD88]">World Type</span>: Interactive Matrix
            </div>
            <div>·</div>
            <div>
              <span className="text-[#C4AD88]">Registration</span>: Permanent Archive
            </div>
          </div>
        </div>
      </div>

      {/* ─────────────────────────────────────────────────────────────
          2. RIGHT SECTION (REGISTRATION FORM)
      ───────────────────────────────────────────────────────────── */}
      <div className="relative flex-1 lg:col-span-6 xl:col-span-5 flex flex-col justify-center px-6 py-12 sm:px-12 md:px-16 bg-[#14191E] border-l border-white/[0.08] min-h-screen">
        {/* Subtle Mobile Environmental Backdrop */}
        <div
          className="lg:hidden absolute inset-0 bg-cover bg-center bg-no-repeat opacity-15 pointer-events-none"
          style={{ backgroundImage: "url('/assets/story-covers/cover-shrine-rain.png')" }}
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
              New Chronicle
            </span>
          </div>

          {/* Header */}
          <div>
            <div className="inline-block rounded-md border border-[#A33B42]/30 bg-[#101317] px-2.5 py-0.5 text-[10px] font-mono uppercase tracking-wider text-[#A33B42] mb-2">
              Create Account
            </div>
            <h1 className="font-cinematic text-4xl font-semibold text-[#F1EEE8]">
              Your story begins here.
            </h1>
            <p className="mt-2 text-xs sm:text-sm text-[#858A8D] leading-relaxed">
              Create an account. Enter the sanctuary of forgotten choices.
            </p>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Username */}
            <div>
              <label htmlFor="username" className="block text-xs uppercase tracking-wider text-[#C4AD88] font-mono mb-1.5">
                Wanderer Username
              </label>
              <input
                id="username"
                type="text"
                autoComplete="username"
                required
                minLength={3}
                maxLength={50}
                pattern="^[A-Za-z0-9_]+$"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="letters, numbers or _ only"
                className="w-full rounded-xl border border-white/10 bg-[#101317] px-4 py-3 text-sm text-[#F1EEE8] placeholder-[#858A8D] outline-none focus:border-[#C4AD88]/60 transition"
              />
              <span className="text-[10px] text-[#858A8D] font-mono mt-1 block">
                3–50 characters; letters, numbers and _ only.
              </span>
            </div>

            {/* Email Address */}
            <div>
              <label htmlFor="email" className="block text-xs uppercase tracking-wider text-[#C4AD88] font-mono mb-1.5">
                Email Address
              </label>
              <input
                id="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="wanderer@mayoiga.jp"
                className="w-full rounded-xl border border-white/10 bg-[#101317] px-4 py-3 text-sm text-[#F1EEE8] placeholder-[#858A8D] outline-none focus:border-[#C4AD88]/60 transition"
              />
            </div>

            {/* Password */}
            <div>
              <label htmlFor="password" className="block text-xs uppercase tracking-wider text-[#C4AD88] font-mono mb-1.5">
                Password
              </label>
              <div className="relative flex items-center">
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="new-password"
                  required
                  minLength={8}
                  maxLength={128}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="At least 8 characters"
                  className="w-full rounded-xl border border-white/10 bg-[#101317] px-4 py-3 pr-14 text-sm text-[#F1EEE8] placeholder-[#858A8D] outline-none focus:border-[#C4AD88]/60 transition"
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

            {/* Confirm Password */}
            <div>
              <label htmlFor="confirmPassword" className="block text-xs uppercase tracking-wider text-[#C4AD88] font-mono mb-1.5">
                Confirm Password
              </label>
              <input
                id="confirmPassword"
                type={showPassword ? 'text' : 'password'}
                autoComplete="new-password"
                required
                minLength={8}
                maxLength={128}
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Re-enter your password"
                className="w-full rounded-xl border border-white/10 bg-[#101317] px-4 py-3 text-sm text-[#F1EEE8] placeholder-[#858A8D] outline-none focus:border-[#C4AD88]/60 transition"
              />
            </div>

            {/* Submit Button */}
            <div className="pt-2">
              <button
                type="submit"
                disabled={submitting}
                className="w-full inline-flex items-center justify-center gap-2.5 rounded-xl border border-[#A33B42] bg-[#A33B42] py-3.5 px-6 text-sm font-semibold text-[#F1EEE8] shadow-lg hover:bg-[#702B34] transition hover:shadow-[0_0_20px_rgba(163,59,66,0.5)] disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <span>{submitting ? 'Creating Sanctuary Account...' : 'Create Account'}</span>
                <span className="text-[#C4AD88]">→</span>
              </button>
            </div>
          </form>

          {/* Switch to Login */}
          <div className="pt-4 border-t border-white/[0.08] text-center text-xs text-[#858A8D]">
            <span>Already have an account? </span>
            <Link to="/login" className="font-semibold text-[#C4AD88] hover:text-[#D9C9A8] transition">
              Sign In →
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
