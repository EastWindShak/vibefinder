import { useState } from 'react'
import { RefreshCw, Loader2, ListMusic, Sparkles } from 'lucide-react'
import { Song } from '../services/api'
import SongCard from './SongCard'
import { useTranslation } from '../context/LanguageContext'

interface RecommendationListProps {
  songs: Song[]
  inputType: 'mood' | 'audio' | 'combined'
  isLoading: boolean
  onLoadMore: (previousSongs: string[]) => void
  onReset: () => void
}

const getTypeTranslationKey = (inputType: 'mood' | 'audio' | 'combined') => {
  switch (inputType) {
    case 'combined':
      return 'recommendations.basedOnCombined'
    case 'audio':
      return 'recommendations.basedOnSong'
    default:
      return 'recommendations.basedOnMood'
  }
}

export default function RecommendationList({
  songs,
  inputType,
  isLoading,
  onLoadMore,
  onReset,
}: RecommendationListProps) {
  const { t } = useTranslation()
  const [loadingMore, setLoadingMore] = useState(false)

  const handleLoadMore = async () => {
    setLoadingMore(true)
    const previousSongsList = songs.map(s => `${s.title} - ${s.artist}`)
    await onLoadMore(previousSongsList)
    setLoadingMore(false)
  }

  if (isLoading && songs.length === 0) {
    return (
      <div className="card p-12 text-center">
        <Loader2 className="w-12 h-12 text-primary-600 animate-spin mx-auto mb-4" />
        <h3 className="text-lg font-semibold text-neutral-900 mb-2">
          {t('recommendations.generating')}
        </h3>
        <p className="text-neutral-500">
          {t('recommendations.generatingSubtitle', { 
            type: t(getTypeTranslationKey(inputType))
          })}
        </p>
      </div>
    )
  }

  if (songs.length === 0) {
    return null
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-primary-100 rounded-lg flex items-center justify-center">
            {inputType === 'mood' ? (
              <Sparkles className="w-5 h-5 text-primary-600" />
            ) : (
              <ListMusic className="w-5 h-5 text-primary-600" />
            )}
          </div>
          <div>
            <h2 className="text-xl font-semibold text-neutral-900">
              {t('recommendations.title')}
            </h2>
            <p className="text-sm text-neutral-500">
              {t('recommendations.songsBasedOn', {
                count: songs.length,
                type: t(getTypeTranslationKey(inputType))
              })}
            </p>
          </div>
        </div>

        <button
          onClick={onReset}
          className="btn btn-outline text-sm"
        >
          <RefreshCw className="w-4 h-4 mr-2" />
          {t('recommendations.newSearch')}
        </button>
      </div>

      {/* Song list */}
      <div className="space-y-3">
        {songs.map((song, index) => (
          <SongCard
            key={`${song.title}-${song.artist}-${index}`}
            song={song}
          />
        ))}
      </div>

      {/* Load more button */}
      <div className="flex justify-center pt-4">
        <button
          onClick={handleLoadMore}
          disabled={loadingMore}
          className="btn btn-primary px-8"
        >
          {loadingMore ? (
            <>
              <Loader2 className="w-5 h-5 mr-2 animate-spin" />
              {t('recommendations.loadingMore')}
            </>
          ) : (
            <>
              <RefreshCw className="w-5 h-5 mr-2" />
              {t('recommendations.loadMore')}
            </>
          )}
        </button>
      </div>

      {/* Info banner for guests */}
      <div className="bg-primary-50 border border-primary-100 rounded-lg p-4 text-center">
        <p className="text-primary-800 text-sm">
          <strong>{t('recommendations.likeBanner')}</strong>{' '}
          <a href="/login" className="underline hover:no-underline">
            {t('recommendations.createAccountBanner')}
          </a>
        </p>
      </div>
    </div>
  )
}
