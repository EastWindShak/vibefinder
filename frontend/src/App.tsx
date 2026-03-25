import { Routes, Route } from 'react-router-dom'
import Navbar from './components/Navbar'
import MiniPlayer from './components/MiniPlayer'
import Home from './pages/Home'
import Login from './pages/Login'
import Profile from './pages/Profile'
import { usePlayer } from './context/PlayerContext'

function App() {
  const { currentSong } = usePlayer()

  return (
    <div className="min-h-screen bg-neutral-50">
      <Navbar />
      <main className={`container mx-auto px-4 py-8 max-w-6xl ${currentSong ? 'pb-28' : ''}`}>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/login" element={<Login />} />
          <Route path="/profile" element={<Profile />} />
        </Routes>
      </main>
      <MiniPlayer />
    </div>
  )
}

export default App
