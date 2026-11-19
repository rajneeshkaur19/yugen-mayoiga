import { useState } from 'react'
import { Link } from 'react-router-dom'
import { authApi } from '../api/client'
import { useToast } from '../context/ToastContext'

export default function ForgotPasswordPage() {
  const { showToast } = useToast()
  const [email, setEmail] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    setSubmitting(true)

    try {
      const result = await authApi.forgotPassword(email.trim())
      showToast(result.message || 'Password reset instructions sent.', 'success')
    } catch (error) {
      showToast(error.message || 'Unable to process your request.', 'error')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center px-5 py-12">
      <section className="w-full max-w-md rounded-2xl border border-white/10 bg-white/[0.035] p-7 shadow-2xl sm:p-9">
        <Link to="/" className="text-xs uppercase tracking-[0.3em] text-amber-200/60">
          Yugen Mayoiga
        </Link>

        <p className="mt-10 text-xs uppercase tracking-[0.25em] text-amber-200/50">
          Account recovery
        </p>
        <h1 className="mt-3 font-serif text-4xl text-[#eeeae2]">
          Forgot password?
        </h1>
        <p className="mt-3 text-sm leading-6 text-gray-400">
          Enter your registered email address to receive password reset instructions.
        </p>

        <form onSubmit={handleSubmit} className="mt-8 space-y-5">
          <div>
            <label htmlFor="email" className="mb-2 block text-sm text-gray-300">
              Email address
            </label>
            <input
              id="email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="w-full rounded-lg border border-white/10 bg-black/20 px-4 py-3 text-sm text-white outline-none focus:border-amber-200/50"
              placeholder="you@example.com"
            />
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-lg bg-amber-100 px-4 py-3 text-sm font-semibold text-[#171713] transition hover:bg-amber-200 disabled:opacity-50"
          >
            {submitting ? 'Sending...' : 'Send reset instructions'}
          </button>
        </form>

        <p className="mt-7 text-center text-sm text-gray-400">
          Remember your password?{' '}
          <Link to="/login" className="text-amber-200 hover:text-amber-100">
            Sign in
          </Link>
        </p>
      </section>
    </main>
  )
}
