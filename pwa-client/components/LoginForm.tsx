import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useAuth } from '../pages/_app'
import { apiClient } from '../lib/api'
import { LockClosedIcon } from '@heroicons/react/24/outline'

interface LoginFormData {
  apiKey: string
}

export default function LoginForm() {
  const [isValidating, setIsValidating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const { login } = useAuth()
  
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormData>()

  const onSubmit = async (data: LoginFormData) => {
    setIsValidating(true)
    setError(null)

    try {
      const isValid = await apiClient.validateApiKey(data.apiKey)
      
      if (isValid) {
        apiClient.setApiKey(data.apiKey)
        login(data.apiKey)
      } else {
        setError('Invalid API key. Please check your key and try again.')
      }
    } catch (err) {
      setError('Unable to connect to the server. Please try again later.')
    } finally {
      setIsValidating(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <div className="mx-auto h-12 w-12 flex items-center justify-center rounded-full bg-primary-100">
            <LockClosedIcon className="h-6 w-6 text-primary-600" />
          </div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
            Welcome to Audiobook Player
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            Enter your API key to access your audiobook library
          </p>
        </div>
        
        <form className="mt-8 space-y-6" onSubmit={handleSubmit(onSubmit)}>
          <div>
            <label htmlFor="apiKey" className="sr-only">
              API Key
            </label>
            <input
              {...register('apiKey', { 
                required: 'API key is required',
                minLength: {
                  value: 8,
                  message: 'API key must be at least 8 characters'
                }
              })}
              type="password"
              placeholder="Enter your API key"
              className="input-field"
              disabled={isValidating}
            />
            {errors.apiKey && (
              <p className="mt-1 text-sm text-red-600">{errors.apiKey.message}</p>
            )}
          </div>

          {error && (
            <div className="rounded-md bg-red-50 p-4">
              <div className="text-sm text-red-700">{error}</div>
            </div>
          )}

          <div>
            <button
              type="submit"
              disabled={isValidating}
              className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isValidating ? (
                <>
                  <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Validating...
                </>
              ) : (
                'Sign In'
              )}
            </button>
          </div>

          <div className="text-center">
            <p className="text-sm text-gray-600">
              Don't have an API key? Contact your administrator.
            </p>
          </div>
        </form>
      </div>
    </div>
  )
} 