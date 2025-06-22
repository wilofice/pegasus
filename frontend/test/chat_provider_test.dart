import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../lib/providers/chat_provider.dart';
import '../lib/models/message_model.dart';

void main() {
  test('addMessage stores messages', () {
    final container = ProviderContainer();
    addTearDown(container.dispose);
    container.read(chatProvider.notifier).addMessage(
      Message(text: 'Hello', isUser: true),
    );
    final messages = container.read(chatProvider);
    expect(messages.length, 1);
    expect(messages.first.text, 'Hello');
  });
}
