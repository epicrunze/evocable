import { apiClient } from './client';
import { Book, BookWithChunks, BookLibraryQuery, BookUpload } from '@/types/book';
import { ApiResponse, PaginatedResponse } from '@/types/base';

export class BooksApi {
  /**
   * Get all books with optional filtering and pagination
   */
  async getBooks(query?: BookLibraryQuery): Promise<ApiResponse<PaginatedResponse<Book>>> {
    const params = query ? {
      search: query.search,
      status: query.status?.join(','),
      sortBy: query.sortBy,
      sortOrder: query.sortOrder,
      page: query.page?.toString(),
      limit: query.limit?.toString(),
    } : undefined;

    return apiClient.get<PaginatedResponse<Book>>('/books', params);
  }

  /**
   * Get a specific book by ID
   */
  async getBook(id: string): Promise<ApiResponse<Book>> {
    return apiClient.get<Book>(`/books/${id}`);
  }

  /**
   * Get a book with its audio chunks
   */
  async getBookWithChunks(id: string): Promise<ApiResponse<BookWithChunks>> {
    return apiClient.get<BookWithChunks>(`/books/${id}/chunks`);
  }

  /**
   * Upload a new book
   */
  async uploadBook(
    upload: BookUpload,
    onProgress?: (progress: number) => void
  ): Promise<ApiResponse<Book>> {
    return apiClient.upload<Book>('/books/upload', upload.file, onProgress);
  }

  /**
   * Delete a book
   */
  async deleteBook(id: string): Promise<ApiResponse<void>> {
    return apiClient.delete<void>(`/books/${id}`);
  }

  /**
   * Get book processing status
   */
  async getProcessingStatus(id: string): Promise<ApiResponse<{ status: Book['status']; percent_complete: number }>> {
    return apiClient.get<{ status: Book['status']; percent_complete: number }>(`/books/${id}/status`);
  }

  /**
   * Retry failed book processing
   */
  async retryProcessing(id: string): Promise<ApiResponse<Book>> {
    return apiClient.post<Book>(`/books/${id}/retry`);
  }

  /**
   * Download book metadata
   */
  async downloadMetadata(id: string): Promise<ApiResponse<Blob>> {
    return apiClient.get<Blob>(`/books/${id}/metadata`);
  }

  /**
   * Get audio chunk URL
   */
  getChunkUrl(bookId: string, chunkIndex: number): string {
    return `${apiClient['baseUrl']}/books/${bookId}/chunks/${chunkIndex}/audio`;
  }

  /**
   * Prefetch audio chunks for offline playback
   */
  async prefetchChunks(bookId: string, chunkIndices: number[]): Promise<ApiResponse<{ cached: number[] }>> {
    return apiClient.post<{ cached: number[] }>(`/books/${bookId}/prefetch`, {
      chunks: chunkIndices,
    });
  }
}

// Create singleton instance
export const booksApi = new BooksApi(); 