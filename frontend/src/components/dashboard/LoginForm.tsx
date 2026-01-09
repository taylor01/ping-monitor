import { useState } from 'react'
import { Activity, LogIn, AlertCircle } from 'lucide-react'
import { login } from '@/api/auth'
import { cn } from '@/lib/utils'
import { ThemeToggle } from './ThemeToggle'

interface LoginFormProps {
  onSuccess: () => void
}

export function LoginForm({ onSuccess }: LoginFormProps) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const success = await login({ email, password })
      if (success) {
        onSuccess()
      } else {
        setError('Invalid credentials')
      }
    } catch {
      setError('Connection failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-[var(--color-void)] grid-bg flex items-center justify-center p-6 relative">
      {/* Theme toggle in corner */}
      <div className="absolute top-4 right-4">
        <ThemeToggle />
      </div>

      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="flex items-center justify-center gap-3 mb-8">
          <div className="p-3 rounded-xl bg-[var(--color-cyan)]/10 border border-[var(--color-cyan)]/30">
            <Activity size={28} className="text-[var(--color-cyan)]" />
          </div>
          <div>
            <h1 className="font-[var(--font-display)] text-2xl font-bold text-[var(--color-text-primary)] uppercase tracking-wider">
              NetMon
            </h1>
            <p className="font-[var(--font-mono)] text-xs text-[var(--color-text-muted)]">
              Network Operations Center
            </p>
          </div>
        </div>

        {/* Login Card */}
        <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-panel)] p-6">
          <h2 className="font-[var(--font-display)] text-lg font-semibold text-[var(--color-text-primary)] uppercase tracking-wide mb-6">
            Authentication
          </h2>

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Email */}
            <div>
              <label className="block text-xs uppercase tracking-wider font-[var(--font-display)] text-[var(--color-text-muted)] mb-2">
                Email
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="user@example.com"
                className="w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-md py-2.5 px-4 text-sm font-[var(--font-mono)] text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-cyan)] focus:ring-1 focus:ring-[var(--color-cyan)]/20 transition-colors"
                required
              />
            </div>

            {/* Password */}
            <div>
              <label className="block text-xs uppercase tracking-wider font-[var(--font-display)] text-[var(--color-text-muted)] mb-2">
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-md py-2.5 px-4 text-sm font-[var(--font-mono)] text-[var(--color-text-primary)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-cyan)] focus:ring-1 focus:ring-[var(--color-cyan)]/20 transition-colors"
                required
              />
            </div>

            {/* Error */}
            {error && (
              <div className="flex items-center gap-2 px-3 py-2 rounded-md bg-[var(--color-alert)]/10 border border-[var(--color-alert)]/30 text-[var(--color-alert)] text-sm font-[var(--font-mono)]">
                <AlertCircle size={16} />
                {error}
              </div>
            )}

            {/* Submit */}
            <button
              type="submit"
              disabled={loading}
              className={cn(
                'w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-md font-[var(--font-display)] uppercase tracking-wider text-sm font-semibold transition-all',
                'bg-[var(--color-cyan)]/10 border border-[var(--color-cyan)]/30 text-[var(--color-cyan)]',
                'hover:bg-[var(--color-cyan)]/20 hover:border-[var(--color-cyan)]/50',
                'disabled:opacity-50 disabled:cursor-not-allowed'
              )}
            >
              {loading ? (
                <div className="w-5 h-5 border-2 border-[var(--color-cyan)] border-t-transparent rounded-full animate-spin" />
              ) : (
                <>
                  <LogIn size={18} />
                  Connect
                </>
              )}
            </button>
          </form>
        </div>

        {/* Footer */}
        <p className="mt-4 text-center text-xs text-[var(--color-text-muted)] font-[var(--font-mono)]">
          Enter your credentials to access the dashboard
        </p>
      </div>
    </div>
  )
}
