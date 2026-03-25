import { useState, useEffect } from 'react'
import { useNavigate, Link, useSearchParams } from 'react-router-dom'
import { Mail, Lock, User, Loader2, AlertCircle } from 'lucide-react'
import { useAuth } from '../hooks/useAuth'
import { useTranslation } from '../context/LanguageContext'
import clsx from 'clsx'

type AuthMode = 'login' | 'register'

export default function Login() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { login, register, loginAsGuest } = useAuth()
  const { t } = useTranslation()
  
  // Get initial mode from URL params
  const initialMode = searchParams.get('mode') === 'register' ? 'register' : 'login'
  
  const [mode, setMode] = useState<AuthMode>(initialMode)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Update mode when URL params change
  useEffect(() => {
    const urlMode = searchParams.get('mode')
    setMode(urlMode === 'register' ? 'register' : 'login')
  }, [searchParams])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setIsLoading(true)

    try {
      if (mode === 'login') {
        await login(email, password)
      } else {
        if (!displayName.trim()) {
          setError(t('auth.pleaseEnterName'))
          setIsLoading(false)
          return
        }
        await register(email, password, displayName)
      }
      navigate('/')
    } catch (err: any) {
      setError(
        err.response?.data?.detail || 
        t('auth.errorOccurred')
      )
    } finally {
      setIsLoading(false)
    }
  }

  const handleGuestLogin = async () => {
    setIsLoading(true)
    try {
      await loginAsGuest()
      navigate('/')
    } catch (err) {
      setError(t('auth.errorGuestSession'))
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-[calc(100vh-12rem)] flex items-center justify-center">
      <div className="w-full max-w-md">
        <div className="card p-8">
          {/* Header */}
          <div className="text-center mb-8">
            <h1 className="text-2xl font-bold text-neutral-900 mb-2">
              {mode === 'login' ? t('auth.welcomeBack') : t('auth.createYourAccount')}
            </h1>
            <p className="text-neutral-500">
              {mode === 'login'
                ? t('auth.signInAccess')
                : t('auth.registerSave')}
            </p>
          </div>

          {/* Mode switcher */}
          <div className="flex bg-neutral-100 p-1 rounded-lg mb-6">
            <button
              type="button"
              onClick={() => setMode('login')}
              className={clsx(
                'flex-1 py-2 rounded-md text-sm font-medium transition-all',
                mode === 'login'
                  ? 'bg-white text-neutral-900 shadow-sm'
                  : 'text-neutral-500 hover:text-neutral-700'
              )}
            >
              {t('auth.signInTab')}
            </button>
            <button
              type="button"
              onClick={() => setMode('register')}
              className={clsx(
                'flex-1 py-2 rounded-md text-sm font-medium transition-all',
                mode === 'register'
                  ? 'bg-white text-neutral-900 shadow-sm'
                  : 'text-neutral-500 hover:text-neutral-700'
              )}
            >
              {t('auth.registerTab')}
            </button>
          </div>

          {/* Error message */}
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-6 flex items-center gap-2">
              <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0" />
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            {mode === 'register' && (
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-1">
                  {t('auth.name')}
                </label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-neutral-400 pointer-events-none" />
                  <input
                    type="text"
                    value={displayName}
                    onChange={(e) => setDisplayName(e.target.value)}
                    placeholder={t('auth.namePlaceholder')}
                    className="input input-with-icon"
                    required
                  />
                </div>
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-1">
                {t('auth.email')}
              </label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-neutral-400 pointer-events-none" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder={t('auth.emailPlaceholder')}
                  className="input input-with-icon"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-neutral-700 mb-1">
                {t('auth.password')}
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-neutral-400 pointer-events-none" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder={mode === 'register' ? t('auth.passwordPlaceholder') : '••••••••'}
                  className="input input-with-icon"
                  minLength={8}
                  required
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="btn btn-primary w-full py-3"
            >
              {isLoading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : mode === 'login' ? (
                t('auth.signInTab')
              ) : (
                t('common.register')
              )}
            </button>
          </form>

          {/* Divider */}
          <div className="relative my-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-neutral-200" />
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-4 bg-white text-neutral-500">{t('common.or')}</span>
            </div>
          </div>

          {/* Guest option */}
          <button
            type="button"
            onClick={handleGuestLogin}
            disabled={isLoading}
            className="btn btn-secondary w-full py-3"
          >
            {t('auth.continueAsGuest')}
          </button>

          <p className="text-xs text-neutral-500 text-center mt-4">
            {t('auth.guestDisclaimer')}
          </p>
        </div>

        {/* Back to home */}
        <p className="text-center mt-6 text-neutral-500">
          <Link to="/" className="text-primary-600 hover:underline">
            ← {t('common.backToHome')}
          </Link>
        </p>
      </div>
    </div>
  )
}
