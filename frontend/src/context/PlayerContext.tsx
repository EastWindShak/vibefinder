import { createContext, useContext, useState, ReactNode, useCallback } from 'react'
import { Song } from '../services/api'

interface PlayerContextType {
  currentSong: Song | null
  isPlaying: boolean
  isExpanded: boolean
  playSong: (song: Song) => void
  pauseSong: () => void
  resumeSong: () => void
  stopSong: () => void
  toggleExpanded: () => void
}

const PlayerContext = createContext<PlayerContextType | undefined>(undefined)

export function PlayerProvider({ children }: { children: ReactNode }) {
  const [currentSong, setCurrentSong] = useState<Song | null>(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [isExpanded, setIsExpanded] = useState(false)

  const playSong = useCallback((song: Song) => {
    setCurrentSong(song)
    setIsPlaying(true)
    // Keep collapsed by default - user can expand manually
  }, [])

  const pauseSong = useCallback(() => {
    setIsPlaying(false)
  }, [])

  const resumeSong = useCallback(() => {
    setIsPlaying(true)
  }, [])

  const stopSong = useCallback(() => {
    setCurrentSong(null)
    setIsPlaying(false)
    setIsExpanded(false)
  }, [])

  const toggleExpanded = useCallback(() => {
    setIsExpanded(prev => !prev)
  }, [])

  return (
    <PlayerContext.Provider value={{
      currentSong,
      isPlaying,
      isExpanded,
      playSong,
      pauseSong,
      resumeSong,
      stopSong,
      toggleExpanded
    }}>
      {children}
    </PlayerContext.Provider>
  )
}

export function usePlayer() {
  const context = useContext(PlayerContext)
  if (context === undefined) {
    throw new Error('usePlayer must be used within a PlayerProvider')
  }
  return context
}
