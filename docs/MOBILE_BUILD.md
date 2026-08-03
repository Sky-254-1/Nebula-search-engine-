# Nebula Mobile Build Configuration

This document provides an overview of the mobile build configuration for the Nebula Search mobile application.

## Overview

The Nebula Search mobile app is built using Capacitor, which allows the existing web frontend to be packaged as native iOS and Android applications. This approach enables:
- Code reuse across platforms
- Access to native device features
- Consistent user experience
- Fast development cycles

## Project Structure

```
mobile/
├── android/                 # Android native project files
│   ├── AndroidManifest.xml  # Android app configuration
│   ├── build.gradle         # Root build configuration
│   └── app/
│       └── build.gradle     # App-specific build configuration
├── ios/                     # iOS native project files
│   ├── Nebula/
│   │   ├── Info.plist       # iOS app metadata and permissions
│   │   └── LaunchScreen.storyboard  # Launch screen
│   ├── Podfile              # CocoaPods dependencies
│   └── Package.swift        # Swift Package Manager config
├── src/                     # Shared web source code
├── capacitor.config.ts      # Capacitor configuration
└── package.json             # Mobile app dependencies
```

## iOS Configuration

### Info.plist

The `Info.plist` file contains:
- App metadata (name, version, bundle ID)
- App Transport Security settings
- Permission descriptions for camera, photo library, microphone, etc.
- Supported interface orientations
- Device capabilities

### Key iOS Settings

```xml
<key>CFBundleIdentifier</key>
<string>com.nebula.search</string>
<key>LSRequiresIPhoneOS</key>
<true/>
<key>NSAppTransportSecurity</key>
<dict>
    <key>NSAllowsArbitraryLoads</key>
    <true/>
</dict>
```

### iOS Deployment Target

- Minimum: iOS 14.0
- Target: iOS 14.0+
- Deployment: iOS 14.0

## Android Configuration

### AndroidManifest.xml

The `AndroidManifest.xml` file contains:
- Required permissions (camera, storage, location, etc.)
- Application metadata
- Activity configurations
- Provider configurations for file sharing

### Key Android Permissions

```xml
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.CAMERA" />
<uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" />
<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />
```

### Android SDK Versions

- Minimum SDK: 26 (Android 8.0)
- Target SDK: 34 (Android 14)
- Compile SDK: 34

## Capacitor Configuration

### capacitor.config.ts

```typescript
const config: CapacitorConfig = {
  appId: 'com.nebula.search',
  appName: 'Nebula Search',
  webDir: '../frontend/dist',
  server: {
    androidScheme: 'https',
    cleartext: true,
  },
  plugins: {
    PushNotifications: {
      presentationOptions: ['badge', 'sound', 'alert'],
    },
    SplashScreen: {
      launchAutoHide: true,
      backgroundColor: '#0f0f1a',
    },
  },
};
```

### Key Capacitor Settings

- **App ID**: `com.nebula.search`
- **App Name**: Nebula Search
- **Web Directory**: `../frontend/dist` (build output from frontend)
- **Splash Screen**: Configured with auto-hide and custom background color

## Build Process

### Development Build

1. Build the frontend web app:
   ```bash
   cd frontend
   npm run build
   ```

2. Sync Capacitor with native projects:
   ```bash
   cd mobile
   npx cap sync
   ```

3. Open in native IDE:
   ```bash
   npx cap open ios    # For iOS
   npx cap open android # For Android
   ```

### Production Build

See the full build guide in `mobile/BUILD.md` for detailed production build instructions.

## Native Features

The mobile app uses the following Capacitor plugins:

| Plugin | Purpose |
|--------|---------|
| `@capacitor/camera` | Camera access for document scanning |
| `@capacitor/filesystem` | File operations |
| `@capacitor/network` | Network status monitoring |
| `@capacitor/preferences` | Local data storage |
| `@capacitor/push-notifications` | Push notifications |
| `@capacitor/share` | Share functionality |
| `@capacitor-community/speech-recognition` | Voice search |

## CI/CD Integration

The mobile app has automated CI/CD workflows defined in `.github/workflows/mobile-build.yml`:

### Workflow Triggers
- Push to mobile-related branches
- Pull requests with mobile changes
- Manual workflow dispatch

### Build Jobs
1. **iOS Build** - macOS runner with Xcode
2. **Android Build** - Ubuntu runner with Gradle
3. **Mobile E2E Tests** - Automated testing
4. **Mobile Performance Tests** - Performance benchmarks

### Artifacts
- iOS: `.xcarchive` and `.ipa` files
- Android: `.apk` and `.aab` files
- Retention: 7 days

## Requirements Coverage

This configuration addresses the following requirements:

| Requirement | Status | Notes |
|-------------|--------|-------|
| 11.1 | ✅ | iOS build configuration with Info.plist |
| 11.2 | ✅ | Android build configuration with AndroidManifest.xml |
| 11.3 | ✅ | CI/CD for mobile builds |
| 11.4 | ✅ | Build documentation |

## Troubleshooting

### Common Issues

1. **Pod install fails on iOS**
   - Run `pod repo update` and `pod install --repo-update`

2. **Gradle sync fails on Android**
   - Run `./gradlew clean` and `./gradlew --stop`

3. **Build fails with "module not found"**
   - Run `npx cap sync` to update native projects

For more troubleshooting tips, see `mobile/BUILD.md`.

## Additional Resources

- [Capacitor Documentation](https://capacitorjs.com/docs)
- [iOS Developer Library](https://developer.apple.com/documentation/)
- [Android Developer Documentation](https://developer.android.com/guide)
