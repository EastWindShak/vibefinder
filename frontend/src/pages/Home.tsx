import { useState, useCallback, useEffect, useRef } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { Mic, MessageSquare, Music2, History, Loader2 } from 'lucide-react'
import MoodSelector from '../components/MoodSelector'
import RecommendationList from '../components/RecommendationList'
import { 
  recommendationsApi, 
  Song, 
  AudioIdentificationResponse,
  AudioAnalysisResult
} from '../services/api'
import { useAuth } from '../hooks/useAuth'
import { useTranslation } from '../context/LanguageContext'

type RecommendationType = 'mood' | 'audio' | 'combined' | 'audio_analysis'

export default function Home() {
  const { isAuthenticated, isGuest, isLoading: isAuthLoading, loginAsGuest } = useAuth()
  const { t } = useTranslation()
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()
  
  const [recommendations, setRecommendations] = useState<Song[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [isLoadingHistory, setIsLoadingHistory] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [identifiedSong, setIdentifiedSong] = useState<AudioIdentificationResponse | null>(null)
  const [currentAudioAnalysis, setCurrentAudioAnalysis] = useState<AudioAnalysisResult | null>(null)
  const [currentInputType, setCurrentInputType] = useState<RecommendationType>('mood')
  const [historyQuery, setHistoryQuery] = useState<string | null>(null)
  const lastMoodRef = useRef<string>('')
  const loadedHistoryRef = useRef<string | null>(null)

  // Auto-create guest session if not authenticated (wait for auth check to complete first)
  useEffect(() => {
    if (!isAuthLoading && !isAuthenticated) {
      loginAsGuest()
    }
  }, [isAuthenticated, isAuthLoading, loginAsGuest])

  // Load history item if ?history=ID is present
  useEffect(() => {
    const historyId = searchParams.get('history')
    
    if (historyId && historyId !== loadedHistoryRef.current && isAuthenticated) {
      loadedHistoryRef.current = historyId
      setIsLoadingHistory(true)
      
      recommendationsApi.getHistoryItem(historyId)
        .then((data) => {
          // Set the query type
          setCurrentInputType(data.query_type as RecommendationType)
          
          // Set the original query for display
          if (data.query_type === 'mood') {
            setHistoryQuery(data.input_data.mood)
            lastMoodRef.current = data.input_data.mood
          } else if (data.query_type === 'combined') {
            setHistoryQuery(`${data.input_data.mood || ''} + ${data.input_data.song_title || ''}`)
            lastMoodRef.current = data.input_data.mood || ''
            if (data.input_data.song_title) {
              setIdentifiedSong({
                identified: true,
                title: data.input_data.song_title,
                artist: data.input_data.song_artist,
                genre: data.input_data.song_genre
              })
            }
          } else {
            setHistoryQuery(`${data.input_data.song_title} - ${data.input_data.song_artist}`)
            setIdentifiedSong({
              identified: true,
              title: data.input_data.song_title,
              artist: data.input_data.song_artist,
              genre: data.input_data.song_genre
            })
          }
          
          // Load the saved recommendations
          // The recommendations are stored as { recommendations: [...], input_type, ... }
          if (data.recommendations?.recommendations) {
            setRecommendations(data.recommendations.recommendations)
          }
        })
        .catch((err) => {
          console.error('Failed to load history item:', err)
          setError(t('home.errorLoadingHistory'))
          // Clear the history param on error
          setSearchParams({})
        })
        .finally(() => {
          setIsLoadingHistory(false)
        })
    }
  }, [searchParams, isAuthenticated, t, setSearchParams])

  const handleMoodSubmit = useCallback(async (
    mood: string, 
    song?: AudioIdentificationResponse,
    audioAnalysis?: AudioAnalysisResult
  ) => {
    setIsLoading(true)
    setError(null)
    lastMoodRef.current = mood

    // Determine request type based on inputs
    const hasMood = mood && mood.trim().length > 0
    const hasSong = song && song.title && song.artist
    const hasAudioAnalysis = audioAnalysis && audioAnalysis.mood_tags && audioAnalysis.mood_tags.length > 0

    if (hasMood && hasSong) {
      // Combined recommendations (mood + identified song)
      setCurrentInputType('combined')
      setIdentifiedSong(song)
      setCurrentAudioAnalysis(null)
      try {
        const response = await recommendationsApi.getCombinedRecommendations(
          mood,
          song.title,
          song.artist,
          song.genre
        )
        setRecommendations(response.recommendations)
      } catch (err) {
        setError(t('home.errorGenerating'))
        console.error(err)
      }
    } else if (hasSong) {
      // Case 2: Audio identified (song reference without mood text)
      setCurrentInputType('audio')
      setIdentifiedSong(song)
      setCurrentAudioAnalysis(null)
      try {
        const response = await recommendationsApi.getAudioRecommendations(
          song.title || 'Unknown',
          song.artist || 'Unknown',
          song.genre
        )
        setRecommendations(response.recommendations)
      } catch (err) {
        setError(t('home.errorGenerating'))
        console.error(err)
      }
    } else if (hasAudioAnalysis) {
      // Case 3: Audio NOT identified - use CLAP analysis
      setCurrentInputType('audio_analysis')
      setIdentifiedSong(null)
      setCurrentAudioAnalysis(audioAnalysis)
      try {
        const response = await recommendationsApi.getAudioAnalysisRecommendations(audioAnalysis)
        setRecommendations(response.recommendations)
      } catch (err) {
        setError(t('home.errorGenerating'))
        console.error(err)
      }
    } else if (hasMood) {
      // Case 1: Mood only (text input)
      setCurrentInputType('mood')
      setIdentifiedSong(null)
      setCurrentAudioAnalysis(null)
      try {
        const response = await recommendationsApi.getMoodRecommendations(mood)
        setRecommendations(response.recommendations)
      } catch (err) {
        setError(t('home.errorGenerating'))
        console.error(err)
      }
    }

    setIsLoading(false)
  }, [t])

  const handleLoadMore = useCallback(async (previousSongs: string[]) => {
    setIsLoading(true)

    try {
      let response
      if (currentInputType === 'combined' && identifiedSong) {
        // Combined: use both mood and song
        response = await recommendationsApi.getCombinedRecommendations(
          lastMoodRef.current || 'similar to previous recommendations',
          identifiedSong.title,
          identifiedSong.artist,
          identifiedSong.genre,
          previousSongs
        )
      } else if (currentInputType === 'audio' && identifiedSong) {
        // Case 2: Identified song
        response = await recommendationsApi.getAudioRecommendations(
          identifiedSong.title || 'Unknown',
          identifiedSong.artist || 'Unknown',
          identifiedSong.genre,
          previousSongs
        )
      } else if (currentInputType === 'audio_analysis' && currentAudioAnalysis) {
        // Case 3: CLAP audio analysis
        response = await recommendationsApi.getAudioAnalysisRecommendations(
          currentAudioAnalysis,
          previousSongs
        )
      } else {
        // Case 1: Mood only
        response = await recommendationsApi.getMoodRecommendations(
          lastMoodRef.current || 'similar to previous recommendations',
          previousSongs
        )
      }
      
      // Append new recommendations
      setRecommendations(prev => [...prev, ...response.recommendations])
    } catch (err) {
      setError(t('home.errorLoadingMore'))
      console.error(err)
    } finally {
      setIsLoading(false)
    }
  }, [currentInputType, identifiedSong, currentAudioAnalysis, t])

  const handleReset = useCallback(() => {
    setRecommendations([])
    setIdentifiedSong(null)
    setError(null)
    setHistoryQuery(null)
    loadedHistoryRef.current = null
    // Clear the history param from URL
    if (searchParams.has('history')) {
      setSearchParams({})
    }
  }, [searchParams, setSearchParams])

  return (
    <div className="space-y-8">
      {/* Hero section */}
      <div className="text-center py-8">
        <h1 className="text-4xl font-bold text-neutral-900 mb-4">
          {t('home.title')}
        </h1>
        <p className="text-lg text-neutral-500 max-w-2xl mx-auto">
          {t('home.subtitle')}
          {isGuest && (
            <span className="text-primary-600"> ({t('common.guestMode')})</span>
          )}
        </p>
      </div>

      {/* Loading history */}
      {isLoadingHistory && (
        <div className="flex items-center justify-center py-12">
          <div className="text-center">
            <Loader2 className="w-10 h-10 text-primary-600 animate-spin mx-auto mb-4" />
            <p className="text-neutral-500">{t('home.loadingHistory')}</p>
          </div>
        </div>
      )}

      {/* Restored from history banner */}
      {historyQuery && recommendations.length > 0 && !isLoadingHistory && (
        <div className="bg-primary-50 border border-primary-200 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-primary-100 rounded-lg flex items-center justify-center">
                <History className="w-5 h-5 text-primary-600" />
              </div>
              <div>
                <p className="text-sm text-primary-600 font-medium">{t('home.restoredFromHistory')}</p>
                <p className="text-neutral-700 font-medium truncate max-w-md">
                  "{historyQuery}"
                </p>
              </div>
            </div>
            <button
              onClick={handleReset}
              className="text-primary-600 hover:text-primary-700 text-sm font-medium"
            >
              {t('home.newSearch')}
            </button>
          </div>
        </div>
      )}

      {/* Error message */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-center">
          <p className="text-red-700">{error}</p>
          <button
            onClick={() => setError(null)}
            className="text-red-600 underline text-sm mt-2 hover:no-underline"
          >
            {t('common.close')}
          </button>
        </div>
      )}

      {/* Identified song banner */}
      {identifiedSong && recommendations.length > 0 && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <div className="flex items-center gap-4">
            {identifiedSong.cover_art_url ? (
              <img
                src={identifiedSong.cover_art_url}
                alt="Album cover"
                className="w-16 h-16 rounded-lg object-cover"
              />
            ) : (
              <div className="w-16 h-16 rounded-lg bg-green-100 flex items-center justify-center">
                <Music2 className="w-8 h-8 text-green-600" />
              </div>
            )}
            <div>
              <p className="text-sm text-green-600 font-medium">{t('home.songIdentified')}</p>
              <p className="text-lg font-semibold text-neutral-900">
                {identifiedSong.title}
              </p>
              <p className="text-neutral-600">{identifiedSong.artist}</p>
            </div>
          </div>
        </div>
      )}

      {/* Input section - MoodSelector handles both mood and audio */}
      {recommendations.length === 0 && !isLoading && (
        <div className="max-w-2xl mx-auto">
          <MoodSelector onMoodSubmit={handleMoodSubmit} isLoading={isLoading} />
        </div>
      )}

      {/* Recommendations */}
      <RecommendationList
        songs={recommendations}
        inputType={currentInputType}
        isLoading={isLoading}
        onLoadMore={handleLoadMore}
        onReset={handleReset}
      />

      {/* Feature cards - only show when no recommendations */}
      {recommendations.length === 0 && !isLoading && (
        <div className="grid md:grid-cols-3 gap-6 pt-8">
          <div className="card p-6 text-center">
            <div className="w-12 h-12 bg-primary-100 rounded-xl flex items-center justify-center mx-auto mb-4">
              <Mic className="w-6 h-6 text-primary-600" />
            </div>
            <h3 className="font-semibold text-neutral-900 mb-2">
              {t('home.features.audioId.title')}
            </h3>
            <p className="text-sm text-neutral-500">
              {t('home.features.audioId.description')}
            </p>
          </div>

          <div className="card p-6 text-center">
            <div className="w-12 h-12 bg-primary-100 rounded-xl flex items-center justify-center mx-auto mb-4">
              <MessageSquare className="w-6 h-6 text-primary-600" />
            </div>
            <h3 className="font-semibold text-neutral-900 mb-2">
              {t('home.features.moodBased.title')}
            </h3>
            <p className="text-sm text-neutral-500">
              {t('home.features.moodBased.description')}
            </p>
          </div>

          <div className="card p-6 text-center">
            <div className="w-12 h-12 bg-primary-100 rounded-xl flex items-center justify-center mx-auto mb-4">
              <Music2 className="w-6 h-6 text-primary-600" />
            </div>
            <h3 className="font-semibold text-neutral-900 mb-2">
              {t('home.features.learns.title')}
            </h3>
            <p className="text-sm text-neutral-500">
              {t('home.features.learns.description')}
            </p>
          </div>
        </div>
      )}
    </div>
  )
}
