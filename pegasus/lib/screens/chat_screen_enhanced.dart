/// Enhanced Chat Screen using API Client V2
/// 
/// This screen demonstrates the new Chat V2 capabilities including:
/// - Context-aware responses with citations
/// - Session management and persistence
/// - Advanced conversation modes and response styles
/// - Source attribution and follow-up suggestions
/// - Real-time confidence scoring

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../widgets/message_bubble.dart';
import '../widgets/message_composer.dart';
import '../models/message_model.dart';
import '../models/api_enums.dart';
import '../models/chat_v2_models.dart';
import '../providers/chat_provider.dart';
import '../api/pegasus_api_client_v2.dart';
import '../services/voice_service.dart';

/// Enhanced chat screen with Chat V2 features
class ChatScreenEnhanced extends ConsumerStatefulWidget {
  const ChatScreenEnhanced({super.key});

  @override
  ConsumerState<ChatScreenEnhanced> createState() => _ChatScreenEnhancedState();
}

class _ChatScreenEnhancedState extends ConsumerState<ChatScreenEnhanced> {
  late final ScrollController _scrollController;
  late final PegasusApiClientV2 _apiClient;
  late final VoiceService _voiceService;
  
  String? _currentSessionId;
  ConversationMode _conversationMode = ConversationMode.standard;
  ResponseStyle _responseStyle = ResponseStyle.professional;
  bool _includeSources = true;
  bool _enablePlugins = true;
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    _scrollController = ScrollController();
    _apiClient = PegasusApiClientV2.defaultConfig();
    _voiceService = VoiceService();
  }

  @override
  void dispose() {
    _scrollController.dispose();
    _apiClient.close();
    super.dispose();
  }

  void _addMessage(String text, bool isUser, {List<SourceInfo>? sources, List<String>? suggestions}) {
    // For now, we'll use the existing simple message model
    // In Phase 2, we'll create enhanced message models with sources and suggestions
    ref.read(chatProvider.notifier).addMessage(Message(text: text, isUser: isUser));
    
    // Auto-scroll to bottom
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

  Future<void> _sendMessage(String text) async {
    if (text.trim().isEmpty || _isLoading) return;

    setState(() => _isLoading = true);
    _addMessage(text, true);

    try {
      // Create Chat V2 request with current settings
      final request = ChatRequestV2(
        message: text,
        sessionId: _currentSessionId,
        userId: 'flutter_user', // In production, use actual user ID
        conversationMode: _conversationMode,
        responseStyle: _responseStyle,
        aggregationStrategy: AggregationStrategy.hybrid,
        rankingStrategy: RankingStrategy.ensemble,
        maxContextResults: 15,
        includeSources: _includeSources,
        includeConfidence: true,
        enablePlugins: _enablePlugins,
        useLocalLlm: false,
      );

      // Send message using Chat V2 API
      final response = await _apiClient.sendMessageV2(request);

      // Update session ID if this is a new conversation
      if (_currentSessionId == null) {
        _currentSessionId = response.sessionId;
      }

      // Add the response message
      _addMessage(
        response.response, 
        false, 
        sources: response.sources,
        suggestions: response.suggestions,
      );

      // Speak the response if voice is enabled
      if (response.response.isNotEmpty) {
        await _voiceService.speak(response.response);
      }

      // Show additional info in debug mode
      if (response.confidenceScore != null) {
        _showResponseInfo(response);
      }

    } catch (e) {
      _addMessage('Error: ${e.toString()}', false);
      _showErrorSnackBar('Failed to send message: ${e.toString()}');
    } finally {
      setState(() => _isLoading = false);
    }
  }

  void _showResponseInfo(ChatResponseV2 response) {
    // Show a brief info about the response quality
    final confidence = response.confidenceScore ?? 0.0;
    final contextCount = response.contextResultsCount;
    final processingTime = response.processingTimeMs;

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          '${(confidence * 100).toStringAsFixed(0)}% confidence • '
          '$contextCount sources • '
          '${processingTime.toStringAsFixed(0)}ms'
        ),
        duration: const Duration(seconds: 2),
        backgroundColor: confidence >= 0.8 ? Colors.green : Colors.orange,
      ),
    );
  }

  void _showErrorSnackBar(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: Colors.red,
        duration: const Duration(seconds: 4),
      ),
    );
  }

  void _showSettingsDialog() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Chat Settings'),
        content: StatefulBuilder(
          builder: (context, setDialogState) => Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              // Conversation Mode
              DropdownButtonFormField<ConversationMode>(
                value: _conversationMode,
                decoration: const InputDecoration(labelText: 'Conversation Mode'),
                items: ConversationMode.values
                    .map((mode) => DropdownMenuItem(
                          value: mode,
                          child: Text(mode.value),
                        ))
                    .toList(),
                onChanged: (value) => setDialogState(() => _conversationMode = value!),
              ),
              const SizedBox(height: 16),
              
              // Response Style
              DropdownButtonFormField<ResponseStyle>(
                value: _responseStyle,
                decoration: const InputDecoration(labelText: 'Response Style'),
                items: ResponseStyle.values
                    .map((style) => DropdownMenuItem(
                          value: style,
                          child: Text(style.value),
                        ))
                    .toList(),
                onChanged: (value) => setDialogState(() => _responseStyle = value!),
              ),
              const SizedBox(height: 16),
              
              // Include Sources
              SwitchListTile(
                title: const Text('Include Sources'),
                subtitle: const Text('Show source citations in responses'),
                value: _includeSources,
                onChanged: (value) => setDialogState(() => _includeSources = value),
              ),
              
              // Enable Plugins
              SwitchListTile(
                title: const Text('Enable Plugins'),
                subtitle: const Text('Use plugins for enhanced analysis'),
                value: _enablePlugins,
                onChanged: (value) => setDialogState(() => _enablePlugins = value),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () {
              setState(() {}); // Update the main state
              Navigator.of(context).pop();
            },
            child: const Text('Apply'),
          ),
        ],
      ),
    );
  }

  void _clearConversation() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Clear Conversation'),
        content: const Text('Are you sure you want to clear the current conversation?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () {
              ref.read(chatProvider.notifier).clear();
              setState(() => _currentSessionId = null);
              Navigator.of(context).pop();
            },
            style: ElevatedButton.styleFrom(backgroundColor: Colors.red),
            child: const Text('Clear'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final messages = ref.watch(chatProvider);

    return Scaffold(
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Pegasus Chat Enhanced'),
            if (_currentSessionId != null)
              Text(
                'Session: ${_currentSessionId!.substring(0, 8)}...',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: Colors.white70,
                ),
              ),
          ],
        ),
        backgroundColor: Theme.of(context).primaryColor,
        foregroundColor: Colors.white,
        actions: [
          // Settings button
          IconButton(
            icon: const Icon(Icons.tune),
            onPressed: _showSettingsDialog,
            tooltip: 'Chat Settings',
          ),
          // Clear conversation button
          IconButton(
            icon: const Icon(Icons.clear_all),
            onPressed: _clearConversation,
            tooltip: 'Clear Conversation',
          ),
          // Info button showing current mode
          PopupMenuButton<String>(
            icon: const Icon(Icons.info_outline),
            tooltip: 'Current Settings',
            itemBuilder: (context) => [
              PopupMenuItem(
                enabled: false,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Mode: ${_conversationMode.value}'),
                    Text('Style: ${_responseStyle.value}'),
                    Text('Sources: ${_includeSources ? 'On' : 'Off'}'),
                    Text('Plugins: ${_enablePlugins ? 'On' : 'Off'}'),
                  ],
                ),
              ),
            ],
          ),
        ],
      ),
      body: Column(
        children: [
          // Status bar showing current settings
          Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            decoration: BoxDecoration(
              color: Theme.of(context).primaryColor.withOpacity(0.1),
              border: const Border(bottom: BorderSide(color: Colors.grey, width: 0.5)),
            ),
            child: Row(
              children: [
                Icon(
                  _conversationMode == ConversationMode.creative 
                      ? Icons.brush 
                      : _conversationMode == ConversationMode.analytical
                          ? Icons.analytics
                          : Icons.chat,
                  size: 16,
                  color: Theme.of(context).primaryColor,
                ),
                const SizedBox(width: 8),
                Text(
                  '${_conversationMode.value} • ${_responseStyle.value}',
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: Theme.of(context).primaryColor,
                    fontWeight: FontWeight.w500,
                  ),
                ),
                const Spacer(),
                if (_includeSources) ...[
                  const Icon(Icons.source, size: 16, color: Colors.green),
                  const SizedBox(width: 4),
                ],
                if (_enablePlugins) ...[
                  const Icon(Icons.extension, size: 16, color: Colors.blue),
                  const SizedBox(width: 4),
                ],
                if (_isLoading) ...[
                  const SizedBox(
                    width: 12,
                    height: 12,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  ),
                  const SizedBox(width: 8),
                  const Text('Thinking...', style: TextStyle(fontSize: 12)),
                ],
              ],
            ),
          ),
          
          // Messages list
          Expanded(
            child: messages.isEmpty
                ? const Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.chat_bubble_outline, size: 64, color: Colors.grey),
                        SizedBox(height: 16),
                        Text(
                          'Start a conversation with enhanced Pegasus Chat',
                          style: TextStyle(color: Colors.grey, fontSize: 16),
                          textAlign: TextAlign.center,
                        ),
                        SizedBox(height: 8),
                        Text(
                          'Features: Context awareness, citations, multiple response styles',
                          style: TextStyle(color: Colors.grey, fontSize: 12),
                          textAlign: TextAlign.center,
                        ),
                      ],
                    ),
                  )
                : ListView.builder(
                    controller: _scrollController,
                    padding: const EdgeInsets.all(16),
                    itemCount: messages.length,
                    itemBuilder: (context, index) {
                      final message = messages[index];
                      return Padding(
                        padding: const EdgeInsets.only(bottom: 8),
                        child: MessageBubble(
                          text: message.text,
                          isUser: message.isUser,
                        ),
                      );
                    },
                  ),
          ),
          
          // Message composer
          MessageComposer(
            onSend: _sendMessage,
            enabled: !_isLoading,
          ),
        ],
      ),
    );
  }
}