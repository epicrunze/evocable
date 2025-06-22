import { useState, useRef, useEffect } from 'react'
import { apiClient, ChunkInfo } from '../lib/api'
import { 
  PlayIcon, 
  PauseIcon, 
  SpeakerWaveIcon,
  SpeakerXMarkIcon,
  ArrowUturnLeftIcon
} from '@heroicons/react/24/solid'

interface AudioPlayerProps {
  bookId: string
  chunks: ChunkInfo[]
  title: string
}

export default function AudioPlayer({ bookId, chunks, title }: AudioPlayerProps) {
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentChunk, setCurrentChunk] = useState(0)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [volume, setVolume] = useState(1)
  const [isMuted, setIsMuted] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  const audioRef = useRef<HTMLAudioElement>(null)
  const progressRef = useRef<HTMLInputElement>(null)

  // Calculate total duration and current position
  const totalDuration = chunks.reduce((sum, chunk) => sum + chunk.duration_s, 0)
  const currentPosition = chunks
    .slice(0, currentChunk)
    .reduce((sum, chunk) => sum + chunk.duration_s, 0) + currentTime

  useEffect(() => {
    const audio = audioRef.current
    if (!audio) return

    const handleTimeUpdate = () => {
      setCurrentTime(audio.currentTime)
    }

    const handleLoadedMetadata = () => {
      setDuration(audio.duration)
      setLoading(false)
    }

    const handleEnded = () => {
      // Auto-advance to next chunk
      if (currentChunk < chunks.length - 1) {
        playChunk(currentChunk + 1)
      } else {
        setIsPlaying(false)
        setCurrentTime(0)
        setCurrentChunk(0)
      }
    }

    const handleCanPlay = () => {
      setLoading(false)
      if (isPlaying) {
        audio.play().catch(console.error)
      }
    }

    const handleWaiting = () => {
      setLoading(true)
    }

    const handleError = () => {
      setError('Failed to load audio chunk')
      setLoading(false)
    }

    audio.addEventListener('timeupdate', handleTimeUpdate)
    audio.addEventListener('loadedmetadata', handleLoadedMetadata)
    audio.addEventListener('ended', handleEnded)
    audio.addEventListener('canplay', handleCanPlay)
    audio.addEventListener('waiting', handleWaiting)
    audio.addEventListener('error', handleError)

    return () => {
      audio.removeEventListener('timeupdate', handleTimeUpdate)
      audio.removeEventListener('loadedmetadata', handleLoadedMetadata)
      audio.removeEventListener('ended', handleEnded)
      audio.removeEventListener('canplay', handleCanPlay)
      audio.removeEventListener('waiting', handleWaiting)
      audio.removeEventListener('error', handleError)
    }
  }, [currentChunk, chunks.length, isPlaying])

  const playChunk = async (chunkIndex: number) => {
    if (chunkIndex < 0 || chunkIndex >= chunks.length) return
    
    setLoading(true)
    setError(null)
    setCurrentChunk(chunkIndex)

    const audio = audioRef.current
    if (!audio) return

    try {
      const chunkUrl = await apiClient.getChunkUrl(bookId, chunks[chunkIndex].seq)
      audio.src = chunkUrl
      audio.load()
    } catch (err) {
      setError('Failed to load audio chunk')
      setLoading(false)
    }
  }

  const togglePlayPause = async () => {
    const audio = audioRef.current
    if (!audio) return

    if (isPlaying) {
      audio.pause()
      setIsPlaying(false)
    } else {
      if (!audio.src) {
        await playChunk(currentChunk)
      }
      try {
        await audio.play()
        setIsPlaying(true)
      } catch (err) {
        setError('Failed to play audio')
      }
    }
  }

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const seekTime = parseFloat(e.target.value)
    const audio = audioRef.current
    if (!audio) return

    // Find which chunk this time falls into
    let accumulatedTime = 0
    let targetChunk = 0
    let timeInChunk = seekTime

    for (let i = 0; i < chunks.length; i++) {
      if (accumulatedTime + chunks[i].duration_s > seekTime) {
        targetChunk = i
        timeInChunk = seekTime - accumulatedTime
        break
      }
      accumulatedTime += chunks[i].duration_s
    }

    if (targetChunk !== currentChunk) {
      // Need to switch chunks
      playChunk(targetChunk).then(() => {
        if (audio) {
          audio.currentTime = timeInChunk
        }
      })
    } else {
      // Same chunk, just seek
      audio.currentTime = timeInChunk
    }
  }

  const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newVolume = parseFloat(e.target.value)
    setVolume(newVolume)
    
    const audio = audioRef.current
    if (audio) {
      audio.volume = newVolume
    }
    
    if (newVolume === 0) {
      setIsMuted(true)
    } else if (isMuted) {
      setIsMuted(false)
    }
  }

  const toggleMute = () => {
    const audio = audioRef.current
    if (!audio) return

    if (isMuted) {
      audio.volume = volume
      setIsMuted(false)
    } else {
      audio.volume = 0
      setIsMuted(true)
    }
  }

  const formatTime = (seconds: number) => {
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    const secs = Math.floor(seconds % 60)

    if (hours > 0) {
      return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
    }
    return `${minutes}:${secs.toString().padStart(2, '0')}`
  }

  const skipBackward = () => {
    const audio = audioRef.current
    if (!audio) return

    const newTime = Math.max(0, currentTime - 15)
    audio.currentTime = newTime
  }

  if (chunks.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6">
        <p className="text-gray-500 text-center">No audio chunks available</p>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <audio
        ref={audioRef}
        preload="metadata"
        className="hidden"
      />

      {/* Track Info */}
      <div className="mb-6">
        <h3 className="text-lg font-medium text-gray-900 truncate">{title}</h3>
        <p className="text-sm text-gray-500">
          Chapter {currentChunk + 1} of {chunks.length} • {formatTime(totalDuration)} total
        </p>
      </div>

      {/* Progress Bar */}
      <div className="mb-6">
        <input
          ref={progressRef}
          type="range"
          min="0"
          max={totalDuration}
          value={currentPosition}
          onChange={handleSeek}
          className="audio-progress w-full"
          disabled={loading}
        />
        <div className="flex justify-between text-xs text-gray-500 mt-1">
          <span>{formatTime(currentPosition)}</span>
          <span>{formatTime(totalDuration)}</span>
        </div>
      </div>

      {/* Controls */}
      <div className="flex items-center justify-center space-x-4 mb-4">
        <button
          onClick={skipBackward}
          className="p-2 rounded-full hover:bg-gray-100 transition-colors"
          disabled={loading}
        >
          <ArrowUturnLeftIcon className="h-5 w-5 text-gray-600" />
        </button>

        <button
          onClick={togglePlayPause}
          disabled={loading}
          className="bg-primary-600 hover:bg-primary-700 text-white rounded-full p-4 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? (
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-white"></div>
          ) : isPlaying ? (
            <PauseIcon className="h-6 w-6" />
          ) : (
            <PlayIcon className="h-6 w-6 ml-0.5" />
          )}
        </button>
      </div>

      {/* Volume Control */}
      <div className="flex items-center justify-center space-x-3">
        <button
          onClick={toggleMute}
          className="p-1 rounded hover:bg-gray-100 transition-colors"
        >
          {isMuted || volume === 0 ? (
            <SpeakerXMarkIcon className="h-5 w-5 text-gray-600" />
          ) : (
            <SpeakerWaveIcon className="h-5 w-5 text-gray-600" />
          )}
        </button>
        
        <input
          type="range"
          min="0"
          max="1"
          step="0.05"
          value={isMuted ? 0 : volume}
          onChange={handleVolumeChange}
          className="w-24 h-1 bg-gray-200 rounded-lg appearance-none cursor-pointer"
        />
      </div>

      {/* Error Display */}
      {error && (
        <div className="mt-4 p-3 bg-red-50 rounded-md">
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {/* Current Chunk Info */}
      <div className="mt-4 text-xs text-gray-500 text-center">
        Playing chunk {chunks[currentChunk]?.seq} • Duration: {formatTime(chunks[currentChunk]?.duration_s || 0)}
      </div>
    </div>
  )
} 