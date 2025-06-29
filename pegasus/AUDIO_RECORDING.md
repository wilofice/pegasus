# Audio Recording Feature

This document describes the audio recording functionality added to the Pegasus Flutter app.

## Overview

The audio recording feature allows users to:
- Record audio with configurable duration limits (10s - 5min)
- Configure audio quality settings (low/medium/high)
- Play back recorded audio
- Automatically upload recordings to the Pegasus backend
- Manage recording preferences

## Features

### ✅ Core Functionality
- **Timer-based Recording**: Auto-stop when max duration is reached
- **Real-time Timer**: Shows elapsed time during recording
- **Quality Settings**: Three quality levels with different bitrates
- **Auto-upload**: Optional automatic upload to backend
- **Audio Playback**: Built-in playback of recorded files
- **Permission Handling**: Proper microphone permission requests

### ✅ User Interface
- **Circular Timer Display**: Visual recording progress
- **Settings Dialog**: Configure max duration, quality, and auto-upload
- **Control Buttons**: Record/Stop, Play/Stop, Upload, Delete
- **Status Indicators**: Clear visual feedback for all states

### ✅ Backend Integration
- **File Upload**: Upload recordings to Pegasus backend
- **API Extensions**: Enhanced PegasusApiClient with file upload support
- **Progress Feedback**: Upload status and error handling

## Architecture

### Components

1. **RecordingScreen** (`lib/screens/recording_screen.dart`)
   - Main recording interface with timer and controls
   - Riverpod state management for recording state
   - Settings dialog for preferences

2. **PrefsService** (`lib/services/prefs_service.dart`)
   - Manages recording preferences using SharedPreferences
   - Configurable settings for duration, quality, and upload

3. **PegasusApiClient** (`lib/api/pegasus_api_client.dart`)
   - Enhanced with file upload capabilities using Dio
   - Audio file management endpoints

### Dependencies

```yaml
# Audio recording dependencies
flutter_sound: ^9.2.13        # Audio recording and playback
permission_handler: ^11.3.0    # Microphone permissions
dio: ^5.4.0                    # HTTP uploads with multipart support
just_audio: ^0.9.36           # Audio playback
```

## Usage

### 1. Access Recording Screen
- Navigate from home screen via "Audio Recorder" button
- Or add to navigation routes: `Navigator.pushNamed(context, '/record')`

### 2. Recording Process
1. Tap the microphone button to start recording
2. Timer shows elapsed time and remaining time
3. Recording auto-stops at max duration or manually stop
4. Options to play, upload, or delete the recording

### 3. Settings Configuration
- Tap settings icon in app bar
- Configure:
  - **Max Duration**: 10s to 300s (5 minutes)
  - **Auto Upload**: Enable/disable automatic upload
  - **Audio Quality**: Low (64kbps), Medium (128kbps), High (256kbps)

## File Management

### Storage Location
- Recordings stored in: `ApplicationDocumentsDirectory/recording_[timestamp].m4a`
- Format: AAC-LC in MP4 container
- Automatic timestamped filenames

### Quality Settings
- **Low**: 64 kbps, 22.05 kHz sampling rate
- **Medium**: 128 kbps, 44.1 kHz sampling rate (default)
- **High**: 256 kbps, 48 kHz sampling rate

### Upload Integration
- Endpoint: `POST /upload/audio`
- Multipart form data with file, timestamp, and duration
- Error handling and retry capabilities

## Platform Requirements

### Android
- **Min SDK Version**: 24 (Android 7.0)
- **Permissions**: `android.permission.RECORD_AUDIO`
- Auto-requests microphone permission

### iOS
- **Permissions**: `NSMicrophoneUsageDescription` in Info.plist
- Compatible with iOS 12.0+

### Permissions Added
The app automatically requests microphone permission when needed. Users can manage permissions in device settings.

## Technical Implementation

### State Management
Uses Riverpod providers for:
- `isRecordingProvider`: Recording status
- `recordingTimeProvider`: Elapsed time counter
- `recordingFileProvider`: Current recording file path
- `maxRecordingTimeProvider`: Maximum recording duration
- `isPlayingProvider`: Playback status
- `isUploadingProvider`: Upload status

### Error Handling
- Permission denied → Settings dialog
- File system errors → User-friendly error messages
- Upload failures → Retry options
- Invalid states → Graceful recovery

### Background Handling
- Proper cleanup when app backgrounded
- Timer cancellation on dispose
- Resource management for recorder and player

## Future Enhancements

### Planned Features
1. **Waveform Visualization**: Real-time audio waveform display
2. **Multiple Formats**: Support for different audio formats
3. **Cloud Storage**: Integration with cloud storage providers
4. **Audio Editing**: Basic trim and edit functionality
5. **Transcription**: Integration with speech-to-text services
6. **Recording History**: List of all recorded files
7. **Sharing Options**: Share recordings via various apps

### Backend Enhancements
1. **Audio Processing**: Server-side audio processing
2. **Transcription Service**: Automatic speech-to-text
3. **Storage Management**: Organized file storage and retrieval
4. **Analytics**: Recording usage analytics

## Troubleshooting

### Common Issues

1. **Permission Denied**
   - Solution: Check device microphone permissions
   - Path: Settings > Apps > Pegasus > Permissions

2. **Recording Fails to Start**
   - Check available storage space
   - Ensure no other apps using microphone
   - Restart the app

3. **Upload Failures**
   - Verify network connectivity
   - Check backend server status
   - File size limitations

4. **Audio Quality Issues**
   - Adjust quality settings in preferences
   - Check microphone hardware
   - Reduce background noise

### Debug Information
- Logs available in Flutter console
- Error states shown in UI with descriptive messages
- File paths and sizes logged for debugging

## Testing

### Manual Testing Checklist
- [ ] Record audio with all quality settings
- [ ] Test auto-stop functionality
- [ ] Verify playback works correctly
- [ ] Test upload to backend
- [ ] Check permission handling
- [ ] Verify settings persistence
- [ ] Test app backgrounding during recording
- [ ] Check file cleanup and deletion

### Device Testing
- Test on different Android versions (7.0+)
- Verify on various device manufacturers
- Test with different microphone configurations
- Check performance on low-end devices

## Installation Notes

The audio recording feature requires:
1. Updated dependencies in `pubspec.yaml`
2. Android minSdkVersion 24 or higher
3. Microphone permissions in app manifests
4. Backend support for file uploads

The feature integrates seamlessly with the existing Pegasus app architecture and maintains consistency with the current design patterns.