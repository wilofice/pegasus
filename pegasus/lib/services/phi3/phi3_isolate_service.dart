import 'dart:isolate';
import 'package:flutter_isolate/flutter_isolate.dart';
import 'phi3_model_manager.dart';

class Phi3IsolateService {
  static FlutterIsolate? _isolate;
  static SendPort? _sendPort;
  static bool _isInitialized = false;

  static Future<void> initialize() async {
    if (_isInitialized) return;

    final receivePort = ReceivePort();
    
    // Spawn isolate
    _isolate = await FlutterIsolate.spawn(
      _isolateEntryPoint,
      receivePort.sendPort,
    );

    // Wait for isolate to send its SendPort
    _sendPort = await receivePort.first as SendPort;
    _isInitialized = true;
  }

  static Future<String> generateText(String prompt, {int maxTokens = 100}) async {
    if (!_isInitialized) {
      await initialize();
    }

    final responsePort = ReceivePort();
    _sendPort!.send({
      'command': 'generate',
      'prompt': prompt,
      'maxTokens': maxTokens,
      'replyPort': responsePort.sendPort,
    });

    final response = await responsePort.first;
    responsePort.close();

    if (response is String) {
      return response;
    } else if (response is Map && response['error'] != null) {
      throw Exception(response['error']);
    } else {
      throw Exception('Invalid response from isolate');
    }
  }

  static void dispose() {
    _isolate?.kill();
    _isolate = null;
    _sendPort = null;
    _isInitialized = false;
  }

  // Isolate entry point
  static void _isolateEntryPoint(SendPort mainSendPort) async {
    final receivePort = ReceivePort();
    mainSendPort.send(receivePort.sendPort);

    Phi3ModelManager? modelManager;
    bool modelLoaded = false;

    await for (final message in receivePort) {
      if (message is Map) {
        final command = message['command'];
        final replyPort = message['replyPort'] as SendPort;

        try {
          switch (command) {
            case 'generate':
              if (!modelLoaded) {
                // Load model on first use
                modelManager = Phi3ModelManager();
                await modelManager.loadModel();
                modelLoaded = true;
              }

              final prompt = message['prompt'] as String;
              final maxTokens = message['maxTokens'] as int;
              
              final result = await modelManager!.generateText(
                prompt,
                maxTokens: maxTokens,
              );
              
              replyPort.send(result);
              break;

            case 'dispose':
              modelManager?.dispose();
              modelManager = null;
              modelLoaded = false;
              replyPort.send('disposed');
              break;

            default:
              replyPort.send({
                'error': 'Unknown command: $command',
              });
          }
        } catch (e) {
          replyPort.send({
            'error': e.toString(),
          });
        }
      }
    }
  }
}

// Alternative implementation using compute() for simpler cases
class Phi3ComputeService {
  static Phi3ModelManager? _modelManager;
  static bool _isLoaded = false;

  static Future<void> ensureModelLoaded() async {
    if (!_isLoaded) {
      _modelManager = Phi3ModelManager();
      await _modelManager!.loadModel();
      _isLoaded = true;
    }
  }

  static Future<String> generateTextSimple(String prompt, {int maxTokens = 100}) async {
    await ensureModelLoaded();
    return _modelManager!.generateText(prompt, maxTokens: maxTokens);
  }

  static void dispose() {
    _modelManager?.dispose();
    _modelManager = null;
    _isLoaded = false;
  }
}