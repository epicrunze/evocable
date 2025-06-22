# Audiobook Player PWA

A Next.js Progressive Web App for streaming audiobooks with real-time processing status and offline capabilities.

## Features

- 🔐 **API Key Authentication** - Secure login with expandable multi-user support
- 📚 **Book Management** - Upload PDF, EPUB, and TXT files
- 🔍 **Search Library** - Find books quickly with real-time search
- 🎵 **Audio Streaming** - Play/pause/seek with cross-chunk navigation
- 📱 **Progressive Web App** - Install on mobile devices
- 🎨 **Responsive Design** - Works on desktop and mobile
- ⚡ **Real-time Updates** - Live processing status polling

## Tech Stack

- **Framework**: Next.js 14 with TypeScript
- **Styling**: Tailwind CSS
- **Icons**: Heroicons
- **PWA**: next-pwa plugin
- **API Client**: Axios with interceptors
- **Forms**: React Hook Form

## Development

### Prerequisites

- Node.js 18+
- npm or yarn
- Running audiobook API server

### Setup

1. **Install dependencies**:
   ```bash
   npm install
   ```

2. **Environment variables**:
   ```bash
   # API server URL (development)
   API_URL=http://localhost:8000
   ```

3. **Start development server**:
   ```bash
   npm run dev
   ```

4. **Access the app**:
   - Development: http://localhost:3000
   - Uses API proxy to backend at http://localhost:8000

### Build for Production

1. **Build the application**:
   ```bash
   npm run build
   ```

2. **Start production server**:
   ```bash
   npm start
   ```

## Docker Deployment

The app includes a multi-stage Dockerfile for production deployment:

```bash
# Build and run with Docker
docker build -t audiobook-pwa .
docker run -p 3000:3000 audiobook-pwa
```

## API Integration

The PWA communicates with the audiobook processing API:

- **Authentication**: Bearer token (API key)
- **Book Upload**: Multipart form data
- **Status Polling**: Real-time progress updates
- **Audio Streaming**: Direct chunk URL access

## PWA Features

- **Offline Support**: Service worker caching
- **Install Prompt**: Add to home screen
- **Responsive**: Mobile-first design
- **Fast Loading**: Optimized bundle size

## Component Architecture

```
pages/
├── _app.tsx           # Auth context & global setup
├── _document.tsx      # PWA manifest & meta tags
├── index.tsx          # Home page (library or login)
├── upload.tsx         # Book upload with drag-and-drop
└── book/[id].tsx      # Book detail with audio player

components/
├── AudioPlayer.tsx    # Streaming audio controls
├── BookLibrary.tsx    # Book management with search
├── Layout.tsx         # Navigation & responsive layout
└── LoginForm.tsx      # API key authentication

lib/
└── api.ts            # API client with auth
```

## Audio Player Features

- **Multi-chunk Playback**: Seamless transitions between audio segments
- **Seek Across Chunks**: Jump to any position in the audiobook
- **Volume Control**: Mute/unmute with volume slider
- **Skip Controls**: 15-second backward skip
- **Progress Display**: Current time and total duration
- **Chapter Navigation**: Visual chapter list

## Search & Filtering

- **Real-time Search**: Filter books by title as you type
- **Search Results**: Shows match count and results
- **Clear Search**: Easy reset with X button
- **No Results State**: Helpful empty state when no matches

## Development Commands

```bash
# Development
npm run dev          # Start development server
npm run build        # Build for production
npm start           # Start production server

# Code Quality
npm run lint        # Run ESLint
npm run format      # Format with Prettier
npm run format:check # Check formatting

# Testing
npm test            # Run tests
npm run test:watch  # Run tests in watch mode
```

## Environment Variables

```bash
# Required
API_URL=http://localhost:8000    # Backend API URL

# Optional
NEXT_PUBLIC_APP_NAME=Audiobooks  # App name for PWA
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

See main project LICENSE file. 