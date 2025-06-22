import 'dart:async';

import 'package:speech_to_text/speech_to_text.dart' as stt;
import 'package:flutter_tts/flutter_tts.dart';

class VoiceService {
  final stt.SpeechToText _speech = stt.SpeechToText();
  final FlutterTts _tts = FlutterTts();

  Future<String?> listen() async {
    final available = await _speech.initialize();
    if (!available) return null;

    final completer = Completer<String?>();
    _speech.listen(onResult: (result) {
      if (result.finalResult) {
        completer.complete(result.recognizedWords);
      }
    });
    return completer.future;
  }

  Future<void> stopListening() async {
    await _speech.stop();
  }

  Future<void> speak(String text) async {
    await _tts.speak(text);
  }
}
