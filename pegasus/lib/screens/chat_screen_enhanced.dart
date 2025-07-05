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
import '../widgets/enhanced_message_bubble.dart';
import '../widgets/context_search_panel.dart';
import '../widgets/suggestion_chips.dart';
import '../widgets/citation_card.dart';
import '../models/api_enums.dart';
import '../models/chat_v2_models.dart';
import '../models/context_search_models.dart';
import '../providers/chat_v2_provider.dart';
import '../api/pegasus_api_client_v2.dart';

/// Enhanced chat screen with Chat V2 features
class ChatScreenEnhanced extends ConsumerStatefulWidget {
  const ChatScreenEnhanced({super.key});

  @override
  ConsumerState<ChatScreenEnhanced> createState() => _ChatScreenEnhancedState();
}

class _ChatScreenEnhancedState extends ConsumerState<ChatScreenEnhanced> {
  late final ScrollController _scrollController;
  late final TextEditingController _messageController;
  late final FocusNode _messageFocusNode;
  
  bool _showContextSearch = false;
  bool _showSettings = false;

  @override
  void initState() {
    super.initState();
    _scrollController = ScrollController();
    _messageController = TextEditingController();
    _messageFocusNode = FocusNode();
  }

  @override
  void dispose() {
    _scrollController.dispose();
    _messageController.dispose();
    _messageFocusNode.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final chatState = ref.watch(chatV2Provider);
    
    return Scaffold(
      appBar: _buildAppBar(chatState),
      body: Column(
        children: [
          if (_showSettings) _buildSettingsPanel(chatState),
          if (_showContextSearch) 
            Expanded(
              flex: 2,
              child: ContextSearchPanel(
                showInline: true,
                onResultSelected: _handleContextResult,
              ),
            ),
          Expanded(
            flex: _showContextSearch ? 3 : 1,
            child: _buildMessagesList(chatState),
          ),
          _buildInputArea(chatState),
        ],
      ),
    );
  }

  PreferredSizeWidget _buildAppBar(ChatV2State chatState) {
    return AppBar(
      title: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Enhanced Chat'),
          if (chatState.currentSessionId != null)
            Text(
              'Session: ${chatState.currentSessionId!.substring(0, 8)}...',
              style: const TextStyle(fontSize: 12, fontWeight: FontWeight.normal),
            ),
        ],
      ),
      actions: [
        IconButton(
          icon: Icon(
            _showContextSearch ? Icons.search : Icons.search_outlined,
            color: _showContextSearch ? Theme.of(context).primaryColor : null,
          ),
          onPressed: () => setState(() => _showContextSearch = !_showContextSearch),
          tooltip: 'Context Search',
        ),
        IconButton(
          icon: Icon(
            _showSettings ? Icons.settings : Icons.settings_outlined,
            color: _showSettings ? Theme.of(context).primaryColor : null,
          ),
          onPressed: () => setState(() => _showSettings = !_showSettings),
          tooltip: 'Chat Settings',
        ),
        PopupMenuButton<String>(
          onSelected: _handleMenuAction,
          itemBuilder: (context) => [
            const PopupMenuItem(
              value: 'clear',
              child: Row(
                children: [
                  Icon(Icons.clear_all),
                  SizedBox(width: 8),
                  Text('Clear Chat'),
                ],
              ),
            ),
            const PopupMenuItem(
              value: 'export',
              child: Row(
                children: [
                  Icon(Icons.download),
                  SizedBox(width: 8),
                  Text('Export'),
                ],
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildSettingsPanel(ChatV2State chatState) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.grey.shade50,
        border: Border(bottom: BorderSide(color: Colors.grey.shade200)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.settings, size: 18),
              const SizedBox(width: 8),
              const Text(
                'Conversation Settings',
                style: TextStyle(fontWeight: FontWeight.w600),
              ),
              const Spacer(),
              TextButton(
                onPressed: () => setState(() => _showSettings = false),
                child: const Text('Done'),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('Mode', style: TextStyle(fontWeight: FontWeight.w500)),
                    DropdownButton<ConversationMode>(
                      value: chatState.conversationMode,
                      isExpanded: true,
                      onChanged: (mode) => ref.read(chatV2Provider.notifier)
                          .updateSettings(conversationMode: mode),
                      items: ConversationMode.values.map((mode) =>
                        DropdownMenuItem(
                          value: mode,
                          child: Text(mode.value),
                        ),
                      ).toList(),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('Style', style: TextStyle(fontWeight: FontWeight.w500)),
                    DropdownButton<ResponseStyle>(
                      value: chatState.responseStyle,
                      isExpanded: true,
                      onChanged: (style) => ref.read(chatV2Provider.notifier)
                          .updateSettings(responseStyle: style),
                      items: ResponseStyle.values.map((style) =>
                        DropdownMenuItem(
                          value: style,
                          child: Text(style.value),
                        ),
                      ).toList(),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: CheckboxListTile(
                  title: const Text('Include Sources'),
                  value: chatState.includeSources,
                  onChanged: (value) => ref.read(chatV2Provider.notifier)
                      .updateSettings(includeSources: value),
                  contentPadding: EdgeInsets.zero,
                ),
              ),
              Expanded(
                child: CheckboxListTile(
                  title: const Text('Enable Plugins'),
                  value: chatState.enablePlugins,
                  onChanged: (value) => ref.read(chatV2Provider.notifier)
                      .updateSettings(enablePlugins: value),
                  contentPadding: EdgeInsets.zero,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildMessagesList(ChatV2State chatState) {
    if (chatState.messages.isEmpty) {
      return _buildEmptyState();
    }

    return ListView.builder(
      controller: _scrollController,
      padding: const EdgeInsets.symmetric(vertical: 8),
      itemCount: chatState.messages.length,
      itemBuilder: (context, index) {
        final message = chatState.messages[index];
        return EnhancedMessageBubble(
          message: message,
          onCitationTap: () => _showSourceDetails(message),
          onSourceTap: () => _showAllSources(message),
        );
      },
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.chat_bubble_outline,
            size: 64,
            color: Colors.grey.shade400,
          ),
          const SizedBox(height: 16),
          Text(
            'Start a conversation',
            style: TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.w500,
              color: Colors.grey.shade600,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'Ask questions and get responses with\ncitations from your documents',
            textAlign: TextAlign.center,
            style: TextStyle(
              fontSize: 14,
              color: Colors.grey.shade500,
            ),
          ),
          const SizedBox(height: 24),
          SuggestionChips(
            suggestions: [
              SuggestionChipData(
                text: "What's in my latest meeting notes?",
                category: SuggestionCategory.followUp,
                onTap: () => _sendMessage("What's in my latest meeting notes?"),
              ),
              SuggestionChipData(
                text: "Summarize recent project updates",
                category: SuggestionCategory.action,
                onTap: () => _sendMessage("Summarize recent project updates"),
              ),
              SuggestionChipData(
                text: "Find information about...",
                category: SuggestionCategory.related,
                onTap: () => setState(() => _showContextSearch = true),
              ),
            ],
            onSuggestionTap: (suggestion) => _sendMessage(suggestion.text),
          ),
        ],
      ),
    );
  }

  Widget _buildInputArea(ChatV2State chatState) {
    return Container(
      padding: EdgeInsets.only(
        left: 16,
        right: 16,
        top: 8,
        bottom: MediaQuery.of(context).viewInsets.bottom + 16,
      ),
      decoration: BoxDecoration(
        color: Colors.white,
        border: Border(top: BorderSide(color: Colors.grey.shade200)),
      ),
      child: Column(
        children: [
          if (!_showContextSearch)
            QuickContextSearch(
              onQuerySelected: (query) => _sendMessage(query),
            ),
          Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _messageController,
                  focusNode: _messageFocusNode,
                  decoration: InputDecoration(
                    hintText: 'Ask me anything...',
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(24),
                      borderSide: BorderSide(color: Colors.grey.shade300),
                    ),
                    enabledBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(24),
                      borderSide: BorderSide(color: Colors.grey.shade300),
                    ),
                    focusedBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(24),
                      borderSide: BorderSide(color: Theme.of(context).primaryColor),
                    ),
                    contentPadding: const EdgeInsets.symmetric(
                      horizontal: 20,
                      vertical: 12,
                    ),
                    suffixIcon: chatState.isLoading
                        ? const Padding(
                            padding: EdgeInsets.all(12),
                            child: SizedBox(
                              width: 20,
                              height: 20,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            ),
                          )
                        : null,
                  ),
                  maxLines: null,
                  textInputAction: TextInputAction.send,
                  onSubmitted: chatState.isLoading ? null : _handleSubmit,
                ),
              ),
              const SizedBox(width: 8),
              FloatingActionButton(
                mini: true,
                onPressed: chatState.isLoading ? null : () => _handleSubmit(_messageController.text),
                child: const Icon(Icons.send),
              ),
            ],
          ),
        ],
      ),
    );
  }

  void _handleSubmit(String text) {
    if (text.trim().isEmpty) return;
    _sendMessage(text.trim());
  }

  Future<void> _sendMessage(String text) async {
    if (text.isEmpty) return;
    
    _messageController.clear();
    final messageId = DateTime.now().millisecondsSinceEpoch.toString();
    
    // Add user message
    final userMessage = EnhancedMessage.userMessage(text, messageId);
    ref.read(chatV2Provider.notifier).addMessage(userMessage);
    
    // Scroll to bottom
    _scrollToBottom();
    
    // Set loading state
    ref.read(chatV2Provider.notifier).setLoading(true);
    
    try {
      final apiClient = ref.read(apiClientV2Provider);
      final chatState = ref.read(chatV2Provider);
      
      final request = ChatRequestV2(
        message: text,
        sessionId: chatState.currentSessionId,
        conversationMode: chatState.conversationMode,
        responseStyle: chatState.responseStyle,
        includeSources: chatState.includeSources,
        enablePlugins: chatState.enablePlugins,
      );
      
      final response = await apiClient.chatV2(request);
      
      // Create AI response message
      final aiMessageId = '${DateTime.now().millisecondsSinceEpoch}_ai';
      final aiMessage = EnhancedMessage.fromChatResponse(response, aiMessageId);
      
      ref.read(chatV2Provider.notifier).addMessage(aiMessage);
      
      // Update session ID if provided
      if (response.sessionId != null) {
        ref.read(chatV2Provider.notifier).setSessionId(response.sessionId!);
      }
      
    } catch (e) {
      ref.read(chatV2Provider.notifier).setError('Failed to send message: $e');
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Error: $e'),
          backgroundColor: Colors.red,
        ),
      );
    } finally {
      ref.read(chatV2Provider.notifier).setLoading(false);
      _scrollToBottom();
    }
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

  void _handleContextResult(ContextSearchResult result) {
    final query = 'Tell me more about: ${result.summary}';
    _sendMessage(query);
  }

  void _showSourceDetails(EnhancedMessage message) {
    if (!message.hasSources) return;
    
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (context) => Container(
        height: MediaQuery.of(context).size.height * 0.7,
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Sources (${message.sources!.length})',
              style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 16),
            Expanded(
              child: ListView.builder(
                itemCount: message.sources!.length,
                itemBuilder: (context, index) {
                  return Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: CitationCard(
                      source: message.sources![index],
                      showMetadata: true,
                    ),
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }

  void _showAllSources(EnhancedMessage message) {
    _showSourceDetails(message);
  }

  void _handleMenuAction(String action) {
    switch (action) {
      case 'clear':
        _showClearDialog();
        break;
      case 'export':
        _exportConversation();
        break;
    }
  }

  void _showClearDialog() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Clear Chat'),
        content: const Text('This will delete all messages in the current conversation. Are you sure?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () {
              ref.read(chatV2Provider.notifier).clear();
              Navigator.of(context).pop();
            },
            child: const Text('Clear'),
          ),
        ],
      ),
    );
  }

  void _exportConversation() {
    final conversation = ref.read(chatV2Provider.notifier).exportConversation();
    
    // In a real app, this would save to file or share
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('Exported ${ref.read(chatV2Provider).messages.length} messages'),
        action: SnackBarAction(
          label: 'Preview',
          onPressed: () => _showExportPreview(conversation),
        ),
      ),
    );
  }

  void _showExportPreview(String conversation) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Export Preview'),
        content: Container(
          width: double.maxFinite,
          height: 400,
          child: SingleChildScrollView(
            child: Text(
              conversation,
              style: const TextStyle(fontFamily: 'monospace', fontSize: 12),
            ),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Close'),
          ),
        ],
      ),
    );
  }
}