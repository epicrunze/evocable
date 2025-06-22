import { useState, useRef } from 'react'
import { useForm } from 'react-hook-form'
import { useAuth } from './_app'
import { apiClient, BookSubmissionRequest, BookResponse } from '../lib/api'
import Layout from '../components/Layout'
import Head from 'next/head'
import { useRouter } from 'next/router'
import {
  CloudArrowUpIcon,
  DocumentIcon,
  XMarkIcon,
  CheckCircleIcon
} from '@heroicons/react/24/outline'

interface UploadFormData {
  title: string
  format: 'pdf' | 'epub' | 'txt'
  file: FileList
}

export default function UploadPage() {
  const [isDragOver, setIsDragOver] = useState(false)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [uploadSuccess, setUploadSuccess] = useState<BookResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const router = useRouter()
  const { apiKey } = useAuth()

  const {
    register,
    handleSubmit,
    formState: { errors },
    setValue,
    watch,
    reset
  } = useForm<UploadFormData>()

  const watchedFormat = watch('format')

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(true)
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)
    
    const files = e.dataTransfer.files
    if (files.length > 0) {
      const file = files[0]
      handleFileSelection(file)
    }
  }

  const handleFileSelection = (file: File) => {
    // Validate file type
    const extension = file.name.split('.').pop()?.toLowerCase()
    const validExtensions = ['pdf', 'epub', 'txt']
    
    if (!extension || !validExtensions.includes(extension)) {
      setError('Please select a PDF, EPUB, or TXT file')
      return
    }

    // Auto-detect format from file extension
    if (extension === 'pdf' || extension === 'epub' || extension === 'txt') {
      setValue('format', extension)
    }

    setSelectedFile(file)
    setError(null)

    // Auto-populate title from filename
    const titleFromFilename = file.name.replace(/\.[^/.]+$/, '')
    setValue('title', titleFromFilename)
  }

  const onFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (files && files.length > 0) {
      handleFileSelection(files[0])
    }
  }

  const onSubmit = async (data: UploadFormData) => {
    if (!selectedFile) {
      setError('Please select a file')
      return
    }

    setUploading(true)
    setError(null)

    try {
      const bookData: BookSubmissionRequest = {
        title: data.title,
        format: data.format,
        file: selectedFile
      }

      const response = await apiClient.submitBook(bookData)
      setUploadSuccess(response)
      
      // Reset form after successful upload
      reset()
      setSelectedFile(null)
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }

    } catch (err: any) {
      if (err.response?.data?.detail) {
        setError(err.response.data.detail)
      } else {
        setError('Failed to upload book. Please try again.')
      }
    } finally {
      setUploading(false)
    }
  }

  const removeFile = () => {
    setSelectedFile(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
    setError(null)
  }

  const viewBook = () => {
    if (uploadSuccess) {
      router.push(`/book/${uploadSuccess.book_id}`)
    }
  }

  return (
    <>
      <Head>
        <title>Upload Book - Audiobook Player</title>
      </Head>
      
      <Layout>
        <div className="p-6 max-w-2xl mx-auto">
          <div className="mb-8">
            <h1 className="text-2xl font-bold text-gray-900">Upload New Audiobook</h1>
            <p className="mt-2 text-sm text-gray-600">
              Upload a PDF, EPUB, or TXT file to convert it into an audiobook
            </p>
          </div>

          {uploadSuccess ? (
            <div className="card">
              <div className="text-center">
                <CheckCircleIcon className="mx-auto h-12 w-12 text-green-500" />
                <h3 className="mt-4 text-lg font-medium text-gray-900">Book Uploaded Successfully!</h3>
                <p className="mt-2 text-sm text-gray-500">
                  Your book "{uploadSuccess.book_id}" is now being processed.
                </p>
                <div className="mt-6 flex flex-col sm:flex-row gap-3 justify-center">
                  <button
                    onClick={viewBook}
                    className="btn-primary"
                  >
                    View Processing Status
                  </button>
                  <button
                    onClick={() => setUploadSuccess(null)}
                    className="btn-secondary"
                  >
                    Upload Another Book
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
              {/* File Upload Area */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Select File
                </label>
                <div
                  className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
                    isDragOver
                      ? 'border-primary-400 bg-primary-50'
                      : 'border-gray-300 hover:border-gray-400'
                  }`}
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onDrop={handleDrop}
                >
                  {selectedFile ? (
                    <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                      <div className="flex items-center">
                        <DocumentIcon className="h-8 w-8 text-gray-400 mr-3" />
                        <div className="text-left">
                          <p className="text-sm font-medium text-gray-900">{selectedFile.name}</p>
                          <p className="text-xs text-gray-500">
                            {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                          </p>
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={removeFile}
                        className="ml-4 text-gray-400 hover:text-gray-500"
                      >
                        <XMarkIcon className="h-5 w-5" />
                      </button>
                    </div>
                  ) : (
                    <div>
                      <CloudArrowUpIcon className="mx-auto h-12 w-12 text-gray-400" />
                      <div className="mt-4">
                        <p className="text-lg font-medium text-gray-900">
                          Drop your file here, or{' '}
                          <button
                            type="button"
                            className="text-primary-600 hover:text-primary-500"
                            onClick={() => fileInputRef.current?.click()}
                          >
                            browse
                          </button>
                        </p>
                        <p className="mt-2 text-sm text-gray-500">
                          Supports PDF, EPUB, and TXT files up to 50MB
                        </p>
                      </div>
                    </div>
                  )}
                </div>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf,.epub,.txt"
                  onChange={onFileInputChange}
                  className="hidden"
                />
              </div>

              {/* Book Details */}
              <div className="space-y-4">
                <div>
                  <label htmlFor="title" className="block text-sm font-medium text-gray-700 mb-1">
                    Book Title
                  </label>
                  <input
                    {...register('title', { required: 'Book title is required' })}
                    type="text"
                    className="input-field"
                    placeholder="Enter book title"
                  />
                  {errors.title && (
                    <p className="mt-1 text-sm text-red-600">{errors.title.message}</p>
                  )}
                </div>

                <div>
                  <label htmlFor="format" className="block text-sm font-medium text-gray-700 mb-1">
                    File Format
                  </label>
                  <select
                    {...register('format', { required: 'File format is required' })}
                    className="input-field"
                  >
                    <option value="">Select format</option>
                    <option value="pdf">PDF</option>
                    <option value="epub">EPUB</option>
                    <option value="txt">TXT</option>
                  </select>
                  {errors.format && (
                    <p className="mt-1 text-sm text-red-600">{errors.format.message}</p>
                  )}
                </div>
              </div>

              {error && (
                <div className="rounded-md bg-red-50 p-4">
                  <div className="text-sm text-red-700">{error}</div>
                </div>
              )}

              <div className="flex justify-end space-x-3">
                <button
                  type="button"
                  onClick={() => router.push('/')}
                  className="btn-secondary"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={uploading || !selectedFile}
                  className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {uploading ? (
                    <>
                      <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      Uploading...
                    </>
                  ) : (
                    'Upload Book'
                  )}
                </button>
              </div>
            </form>
          )}
        </div>
      </Layout>
    </>
  )
} 