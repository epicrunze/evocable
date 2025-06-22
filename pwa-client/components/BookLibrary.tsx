import { useState, useEffect } from 'react'
import { apiClient, BookStatusResponse } from '../lib/api'
import { useAuth } from '../pages/_app'
import Link from 'next/link'
import { 
  ClockIcon, 
  PlayIcon, 
  ExclamationTriangleIcon,
  CloudArrowUpIcon,
  BookOpenIcon,
  MagnifyingGlassIcon,
  XMarkIcon
} from '@heroicons/react/24/outline'

export default function BookLibrary() {
  const [books, setBooks] = useState<BookStatusResponse[]>([])
  const [filteredBooks, setFilteredBooks] = useState<BookStatusResponse[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const { apiKey } = useAuth()

  useEffect(() => {
    if (apiKey) {
      apiClient.setApiKey(apiKey)
      loadBooks()
    }
  }, [apiKey])

  // Filter books based on search query
  useEffect(() => {
    if (!searchQuery.trim()) {
      setFilteredBooks(books)
    } else {
      const filtered = books.filter(book =>
        book.title.toLowerCase().includes(searchQuery.toLowerCase())
      )
      setFilteredBooks(filtered)
    }
  }, [books, searchQuery])

  const loadBooks = async () => {
    try {
      setLoading(true)
      // Note: The current API doesn't have a "list all books" endpoint
      // This would need to be added to the backend API
      // For now, we'll show a placeholder message
      setBooks([])
    } catch (err) {
      setError('Failed to load books')
    } finally {
      setLoading(false)
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'status-completed'
      case 'failed':
        return 'status-failed'
      case 'processing':
      case 'extracting':
      case 'segmenting':
      case 'generating_audio':
      case 'transcoding':
        return 'status-processing'
      default:
        return 'status-pending'
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
        return 'Segmenting'
      case 'generating_audio':
        return 'Generating Audio'
      case 'transcoding':
        return 'Transcoding'
      case 'completed':
        return 'Ready'
      case 'failed':
        return 'Failed'
      default:
        return status
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="rounded-md bg-red-50 p-4">
          <div className="flex">
            <ExclamationTriangleIcon className="h-5 w-5 text-red-400" />
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800">Error</h3>
              <div className="mt-2 text-sm text-red-700">{error}</div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="p-6">
      <div className="sm:flex sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Your Audiobook Library</h1>
          <p className="mt-2 text-sm text-gray-700">
            Upload and manage your audiobook collection
          </p>
        </div>
        <div className="mt-4 sm:mt-0">
          <Link
            href="/upload"
            className="btn-primary inline-flex items-center"
          >
            <CloudArrowUpIcon className="h-5 w-5 mr-2" />
            Upload Book
          </Link>
        </div>
      </div>

      {/* Search Bar */}
      {books.length > 0 && (
        <div className="mt-6">
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <MagnifyingGlassIcon className="h-5 w-5 text-gray-400" />
            </div>
            <input
              type="text"
              placeholder="Search your audiobooks..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="block w-full pl-10 pr-10 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute inset-y-0 right-0 pr-3 flex items-center"
              >
                <XMarkIcon className="h-5 w-5 text-gray-400 hover:text-gray-600" />
              </button>
            )}
          </div>
          {searchQuery && (
            <p className="mt-2 text-sm text-gray-600">
              {filteredBooks.length} of {books.length} books match "{searchQuery}"
            </p>
          )}
        </div>
      )}

      {filteredBooks.length === 0 && searchQuery ? (
        <div className="mt-12 text-center">
          <MagnifyingGlassIcon className="mx-auto h-12 w-12 text-gray-400" />
          <h3 className="mt-4 text-lg font-medium text-gray-900">No books found</h3>
          <p className="mt-2 text-sm text-gray-500">
            No audiobooks match your search for "{searchQuery}"
          </p>
          <div className="mt-6">
            <button
              onClick={() => setSearchQuery('')}
              className="btn-secondary"
            >
              Clear Search
            </button>
          </div>
        </div>
      ) : books.length === 0 ? (
        <div className="mt-12 text-center">
          <BookOpenIcon className="mx-auto h-12 w-12 text-gray-400" />
          <h3 className="mt-4 text-lg font-medium text-gray-900">No audiobooks yet</h3>
          <p className="mt-2 text-sm text-gray-500">
            Get started by uploading your first book
          </p>
          <div className="mt-6">
            <Link href="/upload" className="btn-primary">
              <CloudArrowUpIcon className="h-5 w-5 mr-2" />
              Upload Your First Book
            </Link>
          </div>
        </div>
      ) : (
        <div className="mt-8 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {filteredBooks.map((book) => (
            <div key={book.book_id} className="card hover:shadow-lg transition-shadow">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <h3 className="text-lg font-medium text-gray-900 truncate">
                    {book.title}
                  </h3>
                  <p className="mt-1 text-sm text-gray-500">
                    {formatDate(book.created_at)}
                  </p>
                </div>
                <span className={`status-badge ${getStatusColor(book.status)}`}>
                  {getStatusText(book.status)}
                </span>
              </div>

              {book.status !== 'completed' && book.status !== 'failed' && (
                <div className="mt-4">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-600">Progress</span>
                    <span className="text-gray-900">{Math.round(book.percent_complete)}%</span>
                  </div>
                  <div className="mt-2 bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-primary-600 h-2 rounded-full transition-all duration-300"
                      style={{ width: `${book.percent_complete}%` }}
                    />
                  </div>
                </div>
              )}

              {book.error_message && (
                <div className="mt-4 p-3 bg-red-50 rounded-md">
                  <p className="text-sm text-red-700">{book.error_message}</p>
                </div>
              )}

              <div className="mt-6 flex items-center justify-between">
                <div className="flex items-center text-sm text-gray-500">
                  <ClockIcon className="h-4 w-4 mr-1" />
                  {book.total_chunks > 0 ? `${book.total_chunks} chunks` : 'Processing...'}
                </div>
                
                {book.status === 'completed' ? (
                  <Link
                    href={`/book/${book.book_id}`}
                    className="inline-flex items-center px-3 py-1.5 border border-transparent text-sm font-medium rounded-md text-primary-700 bg-primary-100 hover:bg-primary-200 transition-colors"
                  >
                    <PlayIcon className="h-4 w-4 mr-1" />
                    Play
                  </Link>
                ) : (
                  <button
                    disabled
                    className="inline-flex items-center px-3 py-1.5 border border-gray-300 text-sm font-medium rounded-md text-gray-400 bg-gray-100 cursor-not-allowed"
                  >
                    <ClockIcon className="h-4 w-4 mr-1" />
                    Processing
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
} 