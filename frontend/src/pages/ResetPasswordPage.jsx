import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { authApi } from '../api/client'
import { useToast } from '../context/ToastContext'

export default function ResetPasswordPage() {
  const { showToast } = useToast()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()

  const token = searchParams.get('token') || ''
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  const strength = !password
    ? ''
    : password.length < 8
      ? 'Weak'
      : password.length < 12
        ? 'Fair'
        : /[A-Z]/.test(password) && /[0-9]/.test(password) && /[^A-Za-z0-9]/.test(password)
          ? 'Strong'
          : 'Good'

  async function handleSubmit(event) {
    event.preventDefault()

    if (!token) {
      showToast('Invalid or expired reset link.', 'error')
      return
    }

    if (password.length < 8 || password.length > 128) {
      showToast('Password must be between 8 and 128 characters.', 'error')
      return
    }

    if (password !== confirmPassword) {
      showToast('Passwords do not match.', 'error')
      return
    }

    setSubmitting(true)

    try {
      const result = await authApi.resetPassword(token, password)
      showToast(result.message || 'Password updated successfully!', 'success')
      navigate('/login', { replace: true })
    } catch (error) {
      showToast(error.message || 'Unable to update password.', 'error')
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
          Account security
        </p>
        <h1 className="mt-3 font-serif text-4xl text-[#eeeae2]">
          Set new password
        </h1>
        <p className="mt-3 text-sm leading-6 text-gray-400">
          Choose a new password for your account.
        </p>

        {!token ? (
          <div className="mt-8 space-y-4">
            <p className="text-sm text-red-200">
              This reset link is missing or invalid. Request a new one.
            </p>
            <Link
              to="/forgot-password"
              className="block text-sm text-amber-200 hover:text-amber-100"
            >
              Request another reset link
            </Link>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="mt-8 space-y-5">
            <div>
              <label htmlFor="password" className="mb-2 block text-sm text-gray-300">
                New password
              </label>
              <div className="flex rounded-lg border border-white/10 bg-black/20 focus-within:border-amber-200/50">
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="new-password"
                  required
                  minLength={8}
                  maxLength={128}
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  className="min-w-0 flex-1 bg-transparent px-4 py-3 text-sm text-white outline-none"
                  placeholder="At least 8 characters"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((value) => !value)}
                  className="px-4 text-xs text-amber-200/70 hover:text-amber-100"
                >
                  {showPassword ? 'Hide' : 'Show'}
                </button>
              </div>
              {strength && (
                <p className="mt-2 text-xs text-gray-400">
                  Password strength: <span className="text-amber-200">{strength}</span>
                </p>
              )}
            </div>

            <div>
              <label htmlFor="confirmPassword" className="mb-2 block text-sm text-gray-300">
                Confirm new password
              </label>
              <input
                id="confirmPassword"
                type={showPassword ? 'text' : 'password'}
                autoComplete="new-password"
                required
                minLength={8}
                maxLength={128}
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
                className="w-full rounded-lg border border-white/10 bg-black/20 px-4 py-3 text-sm text-white outline-none focus:border-amber-200/50"
                placeholder="Enter password again"
              />
            </div>

            <button
              type="submit"
              disabled={submitting}
              className="w-full rounded-lg bg-amber-100 px-4 py-3 text-sm font-semibold text-[#171713] transition hover:bg-amber-200 disabled:opacity-50"
            >
              {submitting ? 'Updating...' : 'Update password'}
            </button>
          </form>
        )}

        <p className="mt-7 text-center text-sm text-gray-400">
          <Link to="/login" className="text-amber-200 hover:text-amber-100">
            Back to sign in
          </Link>
        </p>
      </section>
    </main>
  )
}
