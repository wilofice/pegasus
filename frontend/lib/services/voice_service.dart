import 'package:speech_to_text/speech_to_text.dart' as stt;
import 'package:flutter_tts/flutter_tts.dart';

class VoiceService {
  final stt.SpeechToText _speech = stt.SpeechToText();
  final FlutterTts _tts = FlutterTts();

  Future<String?> listen({Duration listenFor = const Duration(seconds: 5)}) async {
    final available = await _speech.initialize();
    if (!available) return null;
    String transcript = '';
    await _speech.listen(
      listenFor: listenFor,
      onResult: (result) {
        transcript = result.recognizedWords;
      },
    );
    await Future.delayed(listenFor);
    await _speech.stop();
    return transcript.isEmpty ? null : transcript;
  }

  Future<void> stopListening() async {
    await _speech.stop();
  }

  Future<void> speak(String text) async {
    await _tts.speak(text);
  }
}
