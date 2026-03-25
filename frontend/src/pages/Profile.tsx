import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { User, Music, History, Heart, ThumbsDown, LogOut, Loader2, ChevronRight, Play } from 'lucide-react'
import { useAuth } from '../hooks/useAuth'
import { useTranslation } from '../context/LanguageContext'
import { useLanguage } from '../context/LanguageContext'
import { recommendationsApi } from '../services/api'
import PreferencesList from '../components/PreferencesList'

export default function Profile() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { user, isAuthenticated, isGuest, logout } = useAuth()
  const { t } = useTranslation()
  const { language } = useLanguage()
  const [deletingId, setDeletingId] = useState<string | null>(null)

  // Redirect if not authenticated or is guest
  useEffect(() => {
    if (!isAuthenticated || isGuest) {
      navigate('/login')
    }
  }, [isAuthenticated, isGuest, navigate])

  // Fetch recommendation history
  const { data: historyData, isLoading: historyLoading } = useQuery({
    queryKey: ['recommendation-history'],
    queryFn: () => recommendationsApi.getHistory(10),
    enabled: isAuthenticated && !isGuest,
  })

  // Fetch preferences counts
  const { data: countsData } = useQuery({
    queryKey: ['preferences-counts'],
    queryFn: () => recommendationsApi.getPreferencesCounts(),
    enabled: isAuthenticated && !isGuest,
  })

  // Fetch liked songs
  const { data: likesData, isLoading: likesLoading } = useQuery({
    queryKey: ['liked-songs'],
    queryFn: () => recommendationsApi.getLikedSongs(),
    enabled: isAuthenticated && !isGuest,
  })

  // Fetch disliked songs
  const { data: dislikesData, isLoading: dislikesLoading } = useQuery({
    queryKey: ['disliked-songs'],
    queryFn: () => recommendationsApi.getDislikedSongs(),
    enabled: isAuthenticated && !isGuest,
  })

  // Handle delete preference
  const handleDeletePreference = async (type: 'likes' | 'dislikes', preferenceId: string) => {
    setDeletingId(preferenceId)
    try {
      await recommendationsApi.deletePreference(type, preferenceId)
      // Invalidate queries to refresh the data
      queryClient.invalidateQueries({ queryKey: ['preferences-counts'] })
      queryClient.invalidateQueries({ queryKey: [type === 'likes' ? 'liked-songs' : 'disliked-songs'] })
    } catch (error) {
      console.error('Failed to delete preference:', error)
    } finally {
      setDeletingId(null)
    }
  }

  const handleLogout = () => {
    logout()
    navigate('/')
  }

  // Get locale for date formatting
  const getLocale = () => {
    const localeMap: Record<string, string> = {
      en: 'en-US',
      es: 'es-ES',
      de: 'de-DE',
      fr: 'fr-FR',
      it: 'it-IT'
    }
    return localeMap[language] || 'en-US'
  }

  if (!user) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <Loader2 className="w-8 h-8 text-primary-600 animate-spin" />
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* Profile header */}
      <div className="card p-8">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-6">
            {/* Avatar */}
            <div className="w-20 h-20 bg-primary-100 rounded-full flex items-center justify-center">
              <User className="w-10 h-10 text-primary-600" />
            </div>

            {/* User info */}
            <div>
              <h1 className="text-2xl font-bold text-neutral-900">
                {user.display_name}
              </h1>
              <p className="text-neutral-500">{user.email}</p>
              <span className="inline-flex items-center gap-1 mt-2 px-3 py-1 bg-green-100 text-green-700 rounded-full text-sm">
                <span className="w-2 h-2 bg-green-500 rounded-full" />
                {t('profile.activeAccount')}
              </span>
            </div>
          </div>

          <button
            onClick={handleLogout}
            className="btn btn-outline text-red-600 border-red-200 hover:bg-red-50 hover:border-red-300"
          >
            <LogOut className="w-4 h-4 mr-2" />
            {t('common.logOut')}
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid md:grid-cols-3 gap-4">
        <div className="card p-6">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-primary-100 rounded-lg flex items-center justify-center">
              <Music className="w-6 h-6 text-primary-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-neutral-900">
                {historyData?.history?.length || 0}
              </p>
              <p className="text-sm text-neutral-500">{t('profile.searchesMade')}</p>
            </div>
          </div>
        </div>

        <div className="card p-6">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
              <Heart className="w-6 h-6 text-green-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-neutral-900">
                {countsData?.likes ?? 0}
              </p>
              <p className="text-sm text-neutral-500">{t('profile.songsYouLike')}</p>
            </div>
          </div>
        </div>

        <div className="card p-6">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-red-100 rounded-lg flex items-center justify-center">
              <ThumbsDown className="w-6 h-6 text-red-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-neutral-900">
                {countsData?.dislikes ?? 0}
              </p>
              <p className="text-sm text-neutral-500">{t('profile.songsFiltered')}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Liked and Disliked Songs */}
      <div className="grid md:grid-cols-2 gap-6">
        {/* Liked Songs */}
        <div className="card">
          <div className="p-4 border-b border-neutral-200 bg-green-50">
            <div className="flex items-center gap-3">
              <Heart className="w-5 h-5 text-green-600" />
              <h2 className="font-semibold text-neutral-900">
                {t('profile.likedSongs')}
              </h2>
              <span className="text-sm text-neutral-500">
                ({countsData?.likes ?? 0})
              </span>
            </div>
            <p className="text-xs text-neutral-500 mt-1">
              {t('profile.likedSongsDescription')}
            </p>
          </div>
          <PreferencesList
            preferences={likesData?.preferences ?? []}
            type="likes"
            isLoading={likesLoading}
            onDelete={(id) => handleDeletePreference('likes', id)}
            isDeleting={deletingId}
          />
        </div>

        {/* Disliked Songs */}
        <div className="card">
          <div className="p-4 border-b border-neutral-200 bg-red-50">
            <div className="flex items-center gap-3">
              <ThumbsDown className="w-5 h-5 text-red-600" />
              <h2 className="font-semibold text-neutral-900">
                {t('profile.dislikedSongs')}
              </h2>
              <span className="text-sm text-neutral-500">
                ({countsData?.dislikes ?? 0})
              </span>
            </div>
            <p className="text-xs text-neutral-500 mt-1">
              {t('profile.dislikedSongsDescription')}
            </p>
          </div>
          <PreferencesList
            preferences={dislikesData?.preferences ?? []}
            type="dislikes"
            isLoading={dislikesLoading}
            onDelete={(id) => handleDeletePreference('dislikes', id)}
            isDeleting={deletingId}
          />
        </div>
      </div>

      {/* History */}
      <div className="card">
        <div className="p-6 border-b border-neutral-200">
          <div className="flex items-center gap-3">
            <History className="w-5 h-5 text-neutral-500" />
            <h2 className="text-lg font-semibold text-neutral-900">
              {t('profile.searchHistory')}
            </h2>
          </div>
        </div>

        {historyLoading ? (
          <div className="p-8 text-center">
            <Loader2 className="w-8 h-8 text-primary-600 animate-spin mx-auto" />
          </div>
        ) : historyData?.history?.length > 0 ? (
          <div className="divide-y divide-neutral-100">
            {historyData.history.map((item: any) => (
              <button
                key={item.id}
                onClick={() => navigate(`/?history=${item.id}`)}
                className="w-full p-4 hover:bg-neutral-50 text-left transition-colors group"
              >
                <div className="flex items-center justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                        item.query_type === 'mood'
                          ? 'bg-purple-100 text-purple-700'
                          : item.query_type === 'combined'
                          ? 'bg-green-100 text-green-700'
                          : 'bg-blue-100 text-blue-700'
                      }`}>
                        {item.query_type === 'mood' ? 'Mood' : item.query_type === 'combined' ? 'Combined' : 'Audio'}
                      </span>
                      {item.recommendations_count > 0 && (
                        <span className="text-xs text-neutral-400">
                          {item.recommendations_count} {t('profile.songs')}
                        </span>
                      )}
                    </div>
                    <p className="mt-1 text-neutral-900 truncate">
                      {item.query_type === 'mood'
                        ? item.input_data.mood
                        : item.query_type === 'combined'
                        ? `${item.input_data.mood || ''} - ${item.input_data.song_title || ''}`
                        : `${item.input_data.song_title} - ${item.input_data.song_artist}`}
                    </p>
                  </div>
                  <div className="flex items-center gap-3 flex-shrink-0">
                    <p className="text-sm text-neutral-500">
                      {new Date(item.created_at).toLocaleDateString(getLocale(), {
                        day: 'numeric',
                        month: 'short',
                        hour: '2-digit',
                        minute: '2-digit'
                      })}
                    </p>
                    <div className="flex items-center gap-1 text-primary-600 opacity-0 group-hover:opacity-100 transition-opacity">
                      <Play className="w-4 h-4" />
                      <ChevronRight className="w-4 h-4" />
                    </div>
                  </div>
                </div>
              </button>
            ))}
          </div>
        ) : (
          <div className="p-8 text-center text-neutral-500">
            <History className="w-12 h-12 mx-auto mb-4 opacity-50" />
            <p>{t('profile.noSearches')}</p>
            <p className="text-sm mt-1">
              {t('profile.searchesWillAppear')}
            </p>
          </div>
        )}
      </div>

      {/* Preferences info */}
      <div className="card p-6 bg-primary-50 border-primary-100">
        <h3 className="font-semibold text-primary-900 mb-2">
          {t('profile.aboutPreferences')}
        </h3>
        <p className="text-sm text-primary-800">
          {t('profile.preferencesDescription')}
        </p>
      </div>
    </div>
  )
}
