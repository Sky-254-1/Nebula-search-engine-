# Nebula Mobile App Build Guide

## Prerequisites

### Java Development Kit (JDK)
- Install JDK 17 or higher
- Set `JAVA_HOME` environment variable
- Verify: `java -version` and `javac -version`

### Android SDK
- Install Android Studio
- Set `ANDROID_HOME` environment variable
- Install SDK 34 (Android 14)
- Install SDK 26 (Android 8.0 minimum)

### Node.js
- Install Node.js 18 or higher
- Install npm packages: `npm install`

### CocoaPods (iOS only)
- Install CocoaPods: `sudo gem install cocoapods`
- Run: `npx cap sync`

## Build Commands

### Build Web Assets
```bash
npm run build:web
```

### Sync with Capacitor
```bash
npx cap sync
```

### Build Android
```bash
# Open in Android Studio (recommended)
npx cap open android

# Or build via command line (requires Java and Android SDK)
./gradlew assembleDebug
```

### Build iOS
```bash
# Open in Xcode (requires macOS)
npx cap open ios

# Or build via command line
npx cap build ios
```

## Running the App

### Android
```bash
npm run android
```

### iOS
```bash
npm run ios
```

## Troubleshooting

### Java not found
Install JDK 17 and set `JAVA_HOME`:
```bash
set JAVA_HOME=C:\Program Files\Java\jdk-17
```

### Android SDK not found
Install Android Studio and set `ANDROID_HOME`:
```bash
set ANDROID_HOME=C:\Users\[username]\AppData\Local\Android\Sdk
```

### Gradle wrapper issues
Ensure `gradle-wrapper.jar` exists in `android/gradle/wrapper/`

## Architecture

- **Mobile Framework**: Capacitor 6.2
- **UI Framework**: React 18 + TypeScript
- **Backend**: FastAPI + PostgreSQL
- **Offline Storage**: SQLite via Capacitor SQLite plugin
- **Push Notifications**: Capacitor PushNotifications plugin
