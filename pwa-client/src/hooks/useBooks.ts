import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { booksApi } from '@/lib/api/books';
import { BookLibraryQuery, BookUpload } from '@/types/book';

// Query keys
export const BOOKS_QUERY_KEYS = {
  all: ['books'] as const,
  lists: () => [...BOOKS_QUERY_KEYS.all, 'list'] as const,
  list: (query?: BookLibraryQuery) => [...BOOKS_QUERY_KEYS.lists(), query] as const,
  details: () => [...BOOKS_QUERY_KEYS.all, 'detail'] as const,
  detail: (id: string) => [...BOOKS_QUERY_KEYS.details(), id] as const,
  chunks: (id: string) => [...BOOKS_QUERY_KEYS.detail(id), 'chunks'] as const,
  status: (id: string) => [...BOOKS_QUERY_KEYS.detail(id), 'status'] as const,
};

/**
 * Hook to fetch books with filtering and pagination
 */
export function useBooks(query?: BookLibraryQuery) {
  return useQuery({
    queryKey: BOOKS_QUERY_KEYS.list(query),
    queryFn: () => booksApi.getBooks(query),
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 10 * 60 * 1000, // 10 minutes
  });
}

/**
 * Hook to fetch a specific book
 */
export function useBook(id: string) {
  return useQuery({
    queryKey: BOOKS_QUERY_KEYS.detail(id),
    queryFn: () => booksApi.getBook(id),
    enabled: !!id,
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * Hook to fetch a book with audio chunks
 */
export function useBookWithChunks(id: string) {
  return useQuery({
    queryKey: BOOKS_QUERY_KEYS.chunks(id),
    queryFn: () => booksApi.getBookWithChunks(id),
    enabled: !!id,
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * Hook to track book processing status
 */
export function useBookStatus(id: string, enabled = true) {
  return useQuery({
    queryKey: BOOKS_QUERY_KEYS.status(id),
    queryFn: () => booksApi.getProcessingStatus(id),
    enabled: enabled && !!id,
    refetchInterval: (query) => {
      // Stop polling if processing is complete or failed
      const status = query.state.data?.data?.status;
      if (status === 'completed' || status === 'failed') {
        return false;
      }
      return 2000; // Poll every 2 seconds
    },
    staleTime: 0, // Always fresh for status updates
  });
}

/**
 * Hook to upload a book
 */
export function useUploadBook() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ upload, onProgress }: { upload: BookUpload; onProgress?: (progress: number) => void }) =>
      booksApi.uploadBook(upload, onProgress),
    onSuccess: (response) => {
      // Invalidate and refetch books list
      queryClient.invalidateQueries({ queryKey: BOOKS_QUERY_KEYS.lists() });
      
      // Add the new book to cache if successful
      if (response.data) {
        queryClient.setQueryData(
          BOOKS_QUERY_KEYS.detail(response.data.id),
          response
        );
      }
    },
  });
}

/**
 * Hook to delete a book
 */
export function useDeleteBook() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => booksApi.deleteBook(id),
    onSuccess: (_, id) => {
      // Remove from cache
      queryClient.removeQueries({ queryKey: BOOKS_QUERY_KEYS.detail(id) });
      queryClient.removeQueries({ queryKey: BOOKS_QUERY_KEYS.chunks(id) });
      queryClient.removeQueries({ queryKey: BOOKS_QUERY_KEYS.status(id) });
      
      // Invalidate lists
      queryClient.invalidateQueries({ queryKey: BOOKS_QUERY_KEYS.lists() });
    },
  });
}

/**
 * Hook to retry book processing
 */
export function useRetryBookProcessing() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => booksApi.retryProcessing(id),
    onSuccess: (response, id) => {
      // Update the book in cache
      if (response.data) {
        queryClient.setQueryData(
          BOOKS_QUERY_KEYS.detail(id),
          response
        );
      }
      
      // Invalidate status to start polling again
      queryClient.invalidateQueries({ queryKey: BOOKS_QUERY_KEYS.status(id) });
    },
  });
}

/**
 * Hook to prefetch books for offline access
 */
export function usePrefetchBooks() {
  const queryClient = useQueryClient();

  return {
    prefetchBook: (id: string) => {
      return queryClient.prefetchQuery({
        queryKey: BOOKS_QUERY_KEYS.detail(id),
        queryFn: () => booksApi.getBook(id),
        staleTime: 10 * 60 * 1000,
      });
    },
    prefetchBookWithChunks: (id: string) => {
      return queryClient.prefetchQuery({
        queryKey: BOOKS_QUERY_KEYS.chunks(id),
        queryFn: () => booksApi.getBookWithChunks(id),
        staleTime: 10 * 60 * 1000,
      });
    },
  };
} 