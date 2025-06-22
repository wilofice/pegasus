import 'package:flutter/material.dart';
import '../services/voice_service.dart';

class MessageComposer extends StatefulWidget {
  final void Function(String) onSend;

  const MessageComposer({super.key, required this.onSend});

  @override
  State<MessageComposer> createState() => _MessageComposerState();
}

class _MessageComposerState extends State<MessageComposer> {
  final TextEditingController _controller = TextEditingController();
  final VoiceService _voice = VoiceService();

  Future<void> _handleVoice() async {
    final transcript = await _voice.listen();
    if (transcript != null && transcript.isNotEmpty) {
      widget.onSend(transcript);
    }
  }

  void _handleSend() {
    final text = _controller.text.trim();
    if (text.isNotEmpty) {
      widget.onSend(text);
      _controller.clear();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(8.0),
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller: _controller,
              decoration: const InputDecoration(
                hintText: 'Send a message',
              ),
              onSubmitted: (_) => _handleSend(),
            ),
          ),
          IconButton(
            icon: const Icon(Icons.send),
            onPressed: _handleSend,
          ),
          IconButton(
            icon: const Icon(Icons.mic),
            onPressed: _handleVoice,
          ),
        ],
      ),
    );
  }
}
