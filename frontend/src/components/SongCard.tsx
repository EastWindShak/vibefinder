import { useState } from 'react'
import { Play, ThumbsUp, ThumbsDown, ExternalLink, Music } from 'lucide-react'
import { useQueryClient } from '@tanstack/react-query'
import { Song, recommendationsApi } from '../services/api'
import { useAuth } from '../hooks/useAuth'
import { useTranslation } from '../context/LanguageContext'
import { usePlayer } from '../context/PlayerContext'
import { getThumbnailWithFallback } from '../utils/thumbnail'
import clsx from 'clsx'

interface SongCardProps {
  song: Song
  onFeedbackSubmitted?: () => void
}

export default function SongCard({ song, onFeedbackSubmitted }: SongCardProps) {
  const { isAuthenticated, isGuest } = useAuth()
  const { t } = useTranslation()
  const { currentSong, isPlaying, playSong } = usePlayer()
  const queryClient = useQueryClient()
  const [feedbackGiven, setFeedbackGiven] = useState<'like' | 'dislike' | null>(null)
  const [isSubmittingFeedback, setIsSubmittingFeedback] = useState(false)
  const [imgError, setImgError] = useState(false)

  // Get thumbnail with fallback to YouTube
  const { primary: thumbnailUrl, fallback: fallbackUrl } = getThumbnailWithFallback(
    song.thumbnail_url,
    song.video_id
  )
  
  const handleImgError = () => {
    if (!imgError && fallbackUrl) {
      setImgError(true)
    }
  }
  
  const displayThumbnail = imgError ? fallbackUrl : thumbnailUrl

  // Check if this song is currently playing
  const isCurrentSong = currentSong?.video_id === song.video_id && 
                        currentSong?.title === song.title

  const handleFeedback = async (score: number) => {
    if (!isAuthenticated) return
    
    setIsSubmittingFeedback(true)
    try {
      await recommendationsApi.submitFeedback(
        song.title,
        song.artist,
        score,
        song.video_id,
        song.genre,
        song.mood ? [song.mood] : undefined
      )
      setFeedbackGiven(score > 0 ? 'like' : 'dislike')
      
      // Invalidate preferences queries to update Profile page lists in real-time
      queryClient.invalidateQueries({ queryKey: ['preferences-counts'] })
      queryClient.invalidateQueries({ queryKey: ['liked-songs'] })
      queryClient.invalidateQueries({ queryKey: ['disliked-songs'] })
      
      onFeedbackSubmitted?.()
    } catch (error) {
      console.error('Error submitting feedback:', error)
    } finally {
      setIsSubmittingFeedback(false)
    }
  }

  const handlePlayOnYouTube = () => {
    if (song.video_id) {
      window.open(`https://music.youtube.com/watch?v=${song.video_id}`, '_blank')
    } else {
      // Search on YouTube Music
      const query = encodeURIComponent(`${song.title} ${song.artist}`)
      window.open(`https://music.youtube.com/search?q=${query}`, '_blank')
    }
  }

  const handlePlayPreview = () => {
    if (!song.video_id) {
      // No video ID, fall back to YouTube Music
      handlePlayOnYouTube()
      return
    }
    playSong(song)
  }

  return (
    <div className={clsx(
      "card song-card p-4 transition-all duration-300 hover:shadow-md",
      isCurrentSong && isPlaying && "ring-2 ring-primary-300 shadow-md"
    )}>
      <div className="flex gap-4">
        {/* Thumbnail */}
        <div className="relative flex-shrink-0 w-20 h-20 rounded-lg overflow-hidden">
          {displayThumbnail ? (
            <img
              src={displayThumbnail}
              alt={`${song.title} cover`}
              className="w-full h-full object-cover bg-neutral-200"
              onError={handleImgError}
            />
          ) : (
            <div className="w-full h-full bg-neutral-200 flex items-center justify-center">
              <Music className="w-8 h-8 text-neutral-400" />
            </div>
          )}
          
          {/* Play button overlay */}
          <button
            onClick={handlePlayPreview}
            className={clsx(
              "absolute inset-0 flex items-center justify-center transition-all",
              isCurrentSong && isPlaying
                ? "bg-primary-600/80 opacity-100" 
                : "bg-black/40 opacity-0 hover:opacity-100"
            )}
            title={t('songCard.preview')}
          >
            <Play className="w-6 h-6 text-white" fill="white" />
          </button>

          {/* Playing indicator */}
          {isCurrentSong && isPlaying && (
            <div className="absolute -top-1 -right-1 w-3 h-3 bg-primary-500 rounded-full animate-pulse" />
          )}
        </div>

        {/* Song info */}
        <div className="flex-1 min-w-0">
          <h3 className={clsx(
            "font-semibold truncate",
            isCurrentSong && isPlaying ? "text-primary-600" : "text-neutral-900"
          )} title={song.title}>
            {song.title}
          </h3>
          <p className="text-sm text-neutral-500 truncate" title={song.artist}>
            {song.artist}
          </p>
          
          {/* Metadata */}
          <div className="flex flex-wrap gap-2 mt-2">
            {song.album && (
              <span className="text-xs px-2 py-0.5 bg-neutral-100 text-neutral-600 rounded">
                {song.album}
              </span>
            )}
            {song.genre && (
              <span className="text-xs px-2 py-0.5 bg-primary-50 text-primary-700 rounded">
                {song.genre}
              </span>
            )}
            {song.mood && (
              <span className="text-xs px-2 py-0.5 bg-blue-50 text-blue-700 rounded">
                {song.mood}
              </span>
            )}
            {song.duration && (
              <span className="text-xs text-neutral-400">
                {song.duration}
              </span>
            )}
          </div>

          {/* Reason */}
          {song.reason && (
            <p className="text-sm text-neutral-500 mt-2 line-clamp-2">
              {song.reason}
            </p>
          )}
        </div>

        {/* Actions */}
        <div className="flex flex-col gap-2 flex-shrink-0">
          {/* Preview button */}
          <button
            onClick={handlePlayPreview}
            className={clsx(
              "p-2 rounded-lg transition-colors",
              isCurrentSong && isPlaying
                ? "text-primary-600 bg-primary-50"
                : "text-neutral-500 hover:text-primary-600 hover:bg-primary-50"
            )}
            title={t('songCard.preview')}
          >
            <Play className="w-5 h-5" />
          </button>

          {/* Play on YouTube Music */}
          <button
            onClick={handlePlayOnYouTube}
            className="p-2 text-neutral-500 hover:text-primary-600 hover:bg-primary-50 rounded-lg transition-colors"
            title={t('songCard.playOnYouTube')}
          >
            <ExternalLink className="w-5 h-5" />
          </button>

          {/* Feedback buttons (only for registered users, hidden for guests) */}
          {isAuthenticated && !isGuest && (
            <>
              <button
                onClick={() => handleFeedback(1)}
                disabled={isSubmittingFeedback || feedbackGiven !== null}
                className={clsx(
                  'p-2 rounded-lg transition-colors',
                  feedbackGiven === 'like'
                    ? 'text-green-600 bg-green-50'
                    : 'text-neutral-500 hover:text-green-600 hover:bg-green-50',
                  'disabled:opacity-50'
                )}
                title={t('songCard.like')}
              >
                <ThumbsUp className="w-5 h-5" />
              </button>
              <button
                onClick={() => handleFeedback(-1)}
                disabled={isSubmittingFeedback || feedbackGiven !== null}
                className={clsx(
                  'p-2 rounded-lg transition-colors',
                  feedbackGiven === 'dislike'
                    ? 'text-red-600 bg-red-50'
                    : 'text-neutral-500 hover:text-red-600 hover:bg-red-50',
                  'disabled:opacity-50'
                )}
                title={t('songCard.dislike')}
              >
                <ThumbsDown className="w-5 h-5" />
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
