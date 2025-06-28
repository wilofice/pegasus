import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../services/phi3/phi3_model_manager.dart';
import '../services/phi3/phi3_isolate_service.dart';
import '../services/phi3/model_downloader.dart';

final phi3ModelProvider = Provider<Phi3ModelManager>((ref) {
  return Phi3ModelManager();
});

final isModelLoadingProvider = StateProvider<bool>((ref) => false);
final downloadProgressProvider = StateProvider<double>((ref) => 0.0);
final downloadStatusProvider = StateProvider<String>((ref) => '');
final isDownloadingProvider = StateProvider<bool>((ref) => false);
final chatMessagesProvider = StateProvider<List<ChatMessage>>((ref) => []);

class ChatMessage {
  final String text;
  final bool isUser;
  final DateTime timestamp;

  ChatMessage({
    required this.text,
    required this.isUser,
    required this.timestamp,
  });
}

class Phi3ChatScreen extends ConsumerStatefulWidget {
  const Phi3ChatScreen({Key? key}) : super(key: key);

  @override
  ConsumerState<Phi3ChatScreen> createState() => _Phi3ChatScreenState();
}

class _Phi3ChatScreenState extends ConsumerState<Phi3ChatScreen> {
  final TextEditingController _messageController = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  bool _isGenerating = false;
  final ModelDownloader _modelDownloader = ModelDownloader();

  @override
  void initState() {
    super.initState();
    // Delay model loading until after the widget tree is built
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _checkAndLoadModel();
    });
  }

  Future<void> _checkAndLoadModel() async {
    try {
      final isDownloaded = await _modelDownloader.isModelDownloaded();
      
      if (!isDownloaded) {
        _addSystemMessage('Model not found. Starting download...');
        await _downloadModel();
      } else {
        _addSystemMessage('Model found. Loading...');
        await _loadModel();
      }
    } catch (e) {
      _addSystemMessage('Error checking model: $e');
    }
  }

  Future<void> _downloadModel() async {
    ref.read(isDownloadingProvider.notifier).state = true;
    ref.read(downloadProgressProvider.notifier).state = 0.0;
    ref.read(downloadStatusProvider.notifier).state = 'Starting download...';
    
    try {
      await _modelDownloader.downloadModelWithProgress((progress, status) {
        ref.read(downloadProgressProvider.notifier).state = progress;
        ref.read(downloadStatusProvider.notifier).state = status;
      });
      
      _addSystemMessage('Model downloaded successfully. Loading...');
      await _loadModel();
    } catch (e) {
      _addSystemMessage('Download failed: $e');
    } finally {
      ref.read(isDownloadingProvider.notifier).state = false;
    }
  }

  Future<void> _loadModel() async {
    ref.read(isModelLoadingProvider.notifier).state = true;
    try {
      // Initialize isolate service
      await Phi3IsolateService.initialize();
      _addSystemMessage('Phi-3 isolate service initialized successfully!');
    } catch (e) {
      _addSystemMessage('Error initializing isolate service: $e');
    } finally {
      ref.read(isModelLoadingProvider.notifier).state = false;
    }
  }

  void _addSystemMessage(String message) {
    final messages = ref.read(chatMessagesProvider);
    ref.read(chatMessagesProvider.notifier).state = [
      ...messages,
      ChatMessage(
        text: message,
        isUser: false,
        timestamp: DateTime.now(),
      ),
    ];
    _scrollToBottom();
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  Future<void> _sendMessage() async {
    final text = _messageController.text.trim();
    if (text.isEmpty || _isGenerating) return;

    _messageController.clear();
    
    // Add user message
    final messages = ref.read(chatMessagesProvider);
    ref.read(chatMessagesProvider.notifier).state = [
      ...messages,
      ChatMessage(
        text: text,
        isUser: true,
        timestamp: DateTime.now(),
      ),
    ];
    _scrollToBottom();

    // Generate response
    setState(() {
      _isGenerating = true;
    });

    try {
      // Use isolate service for background processing
      final response = await Phi3IsolateService.generateText(
        text,
        maxTokens: 100,
      );

      // Add AI response
      final updatedMessages = ref.read(chatMessagesProvider);
      ref.read(chatMessagesProvider.notifier).state = [
        ...updatedMessages,
        ChatMessage(
          text: response,
          isUser: false,
          timestamp: DateTime.now(),
        ),
      ];
      _scrollToBottom();
    } catch (e) {
      _addSystemMessage('Error generating response: $e');
    } finally {
      setState(() {
        _isGenerating = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final isLoading = ref.watch(isModelLoadingProvider);
    final isDownloading = ref.watch(isDownloadingProvider);
    final downloadProgress = ref.watch(downloadProgressProvider);
    final downloadStatus = ref.watch(downloadStatusProvider);
    final messages = ref.watch(chatMessagesProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Phi-3 Mini Chat'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: isLoading ? null : _checkAndLoadModel,
            tooltip: 'Reload Model',
          ),
        ],
      ),
      body: Column(
        children: [
          if (isLoading)
            const LinearProgressIndicator(),
          if (isDownloading)
            _DownloadProgressWidget(
              progress: downloadProgress,
              status: downloadStatus,
            ),
          Expanded(
            child: ListView.builder(
              controller: _scrollController,
              padding: const EdgeInsets.all(16),
              itemCount: messages.length,
              itemBuilder: (context, index) {
                final message = messages[index];
                return _MessageBubble(message: message);
              },
            ),
          ),
          _InputBar(
            controller: _messageController,
            onSend: _sendMessage,
            isGenerating: _isGenerating,
            isModelLoaded: !isLoading && !isDownloading,
          ),
        ],
      ),
    );
  }

  @override
  void dispose() {
    _messageController.dispose();
    _scrollController.dispose();
    Phi3IsolateService.dispose();
    super.dispose();
  }
}

class _MessageBubble extends StatelessWidget {
  final ChatMessage message;

  const _MessageBubble({required this.message});

  @override
  Widget build(BuildContext context) {
    final isUser = message.isUser;
    final theme = Theme.of(context);

    return Align(
      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 4),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
        decoration: BoxDecoration(
          color: isUser
              ? theme.colorScheme.primary
              : theme.colorScheme.surfaceVariant,
          borderRadius: BorderRadius.circular(20),
        ),
        constraints: BoxConstraints(
          maxWidth: MediaQuery.of(context).size.width * 0.75,
        ),
        child: Text(
          message.text,
          style: TextStyle(
            color: isUser
                ? theme.colorScheme.onPrimary
                : theme.colorScheme.onSurfaceVariant,
          ),
        ),
      ),
    );
  }
}

class _InputBar extends StatelessWidget {
  final TextEditingController controller;
  final VoidCallback onSend;
  final bool isGenerating;
  final bool isModelLoaded;

  const _InputBar({
    required this.controller,
    required this.onSend,
    required this.isGenerating,
    required this.isModelLoaded,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        boxShadow: [
          BoxShadow(
            offset: const Offset(0, -2),
            blurRadius: 4,
            color: Colors.black.withOpacity(0.1),
          ),
        ],
      ),
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller: controller,
              enabled: isModelLoaded && !isGenerating,
              decoration: InputDecoration(
                hintText: isModelLoaded
                    ? 'Type a message...'
                    : 'Model not ready...',
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(24),
                  borderSide: BorderSide.none,
                ),
                filled: true,
                fillColor: Theme.of(context).colorScheme.surfaceVariant,
                contentPadding: const EdgeInsets.symmetric(
                  horizontal: 20,
                  vertical: 10,
                ),
              ),
              onSubmitted: (_) => onSend(),
            ),
          ),
          const SizedBox(width: 8),
          IconButton(
            onPressed: isModelLoaded && !isGenerating ? onSend : null,
            icon: isGenerating
                ? const SizedBox(
                    width: 24,
                    height: 24,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.send),
          ),
        ],
      ),
    );
  }
}

class _DownloadProgressWidget extends StatelessWidget {
  final double progress;
  final String status;

  const _DownloadProgressWidget({
    required this.progress,
    required this.status,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surfaceContainerHighest.withValues(alpha: 0.7),
        border: Border(
          bottom: BorderSide(
            color: Theme.of(context).colorScheme.outline.withValues(alpha: 0.3),
          ),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.download, size: 20),
              const SizedBox(width: 8),
              Text(
                'Downloading Phi-3 Model',
                style: Theme.of(context).textTheme.titleSmall,
              ),
              const Spacer(),
              Text(
                '${(progress * 100).toInt()}%',
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ],
          ),
          const SizedBox(height: 8),
          LinearProgressIndicator(
            value: progress,
            backgroundColor: Theme.of(context).colorScheme.outline.withValues(alpha: 0.3),
          ),
          const SizedBox(height: 4),
          Text(
            status,
            style: Theme.of(context).textTheme.bodySmall,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
        ],
      ),
    );
  }
}