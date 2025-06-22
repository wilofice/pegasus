# Pegasus Flutter App

This directory contains the Flutter frontend for the Pegasus project. It was
initialised manually as a lightweight skeleton.

## Setup

Ensure Flutter is installed then run:

```bash
flutter pub get
flutter run
```

The project uses Firebase for push notifications and requires a Firebase
project configured with FCM. Voice interaction relies on the
`speech_to_text` and `flutter_tts` packages.

## Project Structure

- `lib/` contains the Dart source files
- `lib/screens/` UI screens
- `lib/widgets/` reusable widgets
- `lib/api/` API client
- `lib/models/` data models
- `lib/providers/` state management providers
- `lib/services/` app services (voice, notifications)

Unit tests reside in the `test/` directory and can be executed with
`flutter test`.
