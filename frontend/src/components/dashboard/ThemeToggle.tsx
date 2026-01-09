import { Sun, Moon } from 'lucide-react'
import { useTheme } from '@/hooks/useTheme'
import { cn } from '@/lib/utils'

export function ThemeToggle() {
  const { theme, toggleTheme } = useTheme()

  return (
    <button
      onClick={toggleTheme}
      className={cn(
        'relative flex items-center justify-center w-10 h-10 rounded-lg transition-all',
        'border border-[var(--color-border)] hover:border-[var(--color-border-bright)]',
        'bg-[var(--color-surface)] hover:bg-[var(--color-panel)]',
        'text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]'
      )}
      aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
      title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
    >
      <Sun
        size={18}
        className={cn(
          'absolute transition-all duration-200',
          theme === 'light'
            ? 'opacity-100 rotate-0 scale-100'
            : 'opacity-0 rotate-90 scale-0'
        )}
      />
      <Moon
        size={18}
        className={cn(
          'absolute transition-all duration-200',
          theme === 'dark'
            ? 'opacity-100 rotate-0 scale-100'
            : 'opacity-0 -rotate-90 scale-0'
        )}
      />
    </button>
  )
}
