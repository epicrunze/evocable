import { useState, useEffect } from 'react'
import { useRouter } from 'next/router'
import { useAuth } from '../_app'
import { apiClient, BookStatusResponse, ChunkListResponse } from '../../lib/api'
import Layout from '../../components/Layout'
import AudioPlayer from '../../components/AudioPlayer'
import Head from 'next/head'
import Link from 'next/link'
import {
  ArrowLeftIcon,
  ClockIcon,
  ExclamationTriangleIcon,
  CheckCircleIcon
} from '@heroicons/react/24/outline'

export default function BookDetailPage() {
  const router = useRouter()
  const { id } = router.query
  const { apiKey } = useAuth()
  const [bookStatus, setBookStatus] = useState<BookStatusResponse | null>(null)
  const [chunks, setChunks] = useState<ChunkListResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [polling, setPolling] = useState(false)

  useEffect(() => {
    if (id && apiKey) {
      apiClient.setApiKey(apiKey)
      loadBookData()
    }
  }, [id, apiKey])

  // Polling for status updates during processing
  useEffect(() => {
    if (!bookStatus || bookStatus.status === 'completed' || bookStatus.status === 'failed') {
      setPolling(false)
      return
    }

    setPolling(true)
    const interval = setInterval(() => {
      loadBookStatus()
    }, 3000) // Poll every 3 seconds

    return () => clearInterval(interval)
  }, [bookStatus?.status])

  const loadBookData = async () => {
    if (!id || typeof id !== 'string') return

    try {
      setLoading(true)
      setError(null)
      
      // Load book status first
      const statusResponse = await apiClient.getBookStatus(id)
      setBookStatus(statusResponse)
      
      // If completed, also load chunks
      if (statusResponse.status === 'completed') {
        const chunksResponse = await apiClient.getBookChunks(id)
        setChunks(chunksResponse)
      }
    } catch (err: any) {
      if (err.response?.status === 404) {
        setError('Book not found')
      } else {
        setError('Failed to load book data')
      }
    } finally {
      setLoading(false)
    }
  }

  const loadBookStatus = async () => {
    if (!id || typeof id !== 'string') return

    try {
      const statusResponse = await apiClient.getBookStatus(id)
      setBookStatus(statusResponse)
      
      // If just completed, load chunks
      if (statusResponse.status === 'completed' && !chunks) {
        const chunksResponse = await apiClient.getBookChunks(id)
        setChunks(chunksResponse)
      }
    } catch (err) {
      console.error('Failed to update book status:', err)
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'text-green-700 bg-green-100'
      case 'failed':
        return 'text-red-700 bg-red-100'
      case 'processing':
      case 'extracting':
      case 'segmenting':
      case 'generating_audio':
      case 'transcoding':
        return 'text-blue-700 bg-blue-100'
      default:
        return 'text-yellow-700 bg-yellow-100'
    }
  }

  const getStatusText = (status: string) => {
    switch (status) {
      case 'pending':
        return 'Pending'
      case 'processing':
        return 'Processing'
      case 'extracting':
        return 'Extracting Text'
      case 'segmenting':
        return 'Segmenting Text'
      case 'generating_audio':
        return 'Generating Audio'
      case 'transcoding':
        return 'Transcoding Audio'
      case 'completed':
        return 'Ready to Play'
      case 'failed':
        return 'Processing Failed'
      default:
        return status
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const formatDuration = (seconds: number) => {
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    
    if (hours > 0) {
      return `${hours}h ${minutes}m`
    }
    return `${minutes}m`
  }

  if (loading) {
    return (
      <Layout>
        <div className="flex items-center justify-center min-h-96">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
        </div>
      </Layout>
    )
  }

  if (error) {
    return (
      <Layout>
        <div className="p-6">
          <div className="max-w-md mx-auto">
            <div className="rounded-md bg-red-50 p-4">
              <div className="flex">
                <ExclamationTriangleIcon className="h-5 w-5 text-red-400" />
                <div className="ml-3">
                  <h3 className="text-sm font-medium text-red-800">Error</h3>
                  <div className="mt-2 text-sm text-red-700">{error}</div>
                  <div className="mt-4">
                    <Link href="/" className="btn-primary">
                      Back to Library
                    </Link>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </Layout>
    )
  }

  if (!bookStatus) {
    return (
      <Layout>
        <div className="p-6">
          <p className="text-center text-gray-500">Book not found</p>
        </div>
      </Layout>
    )
  }

  return (
    <>
      <Head>
        <title>{bookStatus.title} - Audiobook Player</title>
      </Head>
      
      <Layout>
        <div className="p-6 max-w-4xl mx-auto">
          {/* Header */}
          <div className="flex items-center mb-6">
            <Link
              href="/"
              className="mr-4 p-2 rounded-md hover:bg-gray-100 transition-colors"
            >
              <ArrowLeftIcon className="h-5 w-5 text-gray-600" />
            </Link>
            <div className="flex-1">
              <h1 className="text-2xl font-bold text-gray-900">{bookStatus.title}</h1>
              <p className="text-sm text-gray-500 mt-1">
                Uploaded {formatDate(bookStatus.created_at)}
              </p>
            </div>
          </div>

          {/* Status Card */}
          <div className="card mb-6">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center space-x-3 mb-4">
                  <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(bookStatus.status)}`}>
                    {bookStatus.status === 'completed' ? (
                      <CheckCircleIcon className="h-4 w-4 mr-1" />
                    ) : bookStatus.status === 'failed' ? (
                      <ExclamationTriangleIcon className="h-4 w-4 mr-1" />
                    ) : (
                      <ClockIcon className="h-4 w-4 mr-1" />
                    )}
                    {getStatusText(bookStatus.status)}
                  </span>
                  {polling && (
                    <div className="flex items-center text-sm text-gray-500">
                      <div className="animate-spin rounded-full h-3 w-3 border-b border-gray-400 mr-2"></div>
                      Live updates
                    </div>
                  )}
                </div>

                {/* Progress bar for processing states */}
                {bookStatus.status !== 'completed' && bookStatus.status !== 'failed' && (
                  <div className="mb-4">
                    <div className="flex items-center justify-between text-sm mb-2">
                      <span className="text-gray-600">Processing Progress</span>
                      <span className="text-gray-900 font-medium">{Math.round(bookStatus.percent_complete)}%</span>
                    </div>
                    <div className="bg-gray-200 rounded-full h-2">
                      <div
                        className="bg-primary-600 h-2 rounded-full transition-all duration-300"
                        style={{ width: `${bookStatus.percent_complete}%` }}
                      />
                    </div>
                  </div>
                )}

                {/* Book metadata */}
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-gray-500">Total Chunks:</span>
                    <span className="ml-2 font-medium">{bookStatus.total_chunks || 'Processing...'}</span>
                  </div>
                  {chunks && (
                    <div>
                      <span className="text-gray-500">Duration:</span>
                      <span className="ml-2 font-medium">{formatDuration(chunks.total_duration_s)}</span>
                    </div>
                  )}
                  <div>
                    <span className="text-gray-500">Last Updated:</span>
                    <span className="ml-2 font-medium">{formatDate(bookStatus.updated_at)}</span>
                  </div>
                  <div>
                    <span className="text-gray-500">Book ID:</span>
                    <span className="ml-2 font-mono text-xs">{bookStatus.book_id}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Error message */}
            {bookStatus.error_message && (
              <div className="mt-4 p-3 bg-red-50 rounded-md">
                <h4 className="text-sm font-medium text-red-800">Processing Error</h4>
                <p className="text-sm text-red-700 mt-1">{bookStatus.error_message}</p>
              </div>
            )}
          </div>

          {/* Audio Player */}
          {bookStatus.status === 'completed' && chunks && chunks.chunks.length > 0 ? (
            <div className="mb-6">
              <h2 className="text-lg font-medium text-gray-900 mb-4">Audio Player</h2>
              <AudioPlayer
                bookId={bookStatus.book_id}
                chunks={chunks.chunks}
                title={bookStatus.title}
              />
            </div>
          ) : bookStatus.status === 'completed' ? (
            <div className="card">
              <div className="text-center py-8">
                <ExclamationTriangleIcon className="mx-auto h-12 w-12 text-yellow-500" />
                <h3 className="mt-4 text-lg font-medium text-gray-900">No Audio Available</h3>
                <p className="mt-2 text-sm text-gray-500">
                  The book processing completed but no audio chunks were generated.
                </p>
              </div>
            </div>
          ) : (
            <div className="card">
              <div className="text-center py-8">
                <ClockIcon className="mx-auto h-12 w-12 text-gray-400" />
                <h3 className="mt-4 text-lg font-medium text-gray-900">Processing in Progress</h3>
                <p className="mt-2 text-sm text-gray-500">
                  Your audiobook is being processed. The audio player will appear when ready.
                </p>
                {bookStatus.status === 'failed' && (
                  <div className="mt-4">
                    <Link href="/upload" className="btn-primary">
                      Try Uploading Again
                    </Link>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </Layout>
    </>
  )
} 