# Nebula Mobile

Capacitor-based mobile shell for Nebula Search Engine.

## Development

### Prerequisites
- Node.js 20+
- Android Studio (for Android)
- Xcode (for iOS, macOS only)

### Setup
```bash
cd mobile
npm install
npm run build:web  # builds frontend and syncs to mobile
```

### Run
```bash
npm run android    # opens Android Studio
npm run ios        # opens Xcode (macOS only)
```

### Build APK
```bash
npm run apk:debug  # generates android/app/build/outputs/apk/debug/app-debug.apk
```

## Architecture
- Uses Capacitor 6 for native bridge
- Offline-first: search results cached locally, queued sync when online
- Push notifications via Firebase (Android) / APNs (iOS)
- Secure token storage via Capacitor Preferences
