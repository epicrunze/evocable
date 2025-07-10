import { useState, useEffect, useRef, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { AudioState, AudioError, Bookmark, PlaybackControls } from '@/types/audio';
import { BookWithChunks } from '@/types/book';
import { audioApi } from '@/lib/api/audio';
import { booksApi } from '@/lib/api/books';

interface UseAudioOptions {
  bookId?: string;
  autoPlay?: boolean;
  onPlay?: () => void;
  onPause?: () => void;
  onTimeUpdate?: (time: number) => void;
  onChunkChange?: (chunk: number) => void;
  onEnd?: () => void;
  onError?: (error: AudioError) => void;
}

interface UseAudioReturn {
  audioState: AudioState | null;
  controls: PlaybackControls;
  bookmarks: Bookmark[];
  isLoading: boolean;
  error: AudioError | null;
  book: BookWithChunks | null;
  addBookmark: (title: string) => Promise<void>;
  removeBookmark: (id: string) => Promise<void>;
  seekToBookmark: (id: string) => Promise<void>;
  initialize: (bookId: string) => Promise<void>;
  cleanup: () => void;
}

export function useAudio(options: UseAudioOptions = {}): UseAudioReturn {
  const {
    bookId: initialBookId,
    autoPlay = false,
    onPlay,
    onPause,
    onTimeUpdate,
    onChunkChange,
    onEnd,
    onError,
  } = options;

  // State
  const [bookId, setBookId] = useState<string | null>(initialBookId || null);
  const [audioState, setAudioState] = useState<AudioState | null>(null);
  const [currentError, setCurrentError] = useState<AudioError | null>(null);
  const [isInitialized, setIsInitialized] = useState(false);

  // Refs
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const currentChunkRef = useRef<number>(0);
  const isSeekingRef = useRef(false);

  // Fetch book data with chunks
  const { data: book, isLoading: bookLoading, error: bookError } = useQuery({
    queryKey: ['book', bookId],
    queryFn: async () => {
      if (!bookId) return null;
      const response = await booksApi.getBookWithChunks(bookId);
      return response.data;
    },
    enabled: !!bookId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  // Fetch bookmarks
  const { data: bookmarks = [], refetch: refetchBookmarks } = useQuery({
    queryKey: ['bookmarks', bookId],
    queryFn: async () => {
      if (!bookId) return [];
      const response = await audioApi.getBookmarks(bookId);
      return response.data;
    },
    enabled: !!bookId,
    staleTime: 30 * 1000, // 30 seconds
  });

  // Initialize audio element
  const initializeAudio = useCallback(() => {
    if (!book || !bookId) return;

    const audio = new Audio();
    audio.preload = 'metadata';
    audio.crossOrigin = 'anonymous';

    // Set up event listeners
    audio.addEventListener('loadstart', () => {
      setAudioState(prev => prev ? { ...prev, isLoading: true } : null);
    });

    audio.addEventListener('loadedmetadata', () => {
      setAudioState(prev => prev ? { 
        ...prev, 
        duration: audio.duration,
        isLoading: false 
      } : null);
    });

    audio.addEventListener('timeupdate', () => {
      if (isSeekingRef.current) return;
      
      setAudioState(prev => prev ? {
        ...prev,
        currentTime: audio.currentTime,
        bufferedRanges: audio.buffered,
      } : null);
      
      onTimeUpdate?.(audio.currentTime);
    });

    audio.addEventListener('play', () => {
      setAudioState(prev => prev ? { ...prev, isPlaying: true } : null);
      onPlay?.();
    });

    audio.addEventListener('pause', () => {
      setAudioState(prev => prev ? { ...prev, isPlaying: false } : null);
      onPause?.();
    });

    audio.addEventListener('ended', () => {
      handleChunkEnd();
    });

    audio.addEventListener('error', (e) => {
      const error: AudioError = {
        type: 'playback',
        message: 'Audio playback error',
        recoverable: true,
        chunk: currentChunkRef.current,
      };
      setCurrentError(error);
      onError?.(error);
    });

    audioRef.current = audio;
    setIsInitialized(true);
  }, [book, bookId, onPlay, onPause, onTimeUpdate, onError]);

  // Load audio chunk
  const loadChunk = useCallback(async (chunkIndex: number) => {
    if (!book || !audioRef.current || !bookId) return;

    try {
      const chunk = book.chunks[chunkIndex];
      if (!chunk) return;

      currentChunkRef.current = chunkIndex;
      const chunkUrl = audioApi.getAuthenticatedChunkUrl(bookId, chunkIndex);
      
      audioRef.current.src = chunkUrl;
      audioRef.current.load();

      setAudioState(prev => prev ? {
        ...prev,
        currentChunk: chunkIndex,
        duration: chunk.duration_s,
        isLoading: true,
      } : null);

      onChunkChange?.(chunkIndex);
    } catch (error) {
      const audioError: AudioError = {
        type: 'network',
        message: 'Failed to load audio chunk',
        recoverable: true,
        chunk: chunkIndex,
      };
      setCurrentError(audioError);
      onError?.(audioError);
    }
  }, [book, bookId, onChunkChange, onError]);

  // Handle chunk end
  const handleChunkEnd = useCallback(() => {
    if (!book) return;

    const nextChunkIndex = currentChunkRef.current + 1;
    if (nextChunkIndex < book.chunks.length) {
      loadChunk(nextChunkIndex);
    } else {
      setAudioState(prev => prev ? { ...prev, isPlaying: false } : null);
      onEnd?.();
    }
  }, [book, loadChunk, onEnd]);

  // Playback controls
  const controls: PlaybackControls = {
    play: async () => {
      if (!audioRef.current) return;
      
      try {
        await audioRef.current.play();
      } catch (error) {
        const audioError: AudioError = {
          type: 'playback',
          message: 'Failed to start playback',
          recoverable: true,
        };
        setCurrentError(audioError);
        onError?.(audioError);
      }
    },

    pause: async () => {
      if (!audioRef.current) return;
      audioRef.current.pause();
    },

    seek: async (time: number) => {
      if (!audioRef.current || !book) return;

      isSeekingRef.current = true;
      
      try {
        // Calculate which chunk contains the target time
        let targetChunk = 0;
        let cumulativeTime = 0;
        
        for (let i = 0; i < book.chunks.length; i++) {
          if (cumulativeTime + book.chunks[i].duration_s > time) {
            targetChunk = i;
            break;
          }
          cumulativeTime += book.chunks[i].duration_s;
        }

        const chunkStartTime = cumulativeTime;
        const localTime = time - chunkStartTime;

        // Load chunk if different from current
        if (targetChunk !== currentChunkRef.current) {
          await loadChunk(targetChunk);
        }

        // Seek to local time in chunk
        audioRef.current.currentTime = localTime;
        
        setAudioState(prev => prev ? {
          ...prev,
          currentTime: localTime,
          currentChunk: targetChunk,
        } : null);

        isSeekingRef.current = false;
      } catch (error) {
        isSeekingRef.current = false;
        const audioError: AudioError = {
          type: 'playback',
          message: 'Failed to seek to position',
          recoverable: true,
        };
        setCurrentError(audioError);
        onError?.(audioError);
      }
    },

    setVolume: async (volume: number) => {
      if (!audioRef.current) return;
      
      audioRef.current.volume = Math.max(0, Math.min(1, volume));
      setAudioState(prev => prev ? { ...prev, volume } : null);
    },

    setPlaybackRate: async (rate: number) => {
      if (!audioRef.current) return;
      
      audioRef.current.playbackRate = Math.max(0.25, Math.min(4, rate));
      setAudioState(prev => prev ? { ...prev, playbackRate: rate } : null);
    },

    skipForward: async (seconds: number) => {
      if (!audioRef.current || !audioState) return;
      
      const newTime = audioState.currentTime + seconds;
      await controls.seek(newTime);
    },

    skipBackward: async (seconds: number) => {
      if (!audioRef.current || !audioState) return;
      
      const newTime = Math.max(0, audioState.currentTime - seconds);
      await controls.seek(newTime);
    },
  };

  // Initialize audio when book is loaded
  useEffect(() => {
    if (book && !isInitialized) {
      initializeAudio();
    }
  }, [book, isInitialized, initializeAudio]);

  // Load first chunk when audio is initialized
  useEffect(() => {
    if (isInitialized && book && audioRef.current) {
      loadChunk(0);
    }
  }, [isInitialized, book, loadChunk]);

  // Auto-play if enabled
  useEffect(() => {
    if (autoPlay && audioState && !audioState.isPlaying && !audioState.isLoading) {
      controls.play();
    }
  }, [autoPlay, audioState, controls]);

  // Initialize audio state
  useEffect(() => {
    if (bookId && !audioState) {
      setAudioState({
        bookId,
        currentChunk: 0,
        currentTime: 0,
        duration: 0,
        isPlaying: false,
        isLoading: false,
        volume: 1,
        playbackRate: 1,
        bufferedRanges: null,
        error: currentError || undefined,
      });
    }
  }, [bookId, audioState, currentError]);

  // Bookmark functions
  const addBookmark = useCallback(async (title: string) => {
    if (!bookId || !audioState) return;

    try {
      await audioApi.createBookmark({
        bookId,
        title,
        time: audioState.currentTime,
        chunk: audioState.currentChunk,
      });
      refetchBookmarks();
    } catch (error) {
      console.error('Failed to add bookmark:', error);
    }
  }, [bookId, audioState, refetchBookmarks]);

  const removeBookmark = useCallback(async (id: string) => {
    try {
      await audioApi.deleteBookmark(id);
      refetchBookmarks();
    } catch (error) {
      console.error('Failed to remove bookmark:', error);
    }
  }, [refetchBookmarks]);

  const seekToBookmark = useCallback(async (id: string) => {
    const bookmark = bookmarks.find(b => b.id === id);
    if (!bookmark) return;

    await controls.seek(bookmark.time);
  }, [bookmarks, controls]);

  // Initialize function
  const initialize = useCallback(async (newBookId: string) => {
    // Cleanup existing audio
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.removeEventListener('loadstart', () => {});
      audioRef.current = null;
    }

    setBookId(newBookId);
    setAudioState(null);
    setCurrentError(null);
    setIsInitialized(false);
    currentChunkRef.current = 0;
  }, []);

  // Cleanup function
  const cleanup = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.removeEventListener('loadstart', () => {});
      audioRef.current = null;
    }
    setAudioState(null);
    setCurrentError(null);
    setIsInitialized(false);
  }, []);

  return {
    audioState,
    controls,
    bookmarks,
    isLoading: bookLoading,
    error: bookError ? { 
      type: 'network', 
      message: 'Failed to load book', 
      recoverable: true 
    } : currentError,
    book: book || null,
    addBookmark,
    removeBookmark,
    seekToBookmark,
    initialize,
    cleanup,
  };
} 