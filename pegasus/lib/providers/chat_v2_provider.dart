/// Chat V2 Provider for enhanced chat functionality
/// 
/// This provider manages the state for Chat V2 features including:
/// - Enhanced message models with sources and suggestions
/// - Session management
/// - Conversation settings
/// - Real-time response tracking

import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/chat_v2_models.dart';
import '../models/api_enums.dart';
import '../api/pegasus_api_client_v2.dart';

/// Enhanced message model for Chat V2
class EnhancedMessage {
  final String id;
  final String text;
  final bool isUser;
  final DateTime timestamp;
  final List<SourceInfo>? sources;
  final List<String>? suggestions;
  final double? confidenceScore;
  final double? processingTimeMs;
  final String? sessionId;

  const EnhancedMessage({
    required this.id,
    required this.text,
    required this.isUser,
    required this.timestamp,
    this.sources,
    this.suggestions,
    this.confidenceScore,
    this.processingTimeMs,
    this.sessionId,
  });

  /// Check if message has sources
  bool get hasSources => sources != null && sources!.isNotEmpty;

  /// Check if message has suggestions
  bool get hasSuggestions => suggestions != null && suggestions!.isNotEmpty;

  /// Check if message has high confidence
  bool get hasHighConfidence => confidenceScore != null && confidenceScore! >= 0.8;

  /// Get display timestamp
  String get displayTime {
    final now = DateTime.now();
    final diff = now.difference(timestamp);
    
    if (diff.inMinutes < 1) return 'Just now';
    if (diff.inHours < 1) return '${diff.inMinutes}m ago';
    if (diff.inDays < 1) return '${diff.inHours}h ago';
    return '${diff.inDays}d ago';
  }

  /// Create from Chat V2 response
  factory EnhancedMessage.fromChatResponse(
    ChatResponseV2 response,
    String messageId,
  ) {
    return EnhancedMessage(
      id: messageId,
      text: response.response,
      isUser: false,
      timestamp: DateTime.now(),
      sources: response.sources,
      suggestions: response.suggestions,
      confidenceScore: response.confidenceScore,
      processingTimeMs: response.processingTimeMs,
      sessionId: response.sessionId,
    );
  }

  /// Create user message
  factory EnhancedMessage.userMessage(String text, String messageId) {
    return EnhancedMessage(
      id: messageId,
      text: text,
      isUser: true,
      timestamp: DateTime.now(),
    );
  }
}

/// Chat V2 conversation state
class ChatV2State {
  final List<EnhancedMessage> messages;
  final String? currentSessionId;
  final ConversationMode conversationMode;
  final ResponseStyle responseStyle;
  final bool includeSources;
  final bool enablePlugins;
  final bool isLoading;
  final String? error;

  const ChatV2State({
    this.messages = const [],
    this.currentSessionId,
    this.conversationMode = ConversationMode.standard,
    this.responseStyle = ResponseStyle.professional,
    this.includeSources = true,
    this.enablePlugins = true,
    this.isLoading = false,
    this.error,
  });

  /// Copy with updated fields
  ChatV2State copyWith({
    List<EnhancedMessage>? messages,
    String? currentSessionId,
    ConversationMode? conversationMode,
    ResponseStyle? responseStyle,
    bool? includeSources,
    bool? enablePlugins,
    bool? isLoading,
    String? error,
  }) {
    return ChatV2State(
      messages: messages ?? this.messages,
      currentSessionId: currentSessionId ?? this.currentSessionId,
      conversationMode: conversationMode ?? this.conversationMode,
      responseStyle: responseStyle ?? this.responseStyle,
      includeSources: includeSources ?? this.includeSources,
      enablePlugins: enablePlugins ?? this.enablePlugins,
      isLoading: isLoading ?? this.isLoading,
      error: error,
    );
  }

  /// Check if there are messages
  bool get hasMessages => messages.isNotEmpty;

  /// Get the last message
  EnhancedMessage? get lastMessage => messages.isNotEmpty ? messages.last : null;

  /// Get messages with sources
  List<EnhancedMessage> get messagesWithSources => 
      messages.where((m) => m.hasSources).toList();

  /// Get average confidence score
  double get averageConfidence {
    final confidenceScores = messages
        .where((m) => !m.isUser && m.confidenceScore != null)
        .map((m) => m.confidenceScore!)
        .toList();
    
    if (confidenceScores.isEmpty) return 0.0;
    return confidenceScores.reduce((a, b) => a + b) / confidenceScores.length;
  }
}

/// Chat V2 State Notifier
class ChatV2Notifier extends StateNotifier<ChatV2State> {
  ChatV2Notifier() : super(const ChatV2State());

  /// Add a new message
  void addMessage(EnhancedMessage message) {
    state = state.copyWith(
      messages: [...state.messages, message],
      currentSessionId: message.sessionId ?? state.currentSessionId,
      error: null,
    );
  }

  /// Clear all messages and reset session
  void clear() {
    state = const ChatV2State();
  }

  /// Update conversation settings
  void updateSettings({
    ConversationMode? conversationMode,
    ResponseStyle? responseStyle,
    bool? includeSources,
    bool? enablePlugins,
  }) {
    state = state.copyWith(
      conversationMode: conversationMode,
      responseStyle: responseStyle,
      includeSources: includeSources,
      enablePlugins: enablePlugins,
    );
  }

  /// Set loading state
  void setLoading(bool loading) {
    state = state.copyWith(isLoading: loading, error: null);
  }

  /// Set error state
  void setError(String error) {
    state = state.copyWith(error: error, isLoading: false);
  }

  /// Update session ID
  void setSessionId(String sessionId) {
    state = state.copyWith(currentSessionId: sessionId);
  }

  /// Remove a message by ID
  void removeMessage(String messageId) {
    state = state.copyWith(
      messages: state.messages.where((m) => m.id != messageId).toList(),
    );
  }

  /// Get messages in date range
  List<EnhancedMessage> getMessagesInRange(DateTime start, DateTime end) {
    return state.messages
        .where((m) => m.timestamp.isAfter(start) && m.timestamp.isBefore(end))
        .toList();
  }

  /// Get messages by session ID
  List<EnhancedMessage> getMessagesBySession(String sessionId) {
    return state.messages
        .where((m) => m.sessionId == sessionId)
        .toList();
  }

  /// Export conversation as text
  String exportConversation() {
    final buffer = StringBuffer();
    buffer.writeln('Pegasus Chat Conversation Export');
    buffer.writeln('Generated: ${DateTime.now()}');
    if (state.currentSessionId != null) {
      buffer.writeln('Session ID: ${state.currentSessionId}');
    }
    buffer.writeln('Settings: ${state.conversationMode.value} mode, ${state.responseStyle.value} style');
    buffer.writeln('Messages: ${state.messages.length}');
    buffer.writeln('=' * 50);
    buffer.writeln();

    for (final message in state.messages) {
      final sender = message.isUser ? 'User' : 'Pegasus';
      buffer.writeln('[$sender] ${message.displayTime}');
      buffer.writeln(message.text);
      
      if (message.hasSources) {
        buffer.writeln('Sources:');
        for (final source in message.sources!) {
          buffer.writeln('  - ${source.sourceTypeDisplayName}: ${source.previewContent}');
        }
      }
      
      if (message.hasSuggestions) {
        buffer.writeln('Suggestions:');
        for (final suggestion in message.suggestions!) {
          buffer.writeln('  - $suggestion');
        }
      }
      
      buffer.writeln();
    }

    return buffer.toString();
  }
}

/// Chat V2 Provider
final chatV2Provider = StateNotifierProvider<ChatV2Notifier, ChatV2State>((ref) {
  return ChatV2Notifier();
});

/// API Client Provider
final apiClientV2Provider = Provider<PegasusApiClientV2>((ref) {
  return PegasusApiClientV2.defaultConfig();
});

/// Current session provider
final currentSessionProvider = Provider<String?>((ref) {
  return ref.watch(chatV2Provider).currentSessionId;
});

/// Loading state provider
final isLoadingProvider = Provider<bool>((ref) {
  return ref.watch(chatV2Provider).isLoading;
});

/// Error state provider
final errorProvider = Provider<String?>((ref) {
  return ref.watch(chatV2Provider).error;
});

/// Messages count provider
final messagesCountProvider = Provider<int>((ref) {
  return ref.watch(chatV2Provider).messages.length;
});

/// Average confidence provider
final averageConfidenceProvider = Provider<double>((ref) {
  return ref.watch(chatV2Provider).averageConfidence;
});

/// Messages with sources provider
final messagesWithSourcesProvider = Provider<List<EnhancedMessage>>((ref) {
  return ref.watch(chatV2Provider).messagesWithSources;
});

/// Current settings provider
final chatSettingsProvider = Provider<Map<String, dynamic>>((ref) {
  final state = ref.watch(chatV2Provider);
  return {
    'conversationMode': state.conversationMode.value,
    'responseStyle': state.responseStyle.value,
    'includeSources': state.includeSources,
    'enablePlugins': state.enablePlugins,
  };
});