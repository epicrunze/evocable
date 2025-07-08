# Component Interface Specification

This document defines the standardized interfaces between different modules in the PWA audiobook application, enabling parallel development while maintaining clean boundaries and strong typing.

---

## 1. Interface Design Principles

### Core Principles
- **Strongly Typed**: All interfaces use TypeScript for compile-time safety
- **Minimal Coupling**: Modules depend only on interface contracts, not implementations
- **Consistent Patterns**: Standardized naming and structure across all interfaces
- **Future-Proof**: Interfaces designed to accommodate feature expansion
- **Error-First**: Comprehensive error handling built into all interfaces

### Interface Structure
```typescript
// Standard interface pattern
export interface ModuleInterface<T = any> {
  // Data types
  readonly types: {
    Input: T;
    Output: any;
    Error: any;
  };
  
  // Core methods
  readonly methods: {
    [key: string]: (...args: any[]) => Promise<any>;
  };
  
  // Event handlers
  readonly events: {
    [key: string]: (payload: any) => void;
  };
}
```

---

## 2. Core Type Definitions

### Base Types
```typescript
// src/types/base.ts
export interface BaseEntity {
  id: string;
  created_at: string;
  updated_at: string;
}

export interface ApiResponse<T = any> {
  data?: T;
  error?: ApiError;
  loading: boolean;
  timestamp: string;
}

export interface ApiError {
  code: string;
  message: string;
  details?: any;
  retry?: boolean;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  has_next: boolean;
  has_previous: boolean;
}

export interface StorageQuota {
  used: number;
  total: number;
  available: number;
  percentage: number;
}
```

### Book-Related Types
```typescript
// src/types/book.ts
export interface Book extends BaseEntity {
  title: string;
  format: 'pdf' | 'epub' | 'txt';
  status: BookStatus;
  percent_complete: number;
  total_chunks: number | null;
  duration?: number; // in seconds
  file_size?: number; // in bytes
  error_message?: string;
}

export type BookStatus = 
  | 'pending'
  | 'processing'
  | 'extracting'
  | 'segmenting'
  | 'generating_audio'
  | 'transcoding'
  | 'completed'
  | 'failed';

export interface AudioChunk {
  seq: number;
  duration_s: number;
  url: string;
  file_size: number;
  cached?: boolean;
}

export interface BookWithChunks extends Book {
  chunks: AudioChunk[];
  total_duration_s: number;
}
```

### Audio-Related Types
```typescript
// src/types/audio.ts
export interface AudioState {
  bookId: string;
  currentChunk: number;
  currentTime: number;
  duration: number;
  isPlaying: boolean;
  isLoading: boolean;
  volume: number;
  playbackRate: number;
  bufferedRanges: TimeRange[];
  error?: AudioError;
}

export interface AudioError {
  type: 'network' | 'decode' | 'playback' | 'permission';
  message: string;
  recoverable: boolean;
  chunk?: number;
}

export interface Bookmark {
  id: string;
  bookId: string;
  title: string;
  time: number; // in seconds
  chunk: number;
  created_at: string;
}

export interface PlaybackSession {
  bookId: string;
  startTime: number;
  endTime?: number;
  lastPosition: number;
  completed: boolean;
}
```

---

## 3. Module Interface Contracts

### Authentication Module Interface
```typescript
// src/types/interfaces/auth.ts
export interface AuthenticationInterface {
  types: {
    LoginRequest: {
      apiKey: string;
      remember?: boolean;
    };
    LoginResponse: {
      sessionToken: string;
      expiresAt: string;
      user: {
        id: string;
        permissions: string[];
      };
    };
    AuthState: {
      isAuthenticated: boolean;
      user: any | null;
      token: string | null;
      expiresAt: string | null;
    };
    AuthError: {
      type: 'invalid_key' | 'expired' | 'network' | 'server';
      message: string;
      canRetry: boolean;
    };
  };
  
  methods: {
    login: (request: LoginRequest) => Promise<ApiResponse<LoginResponse>>;
    logout: () => Promise<void>;
    refresh: () => Promise<ApiResponse<LoginResponse>>;
    isValid: () => boolean;
    getToken: () => string | null;
  };
  
  events: {
    onLogin: (user: any) => void;
    onLogout: () => void;
    onTokenExpired: () => void;
    onError: (error: AuthError) => void;
  };
}

// Usage example
export const useAuth = (): AuthenticationInterface => {
  // Implementation details hidden from consumers
};
```

### Library Management Interface
```typescript
// src/types/interfaces/library.ts
export interface LibraryInterface {
  types: {
    LibraryQuery: {
      search?: string;
      status?: BookStatus[];
      sortBy?: 'title' | 'created_at' | 'updated_at';
      sortOrder?: 'asc' | 'desc';
      page?: number;
      limit?: number;
    };
    LibraryResponse: PaginatedResponse<Book>;
    LibraryState: {
      books: Book[];
      loading: boolean;
      error: ApiError | null;
      query: LibraryQuery;
    };
  };
  
  methods: {
    getBooks: (query?: LibraryQuery) => Promise<ApiResponse<LibraryResponse>>;
    getBook: (id: string) => Promise<ApiResponse<Book>>;
    deleteBook: (id: string) => Promise<ApiResponse<void>>;
    searchBooks: (query: string) => Promise<ApiResponse<Book[]>>;
    updateBookStatus: (id: string, status: BookStatus) => Promise<ApiResponse<Book>>;
  };
  
  events: {
    onBookAdded: (book: Book) => void;
    onBookUpdated: (book: Book) => void;
    onBookDeleted: (bookId: string) => void;
    onStatusChanged: (bookId: string, status: BookStatus) => void;
  };
}
```

### Upload Management Interface
```typescript
// src/types/interfaces/upload.ts
export interface UploadInterface {
  types: {
    UploadRequest: {
      file: File;
      title: string;
      format: 'pdf' | 'epub' | 'txt';
      language?: string;
      voice?: string;
    };
    UploadProgress: {
      bookId: string;
      uploaded: number;
      total: number;
      percentage: number;
      speed: number; // bytes per second
      estimatedTime: number; // seconds remaining
      status: 'uploading' | 'processing' | 'completed' | 'failed';
    };
    UploadResponse: {
      bookId: string;
      status: string;
      message: string;
    };
    UploadError: {
      type: 'file_size' | 'file_type' | 'network' | 'server';
      message: string;
      canRetry: boolean;
    };
  };
  
  methods: {
    uploadBook: (request: UploadRequest) => Promise<ApiResponse<UploadResponse>>;
    cancelUpload: (bookId: string) => Promise<void>;
    pauseUpload: (bookId: string) => Promise<void>;
    resumeUpload: (bookId: string) => Promise<void>;
    getUploadProgress: (bookId: string) => Promise<ApiResponse<UploadProgress>>;
  };
  
  events: {
    onUploadStart: (bookId: string) => void;
    onUploadProgress: (progress: UploadProgress) => void;
    onUploadComplete: (bookId: string) => void;
    onUploadError: (error: UploadError) => void;
  };
}
```

### Audio Player Interface
```typescript
// src/types/interfaces/audio.ts
export interface AudioPlayerInterface {
  types: {
    PlaybackRequest: {
      bookId: string;
      startChunk?: number;
      startTime?: number;
      autoPlay?: boolean;
    };
    PlaybackControls: {
      play: () => Promise<void>;
      pause: () => Promise<void>;
      seek: (time: number) => Promise<void>;
      setVolume: (volume: number) => Promise<void>;
      setPlaybackRate: (rate: number) => Promise<void>;
      skipForward: (seconds: number) => Promise<void>;
      skipBackward: (seconds: number) => Promise<void>;
    };
    AudioMetadata: {
      bookId: string;
      totalDuration: number;
      totalChunks: number;
      currentChunk: number;
      currentTime: number;
      bufferedTime: number;
      playbackQuality: 'auto' | 'high' | 'medium' | 'low';
    };
  };
  
  methods: {
    initialize: (request: PlaybackRequest) => Promise<ApiResponse<AudioMetadata>>;
    getControls: () => PlaybackControls;
    getCurrentState: () => AudioState;
    destroy: () => Promise<void>;
  };
  
  events: {
    onPlay: () => void;
    onPause: () => void;
    onTimeUpdate: (time: number) => void;
    onChunkChange: (chunk: number) => void;
    onBufferUpdate: (bufferedTime: number) => void;
    onError: (error: AudioError) => void;
    onEnd: () => void;
  };
}
```

### Offline Storage Interface
```typescript
// src/types/interfaces/storage.ts
export interface OfflineStorageInterface {
  types: {
    DownloadRequest: {
      bookId: string;
      priority?: 'high' | 'medium' | 'low';
      backgroundSync?: boolean;
    };
    DownloadProgress: {
      bookId: string;
      chunksDownloaded: number;
      totalChunks: number;
      bytesDownloaded: number;
      totalBytes: number;
      percentage: number;
      status: 'queued' | 'downloading' | 'completed' | 'failed' | 'paused';
    };
    StorageInfo: {
      quota: StorageQuota;
      books: Array<{
        bookId: string;
        title: string;
        size: number;
        downloadedAt: string;
      }>;
    };
  };
  
  methods: {
    downloadBook: (request: DownloadRequest) => Promise<ApiResponse<void>>;
    cancelDownload: (bookId: string) => Promise<void>;
    removeBook: (bookId: string) => Promise<void>;
    getDownloadProgress: (bookId: string) => Promise<ApiResponse<DownloadProgress>>;
    getStorageInfo: () => Promise<ApiResponse<StorageInfo>>;
    clearStorage: () => Promise<void>;
    isBookAvailable: (bookId: string) => Promise<boolean>;
  };
  
  events: {
    onDownloadStart: (bookId: string) => void;
    onDownloadProgress: (progress: DownloadProgress) => void;
    onDownloadComplete: (bookId: string) => void;
    onDownloadError: (bookId: string, error: any) => void;
    onStorageChange: (info: StorageInfo) => void;
  };
}
```

---

## 4. Cross-Module Communication

### Event Bus Interface
```typescript
// src/types/interfaces/eventBus.ts
export interface EventBusInterface {
  types: {
    EventPayload<T = any>: {
      type: string;
      data: T;
      timestamp: number;
      source: string;
    };
    EventHandler<T = any>: (payload: EventPayload<T>) => void;
  };
  
  methods: {
    subscribe: <T>(eventType: string, handler: EventHandler<T>) => () => void;
    publish: <T>(eventType: string, data: T, source: string) => void;
    unsubscribe: (eventType: string, handler: EventHandler) => void;
    clear: () => void;
  };
}

// Global event types
export type GlobalEvents = {
  'auth:login': { user: any };
  'auth:logout': {};
  'book:added': { book: Book };
  'book:updated': { book: Book };
  'book:deleted': { bookId: string };
  'player:play': { bookId: string };
  'player:pause': { bookId: string };
  'download:complete': { bookId: string };
  'storage:warning': { usage: number };
  'network:online': {};
  'network:offline': {};
  'error:critical': { error: any };
};
```

### Service Worker Interface
```typescript
// src/types/interfaces/serviceWorker.ts
export interface ServiceWorkerInterface {
  types: {
    CacheStrategy: 'cache-first' | 'network-first' | 'stale-while-revalidate';
    CacheConfig: {
      name: string;
      strategy: CacheStrategy;
      maxAge: number;
      maxEntries: number;
    };
    SyncTask: {
      id: string;
      type: 'upload' | 'download' | 'delete';
      data: any;
      priority: number;
      retryCount: number;
    };
  };
  
  methods: {
    register: () => Promise<ServiceWorkerRegistration>;
    unregister: () => Promise<void>;
    update: () => Promise<void>;
    addToCache: (urls: string[], cacheName: string) => Promise<void>;
    removeFromCache: (urls: string[], cacheName: string) => Promise<void>;
    scheduleBackgroundSync: (task: SyncTask) => Promise<void>;
    getNetworkStatus: () => Promise<boolean>;
  };
  
  events: {
    onInstall: () => void;
    onActivate: () => void;
    onUpdate: () => void;
    onCacheUpdate: (cacheName: string) => void;
    onSyncComplete: (taskId: string) => void;
    onNetworkChange: (isOnline: boolean) => void;
  };
}
```

---

## 5. Component Props Interfaces

### Common Component Props
```typescript
// src/types/interfaces/components.ts
export interface BaseComponentProps {
  className?: string;
  testId?: string;
  'aria-label'?: string;
  'aria-describedby'?: string;
}

export interface LoadingProps extends BaseComponentProps {
  loading: boolean;
  error?: string | null;
  retry?: () => void;
  skeleton?: React.ComponentType;
}

export interface ErrorBoundaryProps extends BaseComponentProps {
  fallback?: React.ComponentType<{ error: Error; reset: () => void }>;
  onError?: (error: Error, errorInfo: any) => void;
}
```

### Feature-Specific Component Props
```typescript
// Library components
export interface BookCardProps extends BaseComponentProps {
  book: Book;
  onPlay: (bookId: string) => void;
  onDownload: (bookId: string) => void;
  onDelete: (bookId: string) => void;
  isDownloaded: boolean;
  downloadProgress?: number;
}

export interface LibraryGridProps extends BaseComponentProps {
  books: Book[];
  loading: boolean;
  error?: string | null;
  onBookSelect: (book: Book) => void;
  onRefresh: () => void;
  emptyState?: React.ComponentType;
}

// Audio player components
export interface AudioPlayerProps extends BaseComponentProps {
  bookId: string;
  autoPlay?: boolean;
  showChapters?: boolean;
  showBookmarks?: boolean;
  onTrackEnd?: () => void;
}

export interface PlaybackControlsProps extends BaseComponentProps {
  isPlaying: boolean;
  currentTime: number;
  duration: number;
  volume: number;
  playbackRate: number;
  onPlay: () => void;
  onPause: () => void;
  onSeek: (time: number) => void;
  onVolumeChange: (volume: number) => void;
  onRateChange: (rate: number) => void;
}
```

---

## 6. Hook Interfaces

### Standard Hook Pattern
```typescript
// src/types/interfaces/hooks.ts
export interface HookInterface<T, P = any> {
  data: T | null;
  loading: boolean;
  error: string | null;
  refetch: (params?: P) => Promise<void>;
  reset: () => void;
}

// Specific hook interfaces
export interface UseBookHook extends HookInterface<Book> {
  updateStatus: (status: BookStatus) => Promise<void>;
  delete: () => Promise<void>;
  download: () => Promise<void>;
  isDownloaded: boolean;
}

export interface UseAudioHook extends HookInterface<AudioState> {
  controls: PlaybackControls;
  metadata: AudioMetadata;
  bookmarks: Bookmark[];
  addBookmark: (title: string) => Promise<void>;
  removeBookmark: (id: string) => Promise<void>;
  seekToBookmark: (id: string) => Promise<void>;
}

export interface UseUploadHook extends HookInterface<UploadProgress> {
  upload: (request: UploadRequest) => Promise<void>;
  cancel: () => Promise<void>;
  pause: () => Promise<void>;
  resume: () => Promise<void>;
}
```

---

## 7. Error Handling Interfaces

### Standardized Error Types
```typescript
// src/types/interfaces/errors.ts
export interface ErrorInterface {
  code: string;
  message: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  recoverable: boolean;
  metadata?: any;
  timestamp: number;
}

export interface ErrorHandlerInterface {
  handle: (error: ErrorInterface) => void;
  report: (error: ErrorInterface) => Promise<void>;
  retry: (operationId: string) => Promise<void>;
  dismiss: (errorId: string) => void;
}

export interface ErrorBoundaryInterface {
  captureError: (error: Error, errorInfo: any) => void;
  reset: () => void;
  getLastError: () => ErrorInterface | null;
}
```

---

## 8. Testing Interfaces

### Mock Interfaces
```typescript
// src/types/interfaces/testing.ts
export interface MockServiceInterface<T> {
  mock: Partial<T>;
  restore: () => void;
  verify: () => void;
  reset: () => void;
}

export interface TestUtilsInterface {
  renderWithProviders: (component: React.ReactElement, options?: any) => any;
  createMockBook: (overrides?: Partial<Book>) => Book;
  createMockAudioChunk: (overrides?: Partial<AudioChunk>) => AudioChunk;
  waitForAsync: (callback: () => Promise<void>) => Promise<void>;
}
```

---

## 9. Performance Monitoring Interfaces

### Metrics Collection
```typescript
// src/types/interfaces/performance.ts
export interface PerformanceMetrics {
  loadTime: number;
  renderTime: number;
  memoryUsage: number;
  networkLatency: number;
  errorCount: number;
  userInteractions: number;
}

export interface PerformanceMonitorInterface {
  startMeasure: (name: string) => void;
  endMeasure: (name: string) => number;
  recordMetric: (name: string, value: number) => void;
  getMetrics: () => PerformanceMetrics;
  reportMetrics: () => Promise<void>;
}
```

---

## 10. Module Integration Guidelines

### Interface Implementation Rules
1. **All implementations must fully satisfy their interface contracts**
2. **No direct dependencies between module implementations**
3. **All inter-module communication goes through defined interfaces**
4. **Interfaces should be backward-compatible when possible**
5. **Breaking changes require version bumps and migration guides**

### Development Workflow
1. **Define interfaces before implementation**
2. **Create mock implementations for parallel development**
3. **Write integration tests against interfaces**
4. **Replace mocks with real implementations incrementally**
5. **Validate all interfaces before module integration**

---

These comprehensive interface definitions ensure that all modules can be developed in parallel while maintaining type safety, clear boundaries, and consistent patterns throughout the application. 