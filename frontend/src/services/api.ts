import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios'

const API_BASE_URL = '/api'

// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Helper to get token from either storage
const getToken = () => localStorage.getItem('access_token') || sessionStorage.getItem('access_token')

// Helper to get refresh token from either storage
const getRefreshToken = () => localStorage.getItem('refresh_token') || sessionStorage.getItem('refresh_token')

// Helper to check if tokens are in localStorage (persistent)
const isTokenPersistent = () => localStorage.getItem('access_token') !== null

// Helper to set tokens in the appropriate storage
const setTokens = (accessToken: string, refreshToken?: string) => {
  const persistent = isTokenPersistent()
  if (persistent) {
    localStorage.setItem('access_token', accessToken)
    if (refreshToken) localStorage.setItem('refresh_token', refreshToken)
  } else {
    sessionStorage.setItem('access_token', accessToken)
    if (refreshToken) sessionStorage.setItem('refresh_token', refreshToken)
  }
}

// Helper to clear all auth data from both storages
const clearAuthData = () => {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  localStorage.removeItem('session_id')
  sessionStorage.removeItem('access_token')
  sessionStorage.removeItem('refresh_token')
  sessionStorage.removeItem('session_id')
}

// Track if we're currently refreshing to avoid multiple refresh calls
let isRefreshing = false
let refreshSubscribers: ((token: string) => void)[] = []

const subscribeTokenRefresh = (callback: (token: string) => void) => {
  refreshSubscribers.push(callback)
}

const onTokenRefreshed = (token: string) => {
  refreshSubscribers.forEach(callback => callback(token))
  refreshSubscribers = []
}

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = getToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Handle auth errors with token refresh
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean }
    
    // Only try to refresh on 401 errors and if we haven't already retried
    if (error.response?.status === 401 && !originalRequest._retry) {
      const refreshToken = getRefreshToken()
      
      // If no refresh token, clear auth and reject
      if (!refreshToken) {
        clearAuthData()
        return Promise.reject(error)
      }
      
      // If we're already refreshing, queue this request
      if (isRefreshing) {
        return new Promise((resolve) => {
          subscribeTokenRefresh((token: string) => {
            originalRequest.headers.Authorization = `Bearer ${token}`
            resolve(api(originalRequest))
          })
        })
      }
      
      originalRequest._retry = true
      isRefreshing = true
      
      try {
        // Call refresh endpoint
        const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
          refresh_token: refreshToken
        })
        
        const { access_token, refresh_token: newRefreshToken } = response.data
        
        // Save new tokens
        setTokens(access_token, newRefreshToken)
        
        // Notify all queued requests
        onTokenRefreshed(access_token)
        
        // Retry the original request
        originalRequest.headers.Authorization = `Bearer ${access_token}`
        return api(originalRequest)
        
      } catch (refreshError) {
        // Refresh failed, clear auth and reject
        clearAuthData()
        refreshSubscribers = []
        return Promise.reject(refreshError)
      } finally {
        isRefreshing = false
      }
    }
    
    return Promise.reject(error)
  }
)

// Types
export interface Song {
  title: string
  artist: string
  reason?: string
  genre?: string
  mood?: string
  video_id?: string
  album?: string
  duration?: string
  thumbnail_url?: string
}

export interface RecommendationsResponse {
  recommendations: Song[]
  input_type: string
  session_id: string
  is_continuation: boolean
  used_chromadb: boolean
  chromadb_info: string | null
}

export interface AudioAnalysisResult {
  mood_tags: string[]
  genre_tags: string[]
  tempo_description: string
  energy_level: string
  search_queries: string[]
}

export interface AudioIdentificationResponse {
  identified: boolean
  title?: string
  artist?: string
  album?: string
  genre?: string
  release_year?: string
  cover_art_url?: string
  shazam_id?: string
  video_id?: string  // YouTube Music video ID for playback
  thumbnail_url?: string
  message?: string
  // CLAP audio analysis (for unidentified songs - Case 3)
  audio_analysis?: AudioAnalysisResult
}

export interface User {
  id: string
  email: string
  display_name: string
  is_active: boolean
}

export interface AuthTokens {
  access_token: string
  refresh_token?: string
  token_type: string
}

export interface GuestSession {
  access_token: string
  token_type: string
  session_id: string
  message: string
}

export interface PreferenceItem {
  id: string
  song_title: string
  artist: string
  genre?: string
  video_id?: string
  mood_tags?: string[]
}

export interface PreferencesResponse {
  preferences: PreferenceItem[]
  total: number
  type: 'likes' | 'dislikes'
}

export interface PreferencesCountResponse {
  likes: number
  dislikes: number
}

// Auth API
export const authApi = {
  register: async (email: string, password: string, displayName: string): Promise<AuthTokens> => {
    const response = await api.post('/auth/register', {
      email,
      password,
      display_name: displayName,
    })
    return response.data
  },

  login: async (email: string, password: string): Promise<AuthTokens> => {
    const response = await api.post('/auth/login', { email, password })
    return response.data
  },

  createGuestSession: async (): Promise<GuestSession> => {
    const response = await api.post('/auth/guest')
    return response.data
  },

  getCurrentUser: async (): Promise<User> => {
    const response = await api.get('/auth/me')
    return response.data
  },

  getAuthStatus: async () => {
    const response = await api.get('/auth/status')
    return response.data
  },

  refreshToken: async (refreshToken: string): Promise<AuthTokens> => {
    const response = await api.post('/auth/refresh', { refresh_token: refreshToken })
    return response.data
  },
}

// Helper to log ChromaDB usage
const logChromaDBUsage = (response: RecommendationsResponse, endpoint: string) => {
  const prefix = '[VibeFinder API]'
  if (response.used_chromadb) {
    console.log(
      `%c${prefix} ChromaDB USED ✓`,
      'color: #22c55e; font-weight: bold',
      `\n  Endpoint: ${endpoint}`,
      `\n  Info: ${response.chromadb_info || 'Personalized recommendations'}`,
      `\n  Songs returned: ${response.recommendations.length}`
    )
  } else {
    console.log(
      `%c${prefix} ChromaDB NOT used`,
      'color: #f59e0b; font-weight: bold',
      `\n  Endpoint: ${endpoint}`,
      `\n  Reason: Guest user or no stored preferences`,
      `\n  Songs returned: ${response.recommendations.length}`
    )
  }
}

// Recommendations API
export const recommendationsApi = {
  getMoodRecommendations: async (
    mood: string,
    previousSongs?: string[]
  ): Promise<RecommendationsResponse> => {
    const response = await api.post('/recommendations/mood', {
      mood,
      previous_songs: previousSongs,
    })
    logChromaDBUsage(response.data, '/recommendations/mood')
    return response.data
  },

  getAudioRecommendations: async (
    songTitle: string,
    songArtist: string,
    songGenre?: string,
    previousSongs?: string[]
  ): Promise<RecommendationsResponse> => {
    const response = await api.post('/recommendations/audio', {
      song_title: songTitle,
      song_artist: songArtist,
      song_genre: songGenre,
      previous_songs: previousSongs,
    })
    logChromaDBUsage(response.data, '/recommendations/audio')
    return response.data
  },

  getCombinedRecommendations: async (
    mood?: string,
    songTitle?: string,
    songArtist?: string,
    songGenre?: string,
    previousSongs?: string[]
  ): Promise<RecommendationsResponse> => {
    const response = await api.post('/recommendations/combined', {
      mood,
      song_title: songTitle,
      song_artist: songArtist,
      song_genre: songGenre,
      previous_songs: previousSongs,
    })
    logChromaDBUsage(response.data, '/recommendations/combined')
    return response.data
  },

  // Case 3: Recommendations from CLAP audio analysis (unidentified song)
  getAudioAnalysisRecommendations: async (
    audioAnalysis: AudioAnalysisResult,
    previousSongs?: string[]
  ): Promise<RecommendationsResponse> => {
    const response = await api.post('/recommendations/audio-analysis', {
      mood_tags: audioAnalysis.mood_tags,
      genre_tags: audioAnalysis.genre_tags,
      tempo_description: audioAnalysis.tempo_description,
      energy_level: audioAnalysis.energy_level,
      search_queries: audioAnalysis.search_queries,
      previous_songs: previousSongs,
    })
    logChromaDBUsage(response.data, '/recommendations/audio-analysis')
    return response.data
  },

  submitFeedback: async (
    songTitle: string,
    artist: string,
    feedbackScore: number,
    videoId?: string,
    genre?: string,
    moodTags?: string[]
  ) => {
    const response = await api.post('/recommendations/feedback', {
      song_title: songTitle,
      artist,
      feedback_score: feedbackScore,
      video_id: videoId,
      genre,
      mood_tags: moodTags,
    })
    const prefix = '[VibeFinder API]'
    const action = feedbackScore > 0 ? 'LIKED' : 'DISLIKED'
    const savedToChroma = response.data?.saved_to_chromadb ?? false
    if (savedToChroma) {
      console.log(
        `%c${prefix} Feedback saved to ChromaDB ✓`,
        'color: #22c55e; font-weight: bold',
        `\n  Song: ${songTitle} - ${artist}`,
        `\n  Action: ${action}`,
        `\n  Will affect future recommendations`
      )
    } else {
      console.log(
        `%c${prefix} Feedback NOT saved to ChromaDB`,
        'color: #f59e0b; font-weight: bold',
        `\n  Song: ${songTitle} - ${artist}`,
        `\n  Action: ${action}`,
        `\n  Reason: Guest session - feedback not persisted`
      )
    }
    return response.data
  },

  getHistory: async (limit = 10, includeRecommendations = false) => {
    const response = await api.get(
      `/recommendations/history?limit=${limit}&include_recommendations=${includeRecommendations}`
    )
    return response.data
  },

  getHistoryItem: async (historyId: string) => {
    const response = await api.get(`/recommendations/history/${historyId}`)
    return response.data
  },

  // Preferences endpoints
  getPreferencesCounts: async (): Promise<PreferencesCountResponse> => {
    const response = await api.get('/recommendations/preferences/counts')
    return response.data
  },

  getLikedSongs: async (limit = 100): Promise<PreferencesResponse> => {
    const response = await api.get(`/recommendations/preferences/likes?limit=${limit}`)
    return response.data
  },

  getDislikedSongs: async (limit = 100): Promise<PreferencesResponse> => {
    const response = await api.get(`/recommendations/preferences/dislikes?limit=${limit}`)
    return response.data
  },

  deletePreference: async (preferenceType: 'likes' | 'dislikes', preferenceId: string) => {
    const response = await api.delete(`/recommendations/preferences/${preferenceType}/${preferenceId}`)
    return response.data
  },
}

// Audio API
export const audioApi = {
  identifyAudio: async (audioFile: File): Promise<AudioIdentificationResponse> => {
    const formData = new FormData()
    formData.append('audio_file', audioFile)

    const response = await api.post('/audio/identify', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },

  searchSongs: async (query: string, limit = 5) => {
    const response = await api.get(`/audio/search?query=${encodeURIComponent(query)}&limit=${limit}`)
    return response.data
  },
}

// YouTube Music API
export const youtubeApi = {
  searchSongs: async (query: string, limit = 10) => {
    const response = await api.get(`/youtube/search?query=${encodeURIComponent(query)}&limit=${limit}`)
    return response.data
  },

  getPlaylists: async () => {
    const response = await api.get('/youtube/playlists')
    return response.data
  },

  createPlaylist: async (title: string, description = '', privacyStatus = 'PRIVATE') => {
    const response = await api.post('/youtube/playlists', {
      title,
      description,
      privacy_status: privacyStatus,
    })
    return response.data
  },

  addToPlaylist: async (videoId: string, playlistId: string) => {
    const response = await api.post('/youtube/playlists/add', {
      video_id: videoId,
      playlist_id: playlistId,
    })
    return response.data
  },

  getSongDetails: async (videoId: string) => {
    const response = await api.get(`/youtube/song/${videoId}`)
    return response.data
  },
}

export default api
