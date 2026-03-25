import { useRef, useState, useEffect, useCallback } from 'react'
import { 
  Play, Pause, X, ChevronUp, ChevronDown, ExternalLink, Music,
  SkipBack, SkipForward, Volume2, VolumeX, ThumbsUp, ThumbsDown
} from 'lucide-react'
import { useQueryClient } from '@tanstack/react-query'
import { usePlayer } from '../context/PlayerContext'
import { useTranslation } from '../context/LanguageContext'
import { useAuth } from '../hooks/useAuth'
import { recommendationsApi } from '../services/api'
import { getThumbnailWithFallback } from '../utils/thumbnail'
import clsx from 'clsx'

// Declare YouTube IFrame API types
declare global {
  interface Window {
    YT: {
      Player: new (elementId: string, config: YouTubePlayerConfig) => YouTubePlayer
      PlayerState: {
        PLAYING: number
        PAUSED: number
        ENDED: number
        BUFFERING: number
      }
    }
    onYouTubeIframeAPIReady: () => void
  }
}

interface YouTubePlayerConfig {
  height: string
  width: string
  videoId: string
  playerVars: {
    autoplay: number
    controls: number
    modestbranding: number
    rel: number
    showinfo: number
    fs: number
  }
  events: {
    onReady: (event: { target: YouTubePlayer }) => void
    onStateChange: (event: { data: number }) => void
  }
}

interface YouTubePlayer {
  playVideo: () => void
  pauseVideo: () => void
  seekTo: (seconds: number, allowSeekAhead: boolean) => void
  getCurrentTime: () => number
  getDuration: () => number
  getVolume: () => number
  setVolume: (volume: number) => void
  isMuted: () => boolean
  mute: () => void
  unMute: () => void
  destroy: () => void
}

export default function MiniPlayer() {
  const { currentSong, isPlaying, isExpanded, pauseSong, resumeSong, stopSong, toggleExpanded } = usePlayer()
  const { t } = useTranslation()
  const { isAuthenticated, isGuest } = useAuth()
  const queryClient = useQueryClient()
  
  const [player, setPlayer] = useState<YouTubePlayer | null>(null)
  const [isPlayerReady, setIsPlayerReady] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [volume, setVolume] = useState(60) // Default volume 60%
  const [isMuted, setIsMuted] = useState(false)
  const [feedback, setFeedback] = useState<'like' | 'dislike' | null>(null)
  const [isApiLoaded, setIsApiLoaded] = useState(false)
  const [thumbnailError, setThumbnailError] = useState(false)
  
  const playerContainerRef = useRef<HTMLDivElement>(null)
  const progressInterval = useRef<number | null>(null)
  const lastVideoId = useRef<string | null>(null)

  // Load YouTube IFrame API
  useEffect(() => {
    if (window.YT) {
      setIsApiLoaded(true)
      return
    }

    const tag = document.createElement('script')
    tag.src = 'https://www.youtube.com/iframe_api'
    const firstScriptTag = document.getElementsByTagName('script')[0]
    firstScriptTag.parentNode?.insertBefore(tag, firstScriptTag)

    window.onYouTubeIframeAPIReady = () => {
      setIsApiLoaded(true)
    }
  }, [])

  // Initialize or update player when song changes
  useEffect(() => {
    // Only create player when: API loaded and song has video_id
    if (!isApiLoaded || !currentSong?.video_id) return
    
    // If video ID changed, recreate player
    if (lastVideoId.current !== currentSong.video_id) {
      lastVideoId.current = currentSong.video_id
      
      // Destroy existing player
      if (player) {
        try {
          player.destroy()
        } catch (e) {
          console.warn('Error destroying player:', e)
        }
        setPlayer(null)
      }
      
      setIsPlayerReady(false)
      setCurrentTime(0)
      setDuration(0)
      setFeedback(null)
      setThumbnailError(false)
      
      // Small delay to ensure DOM is ready
      setTimeout(() => {
        // Check if element exists
        const playerElement = document.getElementById('youtube-player')
        if (!playerElement) return
        
        try {
          const newPlayer = new window.YT.Player('youtube-player', {
            height: '100%',
            width: '100%',
            videoId: currentSong.video_id,
            host: 'https://www.youtube-nocookie.com', // Privacy mode - doesn't share session
            playerVars: {
              autoplay: 1,
              controls: 0,
              modestbranding: 1,
              rel: 0,
              showinfo: 0,
              fs: 0,
              origin: window.location.origin // Identify our app
            },
            events: {
              onReady: (event) => {
                setPlayer(event.target)
                setIsPlayerReady(true)
                setDuration(event.target.getDuration())
                // Apply user's saved volume instead of resetting to player default
                event.target.setVolume(volume)
                if (isMuted) {
                  event.target.mute()
                }
                event.target.playVideo()
              },
              onStateChange: (event) => {
                if (event.data === window.YT.PlayerState.PLAYING) {
                  resumeSong()
                } else if (event.data === window.YT.PlayerState.PAUSED) {
                  pauseSong()
                } else if (event.data === window.YT.PlayerState.ENDED) {
                  stopSong()
                }
              }
            }
          })
        } catch (e) {
          console.error('Error creating YouTube player:', e)
        }
      }, 100)
    }
  }, [isApiLoaded, currentSong?.video_id])

  // Update progress
  useEffect(() => {
    if (isPlaying && player && isPlayerReady) {
      progressInterval.current = window.setInterval(() => {
        try {
          const time = player.getCurrentTime()
          setCurrentTime(time)
        } catch (e) {
          // Player might have been destroyed
          if (progressInterval.current) {
            clearInterval(progressInterval.current)
          }
        }
      }, 500)
    }

    return () => {
      if (progressInterval.current) {
        clearInterval(progressInterval.current)
      }
    }
  }, [isPlaying, player, isPlayerReady])

  // Sync play/pause with player
  useEffect(() => {
    if (!player || !isPlayerReady) return
    
    try {
      if (isPlaying) {
        player.playVideo()
      } else {
        player.pauseVideo()
      }
    } catch (e) {
      console.warn('Error syncing play/pause:', e)
    }
  }, [isPlaying, player, isPlayerReady])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (player) {
        try {
          player.destroy()
        } catch (e) {
          console.warn('Error destroying player on unmount:', e)
        }
      }
      if (progressInterval.current) {
        clearInterval(progressInterval.current)
      }
    }
  }, [])

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const handleSeek = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    if (!player || !duration || !isPlayerReady) return
    
    try {
      const rect = e.currentTarget.getBoundingClientRect()
      const percent = (e.clientX - rect.left) / rect.width
      const newTime = percent * duration
      player.seekTo(newTime, true)
      setCurrentTime(newTime)
    } catch (err) {
      console.warn('Error seeking:', err)
    }
  }, [player, duration, isPlayerReady])

  const handlePlayPause = () => {
    if (isPlaying) {
      pauseSong()
    } else {
      resumeSong()
    }
  }

  const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newVolume = parseInt(e.target.value)
    setVolume(newVolume)
    if (player && isPlayerReady) {
      try {
        player.setVolume(newVolume)
        if (newVolume === 0) {
          player.mute()
          setIsMuted(true)
        } else if (isMuted) {
          player.unMute()
          setIsMuted(false)
        }
      } catch (err) {
        console.warn('Error changing volume:', err)
      }
    }
  }

  const toggleMute = () => {
    if (!player || !isPlayerReady) return
    try {
      if (isMuted) {
        player.unMute()
        setIsMuted(false)
      } else {
        player.mute()
        setIsMuted(true)
      }
    } catch (err) {
      console.warn('Error toggling mute:', err)
    }
  }

  const handleOpenYouTube = () => {
    if (currentSong?.video_id) {
      window.open(`https://music.youtube.com/watch?v=${currentSong.video_id}`, '_blank')
    } else if (currentSong) {
      const query = encodeURIComponent(`${currentSong.title} ${currentSong.artist}`)
      window.open(`https://music.youtube.com/search?q=${query}`, '_blank')
    }
  }

  const handleFeedback = async (score: number) => {
    if (!currentSong || (!isAuthenticated && !isGuest)) return
    
    const newFeedback = score > 0 ? 'like' : 'dislike'
    setFeedback(newFeedback)
    
    try {
      await recommendationsApi.submitFeedback(
        currentSong.title,
        currentSong.artist,
        score,
        currentSong.video_id,
        currentSong.genre,
        currentSong.mood ? [currentSong.mood] : undefined
      )
      
      // Invalidate preferences queries to update Profile page lists in real-time
      queryClient.invalidateQueries({ queryKey: ['preferences-counts'] })
      queryClient.invalidateQueries({ queryKey: ['liked-songs'] })
      queryClient.invalidateQueries({ queryKey: ['disliked-songs'] })
    } catch (error) {
      console.error('Failed to submit feedback:', error)
    }
  }

  const handleSkip = (direction: 'forward' | 'back') => {
    if (!player || !duration || !isPlayerReady) return
    try {
      const skipAmount = 10 // seconds
      const newTime = direction === 'forward' 
        ? Math.min(currentTime + skipAmount, duration)
        : Math.max(currentTime - skipAmount, 0)
      player.seekTo(newTime, true)
      setCurrentTime(newTime)
    } catch (err) {
      console.warn('Error skipping:', err)
    }
  }

  if (!currentSong) return null

  const videoId = currentSong.video_id
  const progress = duration > 0 ? (currentTime / duration) * 100 : 0

  return (
    <div className={clsx(
      "mini-player fixed bottom-0 left-0 right-0 z-50 transition-all duration-300",
      "bg-gradient-to-b from-neutral-900 to-neutral-950 border-t border-neutral-800",
      isExpanded ? "h-auto" : "h-[72px]"
    )}>
      {/* Progress bar (always visible at top) */}
      <div 
        className="absolute top-0 left-0 right-0 h-1 bg-neutral-800 cursor-pointer group"
        onClick={handleSeek}
      >
        <div 
          className="h-full bg-primary-500 transition-all duration-100"
          style={{ width: `${progress}%` }}
        />
        <div 
          className="absolute top-1/2 -translate-y-1/2 w-3 h-3 bg-primary-500 rounded-full opacity-0 group-hover:opacity-100 transition-opacity"
          style={{ left: `${progress}%`, transform: `translateX(-50%) translateY(-50%)` }}
        />
      </div>

      {/* Main Player Bar */}
      <div className="h-[72px] px-4 flex items-center gap-4 pt-1">
        {/* Left: Thumbnail + Song Info */}
        <div className="flex items-center gap-3 flex-1 min-w-0">
          {/* Thumbnail */}
          <div className="relative flex-shrink-0">
            {(() => {
              const { primary, fallback } = getThumbnailWithFallback(
                currentSong.thumbnail_url,
                currentSong.video_id
              )
              const displayUrl = thumbnailError && fallback ? fallback : primary
              
              return displayUrl ? (
                <img
                  src={displayUrl}
                  alt={`${currentSong.title} cover`}
                  className="w-12 h-12 rounded object-cover bg-neutral-800"
                  onError={() => !thumbnailError && setThumbnailError(true)}
                />
              ) : (
                <div className="w-12 h-12 rounded bg-neutral-800 flex items-center justify-center">
                  <Music className="w-5 h-5 text-neutral-500" />
                </div>
              )
            })()}
          </div>

          {/* Song Info */}
          <div className="min-w-0 flex-1">
            <h4 className="font-medium text-white truncate text-sm">
              {currentSong.title}
            </h4>
            <p className="text-xs text-neutral-400 truncate">
              {currentSong.artist}
              {currentSong.album && ` • ${currentSong.album}`}
            </p>
          </div>

          {/* Like/Dislike (only for registered users, hidden for guests) */}
          {isAuthenticated && !isGuest && (
            <div className="flex items-center gap-1 flex-shrink-0">
              <button
                onClick={() => handleFeedback(-1)}
                className={clsx(
                  "p-2 rounded-full transition-colors",
                  feedback === 'dislike' 
                    ? "text-red-500" 
                    : "text-neutral-400 hover:text-white hover:bg-neutral-800"
                )}
                title={t('songCard.dislike')}
              >
                <ThumbsDown className="w-4 h-4" />
              </button>
              <button
                onClick={() => handleFeedback(1)}
                className={clsx(
                  "p-2 rounded-full transition-colors",
                  feedback === 'like' 
                    ? "text-primary-500" 
                    : "text-neutral-400 hover:text-white hover:bg-neutral-800"
                )}
                title={t('songCard.like')}
              >
                <ThumbsUp className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>

        {/* Center: Playback Controls */}
        <div className="flex items-center gap-2">
          {/* Skip Back */}
          <button
            onClick={() => handleSkip('back')}
            className="p-2 text-neutral-400 hover:text-white transition-colors"
            title="Retroceder 10s"
          >
            <SkipBack className="w-5 h-5" />
          </button>

          {/* Play/Pause */}
          <button
            onClick={handlePlayPause}
            className="w-10 h-10 flex items-center justify-center bg-white hover:scale-105 text-black rounded-full transition-all"
            title={isPlaying ? t('player.pause') : t('player.play')}
          >
            {isPlaying ? (
              <Pause className="w-5 h-5" fill="black" />
            ) : (
              <Play className="w-5 h-5 ml-0.5" fill="black" />
            )}
          </button>

          {/* Skip Forward */}
          <button
            onClick={() => handleSkip('forward')}
            className="p-2 text-neutral-400 hover:text-white transition-colors"
            title="Avanzar 10s"
          >
            <SkipForward className="w-5 h-5" />
          </button>

          {/* Time */}
          <div className="text-xs text-neutral-400 w-24 text-center hidden sm:block">
            {formatTime(currentTime)} / {formatTime(duration)}
          </div>
        </div>

        {/* Right: Volume + Actions */}
        <div className="flex items-center gap-2 flex-1 justify-end">
          {/* Volume */}
          <div className="hidden md:flex items-center gap-2">
            <button
              onClick={toggleMute}
              className="p-2 text-neutral-400 hover:text-white transition-colors"
            >
              {isMuted || volume === 0 ? (
                <VolumeX className="w-5 h-5" />
              ) : (
                <Volume2 className="w-5 h-5" />
              )}
            </button>
            <input
              type="range"
              min="0"
              max="100"
              value={isMuted ? 0 : volume}
              onChange={handleVolumeChange}
              className="w-20 volume-slider"
              style={{ '--volume-percent': `${isMuted ? 0 : volume}%` } as React.CSSProperties}
            />
          </div>

          {/* Expand/Collapse */}
          <button
            onClick={toggleExpanded}
            className="p-2 text-neutral-400 hover:text-white hover:bg-neutral-800 rounded-full transition-colors"
            title={isExpanded ? t('player.collapse') : t('player.expand')}
          >
            {isExpanded ? (
              <ChevronDown className="w-5 h-5" />
            ) : (
              <ChevronUp className="w-5 h-5" />
            )}
          </button>

          {/* Open in YouTube */}
          <button
            onClick={handleOpenYouTube}
            className="p-2 text-neutral-400 hover:text-white hover:bg-neutral-800 rounded-full transition-colors"
            title={t('songCard.openInYouTube')}
          >
            <ExternalLink className="w-5 h-5" />
          </button>

          {/* Close */}
          <button
            onClick={stopSong}
            className="p-2 text-neutral-400 hover:text-red-500 hover:bg-neutral-800 rounded-full transition-colors"
            title={t('player.close')}
          >
            <X className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Hidden YouTube Player Container (always rendered for audio playback) */}
      {videoId && (
        <div 
          className={clsx(
            "transition-all duration-300",
            isExpanded ? "" : "sr-only"
          )}
          aria-hidden={!isExpanded}
        >
          <div className="px-4 pb-4">
            <div 
              ref={playerContainerRef}
              className="relative w-full max-w-3xl mx-auto aspect-video bg-black rounded-lg overflow-hidden"
            >
              <div id="youtube-player" className="w-full h-full" />
              
              {/* Loading overlay */}
              {!isPlayerReady && isExpanded && (
                <div className="absolute inset-0 flex items-center justify-center bg-black">
                  <div className="text-center">
                    <div className="w-10 h-10 border-4 border-primary-500 border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
                    <p className="text-neutral-400 text-sm">{t('songCard.loadingPreview')}</p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Expanded View - No Video Message */}
      {isExpanded && !videoId && (
        <div className="px-4 pb-4">
          <div 
            className="relative w-full max-w-3xl mx-auto aspect-video bg-black rounded-lg overflow-hidden"
          >
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="text-center">
                <Music className="w-16 h-16 text-neutral-600 mx-auto mb-4" />
                <p className="text-neutral-400 mb-4">{t('player.noVideo')}</p>
                <button
                  onClick={handleOpenYouTube}
                  className="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-full transition-colors text-sm"
                >
                  {t('player.searchOnYouTube')}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Song details in expanded view */}
      {isExpanded && (
        <div className="px-4 pb-4">
          <div className="text-center max-w-3xl mx-auto">
            <h3 className="font-semibold text-white text-xl">
              {currentSong.title}
            </h3>
            <p className="text-neutral-400 mt-1">
              {currentSong.artist}
              {currentSong.album && ` • ${currentSong.album}`}
            </p>
            
            {/* Tags */}
            <div className="flex flex-wrap justify-center gap-2 mt-3">
              {currentSong.genre && (
                <span className="text-xs px-3 py-1 bg-neutral-800 text-neutral-300 rounded-full">
                  {currentSong.genre}
                </span>
              )}
              {currentSong.mood && (
                <span className="text-xs px-3 py-1 bg-neutral-800 text-neutral-300 rounded-full">
                  {currentSong.mood}
                </span>
              )}
              {currentSong.duration && (
                <span className="text-xs px-3 py-1 bg-neutral-800 text-neutral-300 rounded-full">
                  {currentSong.duration}
                </span>
              )}
            </div>

            {/* Reason why recommended */}
            {currentSong.reason && (
              <p className="mt-4 text-sm text-neutral-500 italic max-w-lg mx-auto">
                "{currentSong.reason}"
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
