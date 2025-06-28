# Phi-3 Mini Integration Guide

This document describes the integration of Microsoft's Phi-3 Mini 4K model into the Pegasus Flutter app.

## Overview

The integration allows users to run the Phi-3 Mini language model locally on their device, providing offline AI chat capabilities.

## Setup Instructions

### 1. Model Preparation

The Phi-3 Mini model is now downloaded automatically when you first use the feature:

1. **No manual download required** - The app will download the model (~2.4GB) automatically
2. **First-time setup** - On first use, the app will show a download progress indicator
3. **Storage location** - Models are stored in the app's documents directory
4. **Offline use** - Once downloaded, the model works completely offline

### 2. Dependencies

The following dependencies have been added to support Phi-3:

- `onnxruntime: ^1.4.1` - For running ONNX models
- `path_provider: ^2.1.1` - For accessing device storage
- `flutter_isolate: ^2.0.4` - For background processing
- `shared_preferences: ^2.2.2` - For caching model metadata

### 3. Architecture

The integration consists of several components:

#### Core Components

- **Phi3ModelManager** (`lib/services/phi3/phi3_model_manager.dart`)
  - Handles model loading and inference
  - Manages ONNX Runtime session
  - Processes input/output tensors

- **ModelDownloader** (`lib/services/phi3/model_downloader.dart`)
  - Downloads models from Hugging Face automatically
  - Shows download progress with real-time updates
  - Manages model storage in app documents directory

- **Phi3Tokenizer** (`lib/services/phi3/phi3_tokenizer.dart`)
  - Simplified BPE tokenizer implementation
  - Handles text encoding/decoding
  - Creates attention masks and padding

- **Phi3IsolateService** (`lib/services/phi3/phi3_isolate_service.dart`)
  - Runs inference in background isolate
  - Prevents UI blocking during generation
  - Manages isolate lifecycle

#### UI Components

- **Phi3ChatScreen** (`lib/screens/phi3_chat_screen.dart`)
  - Dedicated chat interface for Phi-3
  - Manages conversation state
  - Shows loading indicators

- **HomeScreen** (`lib/screens/home_screen.dart`)
  - Navigation hub for both chat modes
  - Clear distinction between server and local modes

## Usage

1. Launch the app
2. From the home screen, tap "Phi-3 Mini Chat (Experimental)"
3. **First time only**: Wait for the model to download (~2.4GB, progress shown)
4. Wait for the model to initialize
5. Start chatting with the local AI model

### Download Process

- **Automatic**: No manual intervention required
- **Progress tracking**: Real-time download progress and status
- **Resumable**: Download will resume if interrupted
- **One-time**: Only downloads once, then uses cached model

## Performance Considerations

- **Model Size**: ~2GB storage required
- **Memory Usage**: 4-6GB RAM recommended for smooth operation
- **Cold Start**: First inference may take 20-30 seconds
- **Token Generation**: Expect 5-10 tokens/second on modern devices

## Testing

Run the test suite:

```bash
flutter test test/phi3_integration_test.dart
```

## Current Limitations

1. **Tokenizer**: The current implementation uses a simplified tokenizer. For production use, integrate the official Phi-3 tokenizer.

2. **Model Format**: Ensure the ONNX model is optimized for mobile inference (quantized if possible).

3. **Context Length**: Limited to 4K tokens as per Phi-3 Mini specifications.

4. **Platform Support**: ONNX Runtime support varies by platform. Test thoroughly on target devices.

## Future Improvements

1. Implement proper Phi-3 tokenizer with full vocabulary
2. Add model quantization for reduced memory usage
3. Implement streaming token generation
4. Add conversation history management
5. Support for multiple model variants
6. Add model download functionality within the app

## Troubleshooting

### Model Loading Fails
- Verify model file exists at `assets/models/phi3_mini.onnx`
- Check available device storage
- Ensure sufficient RAM available

### Poor Performance
- Close other apps to free memory
- Consider using quantized model version
- Reduce max token generation length

### App Crashes
- Check device compatibility with ONNX Runtime
- Monitor memory usage during inference
- Enable release mode optimizations

### Release Build Issues (FIXED)
If you encounter errors like "To access 'Phi3IsolateService' from native code, it must be annotated":
- ✅ **FIXED**: Added `@pragma('vm:entry-point')` annotations to all isolate entry points
- This is required when using flutter_isolate in AOT/release mode

### Android Back Navigation Warning (FIXED)
If you see "OnBackInvokedCallback is not enabled":
- ✅ **FIXED**: Added `android:enableOnBackInvokedCallback="true"` to AndroidManifest.xml
- This enables proper back gesture handling on Android 13+

### Riverpod Provider Lifecycle Error (FIXED)
If you encounter "Tried to modify a provider while the widget tree was building":
- ✅ **FIXED**: Moved provider modifications out of `initState()` using `WidgetsBinding.instance.addPostFrameCallback()`
- Provider state changes are now properly delayed until after the widget tree is built
- This prevents inconsistent UI state when multiple widgets listen to the same provider

### Build Failed - Asset Compression Error (FIXED)
If you encounter "Required array size too large" during build:
- ✅ **FIXED**: Removed large model files from assets, implemented runtime download
- Models are now downloaded automatically from Hugging Face on first use
- APK size reduced significantly, avoiding Android asset compression limits
- Download progress is shown to user with real-time updates