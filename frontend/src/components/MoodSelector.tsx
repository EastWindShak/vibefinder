import { useState, useRef, useEffect, useCallback } from 'react'
import { Sparkles, Send, Zap, Paperclip, X, Music2, Loader2, Mic, Square, MessageSquare, Play, Pause } from 'lucide-react'
import { useTranslation } from '../context/LanguageContext'
import { usePlayer } from '../context/PlayerContext'
import { audioApi, AudioIdentificationResponse, AudioAnalysisResult } from '../services/api'

interface MoodSelectorProps {
  onMoodSubmit: (
    mood: string, 
    identifiedSong?: AudioIdentificationResponse,
    audioAnalysis?: AudioAnalysisResult  // Case 3: CLAP analysis for unidentified songs
  ) => void
  isLoading: boolean
}

type RecordingMode = 'voice' | 'song' | null

export default function MoodSelector({ onMoodSubmit, isLoading }: MoodSelectorProps) {
  const { t } = useTranslation()
  const { playSong, currentSong, isPlaying } = usePlayer()
  const [customMood, setCustomMood] = useState('')
  const [identifiedSong, setIdentifiedSong] = useState<AudioIdentificationResponse | null>(null)
  const [audioAnalysis, setAudioAnalysis] = useState<AudioAnalysisResult | null>(null)  // Case 3: CLAP analysis
  const [isIdentifying, setIsIdentifying] = useState(false)
  const [audioError, setAudioError] = useState<string | null>(null)
  const [songNotRecognized, setSongNotRecognized] = useState(false) // Track when identification fails
  const [capturedAudioUrl, setCapturedAudioUrl] = useState<string | null>(null) // Store captured audio for playback
  const [isPlayingCaptured, setIsPlayingCaptured] = useState(false)
  const capturedAudioRef = useRef<HTMLAudioElement | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  
  // Recording state
  const [showRecordMenu, setShowRecordMenu] = useState(false)
  const [recordingMode, setRecordingMode] = useState<RecordingMode>(null)
  const [isRecording, setIsRecording] = useState(false)
  const [recordingTime, setRecordingTime] = useState(0)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const audioChunksRef = useRef<Blob[]>([])
  const timerRef = useRef<NodeJS.Timeout | null>(null)
  const menuRef = useRef<HTMLDivElement>(null)
  
  // Speech recognition
  const recognitionRef = useRef<SpeechRecognition | null>(null)

  const MOOD_SUGGESTIONS = [
    { labelKey: 'moodSelector.moods.energetic', mood: 'energetic and upbeat, perfect for working out or dancing' },
    { labelKey: 'moodSelector.moods.relaxed', mood: 'calm and relaxing, good for unwinding after a long day' },
    { labelKey: 'moodSelector.moods.melancholic', mood: 'melancholic and emotional, introspective mood' },
    { labelKey: 'moodSelector.moods.party', mood: 'party vibes, fun and celebratory music' },
    { labelKey: 'moodSelector.moods.focus', mood: 'focus and concentration, ambient or lo-fi beats' },
    { labelKey: 'moodSelector.moods.romantic', mood: 'romantic and sensual, love songs' },
    { labelKey: 'moodSelector.moods.motivational', mood: 'motivational and inspiring, empowering music' },
    { labelKey: 'moodSelector.moods.nostalgic', mood: 'nostalgic, throwback to the past, vintage feel' },
  ]

  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setShowRecordMenu(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
      if (recognitionRef.current) recognitionRef.current.stop()
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        mediaRecorderRef.current.stop()
      }
      // Cleanup captured audio URL
      if (capturedAudioUrl) {
        URL.revokeObjectURL(capturedAudioUrl)
      }
    }
  }, [capturedAudioUrl])

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    const validTypes = ['audio/mpeg', 'audio/mp3', 'audio/wav', 'audio/webm', 'audio/ogg', 'audio/mp4', 'audio/m4a']
    if (!validTypes.includes(file.type) && !file.name.match(/\.(mp3|wav|webm|ogg|m4a|mp4)$/i)) {
      setAudioError(t('moodSelector.audio.invalidFormat'))
      return
    }

    if (file.size > 10 * 1024 * 1024) {
      setAudioError(t('moodSelector.audio.fileTooLarge'))
      return
    }

    setAudioError(null)
    setSongNotRecognized(false)
    setIsIdentifying(true)
    
    // Clean up previous captured audio
    if (capturedAudioUrl) {
      URL.revokeObjectURL(capturedAudioUrl)
      setCapturedAudioUrl(null)
    }

    try {
      const result = await audioApi.identifyAudio(file)
      if (result.identified) {
        setIdentifiedSong(result)
        setSongNotRecognized(false)
        setCapturedAudioUrl(null)
      } else {
        // Song not identified - store CLAP analysis and audio for playback
        const audioUrl = URL.createObjectURL(file)
        setCapturedAudioUrl(audioUrl)
        setSongNotRecognized(true)
        setIdentifiedSong(null)
        // Store CLAP audio analysis for Case 3
        if (result.audio_analysis) {
          setAudioAnalysis(result.audio_analysis)
        }
      }
    } catch (err) {
      setAudioError(t('moodSelector.audio.errorProcessing'))
    } finally {
      setIsIdentifying(false)
    }

    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const handleRemoveSong = () => {
    setIdentifiedSong(null)
    setAudioError(null)
  }

  // Start voice recording (speech-to-text)
  const startVoiceRecording = useCallback(() => {
    setShowRecordMenu(false)
    setRecordingMode('voice')
    setIsRecording(true)
    setAudioError(null)

    // Check for Web Speech API support
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SpeechRecognition) {
      setAudioError(t('moodSelector.recording.speechNotSupported'))
      setIsRecording(false)
      setRecordingMode(null)
      return
    }

    const recognition = new SpeechRecognition()
    recognitionRef.current = recognition
    recognition.continuous = true
    recognition.interimResults = true
    recognition.lang = navigator.language || 'en-US'

    let finalTranscript = customMood

    recognition.onresult = (event) => {
      let interimTranscript = ''
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript
        if (event.results[i].isFinal) {
          finalTranscript += (finalTranscript ? ' ' : '') + transcript
          setCustomMood(finalTranscript)
        } else {
          interimTranscript += transcript
        }
      }
      // Show interim results
      if (interimTranscript) {
        setCustomMood(finalTranscript + (finalTranscript ? ' ' : '') + interimTranscript)
      }
    }

    recognition.onerror = (event) => {
      console.error('Speech recognition error:', event.error)
      if (event.error === 'not-allowed') {
        setAudioError(t('moodSelector.recording.microphoneError'))
      }
      stopRecording()
    }

    recognition.onend = () => {
      setCustomMood(finalTranscript)
      setIsRecording(false)
      setRecordingMode(null)
    }

    recognition.start()

    // Start timer
    setRecordingTime(0)
    timerRef.current = setInterval(() => {
      setRecordingTime(prev => prev + 1)
    }, 1000)
  }, [customMood, t])

  // Start song recording (for identification)
  const startSongRecording = useCallback(async () => {
    setShowRecordMenu(false)
    setRecordingMode('song')
    setAudioError(null)

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus'
      })

      mediaRecorderRef.current = mediaRecorder
      audioChunksRef.current = []

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data)
        }
      }

      mediaRecorder.onstop = async () => {
        stream.getTracks().forEach(track => track.stop())
        
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' })
        const audioFile = new File([audioBlob], 'recording.webm', { type: 'audio/webm' })

        // Clean up previous captured audio
        if (capturedAudioUrl) {
          URL.revokeObjectURL(capturedAudioUrl)
          setCapturedAudioUrl(null)
        }

        setIsIdentifying(true)
        setSongNotRecognized(false)
        try {
          const result = await audioApi.identifyAudio(audioFile)
          if (result.identified) {
            setIdentifiedSong(result)
            setSongNotRecognized(false)
            setCapturedAudioUrl(null)
          } else {
            // Song not identified - store CLAP analysis and audio for playback
            const audioUrl = URL.createObjectURL(audioBlob)
            setCapturedAudioUrl(audioUrl)
            setSongNotRecognized(true)
            setIdentifiedSong(null)
            // Store CLAP audio analysis for Case 3
            if (result.audio_analysis) {
              setAudioAnalysis(result.audio_analysis)
            }
          }
        } catch (err) {
          setAudioError(t('moodSelector.audio.errorProcessing'))
        } finally {
          setIsIdentifying(false)
        }
      }

      mediaRecorder.start(1000)
      setIsRecording(true)
      setRecordingTime(0)

      timerRef.current = setInterval(() => {
        setRecordingTime(prev => prev + 1)
      }, 1000)

    } catch (err) {
      setAudioError(t('moodSelector.recording.microphoneError'))
      setRecordingMode(null)
    }
  }, [t])

  const stopRecording = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current)
      timerRef.current = null
    }

    if (recordingMode === 'voice' && recognitionRef.current) {
      recognitionRef.current.stop()
    } else if (recordingMode === 'song' && mediaRecorderRef.current) {
      mediaRecorderRef.current.stop()
    }

    setIsRecording(false)
    setRecordingMode(null)
  }, [recordingMode])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    // Allow submit with: text, identified song, OR audio analysis (Case 3)
    if (customMood.trim() || identifiedSong || audioAnalysis) {
      onMoodSubmit(customMood.trim(), identifiedSong || undefined, audioAnalysis || undefined)
    }
  }

  const handleQuickMood = (mood: string) => {
    onMoodSubmit(mood, identifiedSong || undefined, audioAnalysis || undefined)
  }

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const canSubmit = (customMood.trim() || identifiedSong || audioAnalysis) && !isIdentifying && !isRecording

  return (
    <div className="card p-8">
      <div className="text-center mb-6">
        <h2 className="text-xl font-semibold text-neutral-900 mb-2">
          {t('moodSelector.title')}
        </h2>
        <p className="text-neutral-500">
          {t('moodSelector.subtitle')}
        </p>
      </div>

      {/* Quick mood buttons */}
      <div className="mb-6">
        <div className="flex items-center gap-2 text-sm text-neutral-600 mb-3">
          <Zap className="w-4 h-4" />
          <span>{t('moodSelector.quickMoods')}</span>
        </div>
        <div className="flex flex-wrap gap-2">
          {MOOD_SUGGESTIONS.map((suggestion) => (
            <button
              key={suggestion.labelKey}
              onClick={() => handleQuickMood(suggestion.mood)}
              disabled={isLoading || isIdentifying || isRecording}
              className="px-4 py-2 bg-neutral-100 hover:bg-neutral-200 text-neutral-700 rounded-full text-sm font-medium transition-colors disabled:opacity-50"
            >
              {t(suggestion.labelKey)}
            </button>
          ))}
        </div>
      </div>

      {/* Divider */}
      <div className="relative my-6">
        <div className="absolute inset-0 flex items-center">
          <div className="w-full border-t border-neutral-200" />
        </div>
        <div className="relative flex justify-center text-sm">
          <span className="px-4 bg-white text-neutral-500">{t('moodSelector.orDescribe')}</span>
        </div>
      </div>

      {/* Identified song card with Play and Find Similar buttons */}
      {identifiedSong && (
        <div className="mb-4 p-4 bg-green-50 border border-green-200 rounded-lg">
          <div className="flex items-center gap-3">
            {/* Thumbnail with play overlay */}
            <div className="relative flex-shrink-0">
              {identifiedSong.cover_art_url || identifiedSong.thumbnail_url ? (
                <img
                  src={identifiedSong.cover_art_url || identifiedSong.thumbnail_url}
                  alt="Album cover"
                  className="w-14 h-14 rounded-lg object-cover shadow-sm"
                />
              ) : (
                <div className="w-14 h-14 rounded-lg bg-green-100 flex items-center justify-center">
                  <Music2 className="w-7 h-7 text-green-600" />
                </div>
              )}
              {/* Play button overlay */}
              {identifiedSong.video_id && (
                <button
                  onClick={() => playSong({
                    title: identifiedSong.title || 'Unknown',
                    artist: identifiedSong.artist || 'Unknown',
                    video_id: identifiedSong.video_id,
                    thumbnail_url: identifiedSong.cover_art_url || identifiedSong.thumbnail_url,
                    album: identifiedSong.album,
                    genre: identifiedSong.genre
                  })}
                  className="absolute inset-0 flex items-center justify-center bg-black/40 rounded-lg opacity-0 hover:opacity-100 transition-opacity"
                  title={t('songCard.preview')}
                >
                  {currentSong?.video_id === identifiedSong.video_id && isPlaying ? (
                    <Pause className="w-6 h-6 text-white" fill="white" />
                  ) : (
                    <Play className="w-6 h-6 text-white" fill="white" />
                  )}
                </button>
              )}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-neutral-900 truncate">
                {identifiedSong.title}
              </p>
              <p className="text-xs text-neutral-500 truncate">
                {identifiedSong.artist}
              </p>
              {identifiedSong.genre && (
                <p className="text-xs text-green-600 mt-0.5">{identifiedSong.genre}</p>
              )}
            </div>
            {/* Play button (explicit) */}
            {identifiedSong.video_id && (
              <button
                onClick={() => playSong({
                  title: identifiedSong.title || 'Unknown',
                  artist: identifiedSong.artist || 'Unknown',
                  video_id: identifiedSong.video_id,
                  thumbnail_url: identifiedSong.cover_art_url || identifiedSong.thumbnail_url,
                  album: identifiedSong.album,
                  genre: identifiedSong.genre
                })}
                className="p-2 bg-green-600 hover:bg-green-700 rounded-full transition-colors"
                title={t('songCard.preview')}
              >
                {currentSong?.video_id === identifiedSong.video_id && isPlaying ? (
                  <Pause className="w-4 h-4 text-white" fill="white" />
                ) : (
                  <Play className="w-4 h-4 text-white" fill="white" />
                )}
              </button>
            )}
            <button
              onClick={handleRemoveSong}
              className="p-1.5 hover:bg-green-100 rounded-full transition-colors"
              title={t('common.remove')}
            >
              <X className="w-4 h-4 text-green-600" />
            </button>
          </div>
          
          {/* Find Similar button - prominent action */}
          <button
            onClick={() => onMoodSubmit('', identifiedSong)}
            disabled={isLoading}
            className="mt-3 w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-green-600 hover:bg-green-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Sparkles className="w-4 h-4" />
            )}
            {t('moodSelector.findSimilar')}
          </button>
          
          <p className="mt-2 text-xs text-center text-green-700">
            {t('moodSelector.orAddDescription')}
          </p>
        </div>
      )}

      {/* Song not recognized - prompt to describe vibe with audio playback */}
      {songNotRecognized && !identifiedSong && (
        <div className="mb-4 p-4 bg-amber-50 border border-amber-200 rounded-lg">
          <div className="flex items-start gap-3">
            <div className="w-10 h-10 rounded-full bg-amber-100 flex items-center justify-center flex-shrink-0">
              <Music2 className="w-5 h-5 text-amber-600" />
            </div>
            <div className="flex-1">
              <p className="text-sm font-medium text-amber-800">
                {t('moodSelector.audio.songNotRecognized')}
              </p>
              
              {/* Show CLAP analysis results if available */}
              {audioAnalysis && (
                <div className="mt-2 space-y-1">
                  {audioAnalysis.mood_tags.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      <span className="text-xs text-amber-700 font-medium">Mood:</span>
                      {audioAnalysis.mood_tags.slice(0, 3).map((tag) => (
                        <span key={tag} className="px-2 py-0.5 bg-amber-100 text-amber-800 text-xs rounded-full">
                          {tag}
                        </span>
                      ))}
                    </div>
                  )}
                  {audioAnalysis.genre_tags.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      <span className="text-xs text-amber-700 font-medium">Genre:</span>
                      {audioAnalysis.genre_tags.slice(0, 3).map((tag) => (
                        <span key={tag} className="px-2 py-0.5 bg-amber-100 text-amber-800 text-xs rounded-full">
                          {tag}
                        </span>
                      ))}
                    </div>
                  )}
                  <p className="text-xs text-amber-600">
                    {audioAnalysis.tempo_description} tempo • {audioAnalysis.energy_level} energy
                  </p>
                </div>
              )}
              
              {!audioAnalysis && (
                <p className="text-xs text-amber-600 mt-1">
                  {t('moodSelector.audio.describeVibeInstead')}
                </p>
              )}
              
              {/* Audio playback for captured audio */}
              {capturedAudioUrl && (
                <div className="mt-3 flex items-center gap-2">
                  <button
                    onClick={() => {
                      if (capturedAudioRef.current) {
                        if (isPlayingCaptured) {
                          capturedAudioRef.current.pause()
                          setIsPlayingCaptured(false)
                        } else {
                          capturedAudioRef.current.play()
                          setIsPlayingCaptured(true)
                        }
                      }
                    }}
                    className="flex items-center gap-2 px-3 py-1.5 bg-amber-100 hover:bg-amber-200 rounded-full text-xs font-medium text-amber-800 transition-colors"
                  >
                    {isPlayingCaptured ? (
                      <>
                        <Pause className="w-3 h-3" />
                        {t('moodSelector.audio.pauseRecording')}
                      </>
                    ) : (
                      <>
                        <Play className="w-3 h-3" />
                        {t('moodSelector.audio.playRecording')}
                      </>
                    )}
                  </button>
                  <audio
                    ref={capturedAudioRef}
                    src={capturedAudioUrl}
                    onEnded={() => setIsPlayingCaptured(false)}
                    className="hidden"
                  />
                </div>
              )}
              
              {/* Find Similar button when we have CLAP analysis */}
              {audioAnalysis && (
                <button
                  onClick={() => onMoodSubmit('', undefined, audioAnalysis)}
                  disabled={isLoading}
                  className="mt-3 w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-amber-600 hover:bg-amber-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isLoading ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Sparkles className="w-4 h-4" />
                  )}
                  {t('moodSelector.findSimilarByVibe')}
                </button>
              )}
            </div>
            <button
              onClick={() => {
                setSongNotRecognized(false)
                setAudioAnalysis(null)
                if (capturedAudioUrl) {
                  URL.revokeObjectURL(capturedAudioUrl)
                  setCapturedAudioUrl(null)
                }
                setIsPlayingCaptured(false)
              }}
              className="p-1 hover:bg-amber-100 rounded-full transition-colors"
            >
              <X className="w-4 h-4 text-amber-600" />
            </button>
          </div>
        </div>
      )}

      {/* Recording indicator */}
      {isRecording && (
        <div className="mb-3 flex items-center gap-3">
          <div className="flex items-center gap-2 px-3 py-2 bg-red-50 border border-red-200 rounded-full">
            <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
            <span className="text-sm font-medium text-red-700">
              {recordingMode === 'voice' ? t('moodSelector.recording.listening') : t('moodSelector.recording.identifyingSong')}
            </span>
            <span className="text-sm font-mono text-red-600">{formatTime(recordingTime)}</span>
          </div>
          <button
            onClick={stopRecording}
            className="p-2 bg-red-100 hover:bg-red-200 rounded-full transition-colors"
            title={t('moodSelector.recording.stop')}
          >
            <Square className="w-4 h-4 text-red-600" fill="currentColor" />
          </button>
        </div>
      )}

      {/* Error message */}
      {audioError && (
        <div className="mb-3 text-sm text-red-600 flex items-center gap-2">
          <span>{audioError}</span>
          <button 
            onClick={() => setAudioError(null)}
            className="text-red-400 hover:text-red-600"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Chat-style input */}
      <form onSubmit={handleSubmit}>
        <div className="relative flex items-center bg-white border border-neutral-300 rounded-xl focus-within:ring-2 focus-within:ring-primary-500 focus-within:border-transparent transition-all">
          {/* File upload button */}
          <input
            ref={fileInputRef}
            type="file"
            accept="audio/*,.mp3,.wav,.webm,.ogg,.m4a"
            onChange={handleFileChange}
            className="hidden"
            id="audio-upload"
          />
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={isIdentifying || isLoading || isRecording}
            className="flex-shrink-0 p-3 text-neutral-400 hover:text-neutral-600 hover:bg-neutral-100 rounded-l-xl transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            title={t('moodSelector.audio.attachAudio')}
          >
            {isIdentifying ? (
              <Loader2 className="w-5 h-5 animate-spin text-primary-600" />
            ) : (
              <Paperclip className="w-5 h-5" />
            )}
          </button>

          {/* Microphone button with menu */}
          <div className="relative flex-shrink-0" ref={menuRef}>
            <button
              type="button"
              onClick={() => isRecording ? stopRecording() : setShowRecordMenu(!showRecordMenu)}
              disabled={isIdentifying || isLoading}
              className={`p-3 transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${
                isRecording 
                  ? 'text-red-500 hover:text-red-600 bg-red-50' 
                  : 'text-neutral-400 hover:text-neutral-600 hover:bg-neutral-100'
              }`}
              title={isRecording ? t('moodSelector.recording.stop') : t('moodSelector.recording.start')}
            >
              {isRecording ? (
                <Square className="w-5 h-5" fill="currentColor" />
              ) : (
                <Mic className="w-5 h-5" />
              )}
            </button>

            {/* Recording mode menu */}
            {showRecordMenu && !isRecording && (
              <div className="absolute bottom-full left-0 mb-2 bg-white border border-neutral-200 rounded-lg shadow-lg overflow-hidden z-10 min-w-[200px]">
                <button
                  type="button"
                  onClick={startVoiceRecording}
                  className="w-full flex items-center gap-3 px-4 py-3 hover:bg-neutral-50 transition-colors text-left"
                >
                  <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                    <MessageSquare className="w-4 h-4 text-blue-600" />
                  </div>
                  <div>
                    <div className="text-sm font-medium text-neutral-900">{t('moodSelector.recording.voiceInput')}</div>
                    <div className="text-xs text-neutral-500">{t('moodSelector.recording.voiceInputDesc')}</div>
                  </div>
                </button>
                <div className="border-t border-neutral-100" />
                <button
                  type="button"
                  onClick={startSongRecording}
                  className="w-full flex items-center gap-3 px-4 py-3 hover:bg-neutral-50 transition-colors text-left"
                >
                  <div className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center">
                    <Music2 className="w-4 h-4 text-green-600" />
                  </div>
                  <div>
                    <div className="text-sm font-medium text-neutral-900">{t('moodSelector.recording.identifySong')}</div>
                    <div className="text-xs text-neutral-500">{t('moodSelector.recording.identifySongDesc')}</div>
                  </div>
                </button>
              </div>
            )}
          </div>

          {/* Text input */}
          <div className="flex-1 flex items-center">
            <Sparkles className="w-5 h-5 text-neutral-300 mr-2 flex-shrink-0" />
            <input
              type="text"
              value={customMood}
              onChange={(e) => setCustomMood(e.target.value)}
              placeholder={identifiedSong 
                ? t('moodSelector.placeholderWithSong') 
                : t('moodSelector.placeholder')
              }
              className="flex-1 py-3 pr-3 bg-transparent text-neutral-900 placeholder-neutral-400 focus:outline-none"
              disabled={isLoading || isIdentifying || isRecording}
            />
          </div>

          {/* Submit button */}
          <button
            type="submit"
            disabled={!canSubmit || isLoading}
            className="flex-shrink-0 m-1.5 p-2.5 bg-primary-600 hover:bg-primary-700 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-primary-600"
          >
            {isLoading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
          </button>
        </div>

        {/* Helper text */}
        <p className="text-xs text-neutral-400 mt-2 text-center">
          {isRecording 
            ? (recordingMode === 'voice' 
                ? t('moodSelector.recording.speakNow') 
                : t('moodSelector.recording.playMusic'))
            : identifiedSong 
              ? t('moodSelector.audio.addMoodForBetter')
              : t('moodSelector.audio.attachHint')
          }
        </p>
      </form>

      {/* Examples */}
      <div className="mt-6 text-sm text-neutral-500">
        <p className="font-medium mb-2">{t('moodSelector.examples.title')}</p>
        <ul className="space-y-1 text-neutral-400">
          <li>"{t('moodSelector.examples.ex1')}"</li>
          <li>"{t('moodSelector.examples.ex2')}"</li>
          <li>"{t('moodSelector.examples.ex3')}"</li>
        </ul>
      </div>
    </div>
  )
}

// Add TypeScript declarations for Web Speech API
declare global {
  interface Window {
    SpeechRecognition: typeof SpeechRecognition
    webkitSpeechRecognition: typeof SpeechRecognition
  }
}
