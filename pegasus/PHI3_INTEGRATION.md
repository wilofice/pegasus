# Phi-3 Mini Integration Guide

This document describes the integration of Microsoft's Phi-3 Mini 4K model into the Pegasus Flutter app.

## Overview

The integration allows users to run the Phi-3 Mini language model locally on their device, providing offline AI chat capabilities.

## Setup Instructions

### 1. Model Preparation

Before running the app with Phi-3 functionality, you need to obtain the Phi-3 Mini ONNX model:

1. Download the Phi-3 Mini ONNX model (approximately 2GB)
2. Place the model file at: `assets/models/phi3_mini.onnx`
3. Update `pubspec.yaml` to include the model in assets:

```yaml
flutter:
  assets:
    - assets/models/phi3_mini.onnx
```

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
3. Wait for the model to initialize (first load copies model to device storage)
4. Start chatting with the local AI model

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