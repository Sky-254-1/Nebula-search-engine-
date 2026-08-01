# Nebula Mobile App

A native mobile application for the Nebula Search Engine platform, built with Capacitor.

## Features

- **Search**: Perform hybrid searches across web and documents
- **AI Assistant**: Chat with the Nebula AI assistant
- **Documents**: Upload, view, and manage documents
- **Notifications**: Real-time push notifications
- **Analytics**: View search analytics and insights
- **Offline**: Full offline support with caching
- **Dark Mode**: Theme support with automatic system detection

## Tech Stack

| Component | Technology |
|-----------|------------|
| Mobile Framework | Capacitor 6.2 |
| UI Framework | React 18 + TypeScript |
| Android | Kotlin (for native modules) |
| iOS | Swift (for native modules) |
| Backend API | FastAPI + PostgreSQL |
| Local Storage | SQLite |
| State Management | Zustand + React Context |

## Project Structure

```
mobile/
├── src/                    # TypeScript source files
│   ├── app.ts             # App initialization
│   ├── auth.ts            # Authentication services
│   ├── config.ts          # App configuration
│   ├── main.ts            # Entry point
│   └── search.ts          # Search services
├── plugins/               # Native plugins
│   └── native.ts          # Capacitor plugins wrapper
├── sync/                  # Offline sync
│   └── queue.ts           # Sync queue management
├── android/               # Android native project
├── ios/                   # iOS native project
├── assets/                # App assets
├── package.json           # Dependencies
└── capacitor.config.ts    # Capacitor configuration
```

## Installation

```bash
cd mobile
npm install
npx cap sync
```

## Build

```bash
# Build web assets
npm run build:web

# Sync with Capacitor
npx cap sync

# Open in Android Studio
npx cap open android

# Open in Xcode (macOS only)
npx cap open ios
```

## Requirements

- **Java**: JDK 17 or higher
- **Android SDK**: API 34 (Android 14)
- **Node.js**: 18 or higher
- **iOS**: Xcode 15+ (macOS only)

## License

MIT
