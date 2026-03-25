import { useState } from 'react'
import { Play, Trash2, Music, Loader2, ChevronDown, ChevronUp } from 'lucide-react'
import { PreferenceItem, recommendationsApi } from '../services/api'
import { usePlayer } from '../context/PlayerContext'
import { useTranslation } from '../context/LanguageContext'
import { getThumbnailWithFallback } from '../utils/thumbnail'
import clsx from 'clsx'

interface PreferencesListProps {
  preferences: PreferenceItem[]
  type: 'likes' | 'dislikes'
  isLoading: boolean
  onDelete: (preferenceId: string) => void
  isDeleting: string | null
}

export default function PreferencesList({ 
  preferences, 
  type, 
  isLoading,
  onDelete,
  isDeleting
}: PreferencesListProps) {
  const { playSong } = usePlayer()
  const { t } = useTranslation()
  const [expanded, setExpanded] = useState(false)
  const [imgErrors, setImgErrors] = useState<Set<string>>(new Set())

  const handlePlay = (pref: PreferenceItem) => {
    if (!pref.video_id) return
    
    playSong({
      title: pref.song_title,
      artist: pref.artist,
      video_id: pref.video_id,
      genre: pref.genre,
    })
  }

  const handleImageError = (id: string) => {
    setImgErrors(prev => new Set(prev).add(id))
  }

  // Show first 5 items when collapsed
  const displayedPreferences = expanded ? preferences : preferences.slice(0, 5)
  const hasMore = preferences.length > 5

  if (isLoading) {
    return (
      <div className="p-6 text-center">
        <Loader2 className="w-6 h-6 text-primary-600 animate-spin mx-auto" />
      </div>
    )
  }

  if (preferences.length === 0) {
    return (
      <div className="p-6 text-center text-neutral-500">
        <Music className="w-10 h-10 mx-auto mb-3 opacity-50" />
        <p className="text-sm">
          {type === 'likes' ? t('profile.noLikedSongs') : t('profile.noDislikedSongs')}
        </p>
      </div>
    )
  }

  return (
    <div>
      <div className="divide-y divide-neutral-100">
        {displayedPreferences.map((pref) => {
          const { primary: thumbnailUrl, fallback: fallbackUrl } = getThumbnailWithFallback(
            undefined,
            pref.video_id
          )
          const showFallback = imgErrors.has(pref.id)

          return (
            <div
              key={pref.id}
              className="flex items-center gap-3 p-3 hover:bg-neutral-50 transition-colors group"
            >
              {/* Thumbnail */}
              <div className="w-12 h-12 bg-neutral-200 rounded-lg overflow-hidden flex-shrink-0 relative">
                {pref.video_id ? (
                  <img
                    src={showFallback && fallbackUrl ? fallbackUrl : thumbnailUrl}
                    alt={pref.song_title}
                    className="w-full h-full object-cover"
                    onError={() => !showFallback && fallbackUrl && handleImageError(pref.id)}
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center">
                    <Music className="w-5 h-5 text-neutral-400" />
                  </div>
                )}
              </div>

              {/* Song info */}
              <div className="flex-1 min-w-0">
                <p className="font-medium text-neutral-900 truncate text-sm">
                  {pref.song_title}
                </p>
                <p className="text-xs text-neutral-500 truncate">
                  {pref.artist}
                  {pref.genre && ` • ${pref.genre}`}
                </p>
              </div>

              {/* Actions */}
              <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                {/* Play button */}
                {pref.video_id && (
                  <button
                    onClick={() => handlePlay(pref)}
                    className="p-2 text-neutral-500 hover:text-primary-600 hover:bg-primary-50 rounded-lg transition-colors"
                    title={t('common.play')}
                  >
                    <Play className="w-4 h-4" />
                  </button>
                )}

                {/* Delete button */}
                <button
                  onClick={() => onDelete(pref.id)}
                  disabled={isDeleting === pref.id}
                  className={clsx(
                    "p-2 rounded-lg transition-colors",
                    type === 'likes' 
                      ? "text-neutral-500 hover:text-red-600 hover:bg-red-50"
                      : "text-neutral-500 hover:text-green-600 hover:bg-green-50",
                    isDeleting === pref.id && "opacity-50"
                  )}
                  title={type === 'likes' ? t('profile.removeLike') : t('profile.removeDislike')}
                >
                  {isDeleting === pref.id ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Trash2 className="w-4 h-4" />
                  )}
                </button>
              </div>
            </div>
          )
        })}
      </div>

      {/* Show more/less button */}
      {hasMore && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="w-full p-3 text-sm text-primary-600 hover:bg-primary-50 transition-colors flex items-center justify-center gap-1 border-t border-neutral-100"
        >
          {expanded ? (
            <>
              <ChevronUp className="w-4 h-4" />
              {t('common.showLess')}
            </>
          ) : (
            <>
              <ChevronDown className="w-4 h-4" />
              {t('profile.showMore', { count: preferences.length - 5 })}
            </>
          )}
        </button>
      )}
    </div>
  )
}
