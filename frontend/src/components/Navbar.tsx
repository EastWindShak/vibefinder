import { Link, useNavigate } from 'react-router-dom'
import { Music, User, LogOut, LogIn, UserPlus } from 'lucide-react'
import { useAuth } from '../hooks/useAuth'
import { useTranslation } from '../context/LanguageContext'
import LanguageSelector from './LanguageSelector'
import ThemeToggle from './ThemeToggle'

export default function Navbar() {
  const { user, isAuthenticated, isGuest, logout } = useAuth()
  const navigate = useNavigate()
  const { t } = useTranslation()

  const handleLogout = () => {
    logout()
    navigate('/')
  }

  return (
    <nav className="bg-white border-b border-neutral-200 sticky top-0 z-50">
      <div className="container mx-auto px-4 max-w-6xl">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2 group">
            <div className="w-10 h-10 bg-primary-600 rounded-xl flex items-center justify-center group-hover:bg-primary-700 transition-colors">
              <Music className="w-5 h-5 text-white" />
            </div>
            <span className="font-bold text-xl text-neutral-900">
              Vibe<span className="text-primary-600">Finder</span>
            </span>
          </Link>

          {/* Navigation */}
          <div className="flex items-center gap-2 sm:gap-4">
            {/* Theme Toggle */}
            <ThemeToggle />
            
            {/* Language Selector */}
            <LanguageSelector />

            {/* Show user info and logout only for registered users */}
            {isAuthenticated && !isGuest ? (
              <>
                {/* User profile link */}
                <Link
                  to="/profile"
                  className="flex items-center gap-2 text-sm text-neutral-700 hover:text-neutral-900"
                >
                  <User className="w-4 h-4" />
                  <span className="hidden sm:inline">{user?.display_name}</span>
                </Link>

                {/* Logout button */}
                <button
                  onClick={handleLogout}
                  className="p-2 text-neutral-500 hover:text-neutral-700 hover:bg-neutral-100 rounded-lg transition-colors"
                  title={t('common.logOut')}
                >
                  <LogOut className="w-5 h-5" />
                </button>
              </>
            ) : (
              /* Show Sign In and Register for guests and unauthenticated users */
              <div className="flex items-center gap-2">
                <Link
                  to="/login"
                  className="btn btn-outline flex items-center gap-2 text-sm"
                >
                  <LogIn className="w-4 h-4" />
                  <span className="hidden sm:inline">{t('common.signIn')}</span>
                </Link>
                
                <Link
                  to="/login?mode=register"
                  className="btn btn-primary flex items-center gap-2 text-sm"
                >
                  <UserPlus className="w-4 h-4" />
                  <span className="hidden sm:inline">{t('common.register')}</span>
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>
    </nav>
  )
}
