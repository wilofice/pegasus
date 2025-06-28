import 'package:flutter_test/flutter_test.dart';
import 'package:pegasus/services/phi3/phi3_tokenizer.dart';
import 'package:pegasus/services/phi3/phi3_model_manager.dart';

void main() {
  group('Phi3Tokenizer Tests', () {
    late Phi3Tokenizer tokenizer;

    setUp(() {
      tokenizer = Phi3Tokenizer();
    });

    test('should encode simple text', () {
      final text = 'Hello, how are you?';
      final tokens = tokenizer.encode(text);
      
      expect(tokens, isNotEmpty);
      expect(tokens.first, equals(Phi3Tokenizer.startToken));
      expect(tokens.last, equals(Phi3Tokenizer.endToken));
    });

    test('should decode tokens back to text', () {
      final text = 'Hello world';
      final tokens = tokenizer.encode(text);
      final decoded = tokenizer.decode(tokens);
      
      // The decoded text might have different spacing/formatting
      expect(decoded.toLowerCase(), contains('hello'));
      expect(decoded.toLowerCase(), contains('world'));
    });

    test('should handle empty text', () {
      final tokens = tokenizer.encode('');
      expect(tokens.length, equals(2)); // Start and end tokens only
    });

    test('should create attention mask', () {
      final tokens = [1, 2, 3, 0, 0]; // Including padding
      final mask = tokenizer.createAttentionMask(tokens);
      
      expect(mask, equals([1, 1, 1, 0, 0]));
    });

    test('should pad tokens correctly', () {
      final tokens = [1, 2, 3];
      final padded = tokenizer.padTokens(tokens, 5);
      
      expect(padded.length, equals(5));
      expect(padded, equals([1, 2, 3, 0, 0]));
    });
  });

  group('Phi3ModelManager Tests', () {
    test('should initialize with default values', () {
      final manager = Phi3ModelManager();
      expect(manager.isLoaded, isFalse);
    });

    // Note: Full model loading tests would require the actual ONNX model file
    // These would typically be integration tests run on actual devices
  });
}