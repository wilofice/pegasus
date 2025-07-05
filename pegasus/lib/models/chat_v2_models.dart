/// Enhanced Chat V2 models for advanced conversation features
/// 
/// These models support the advanced Chat V2 API with context awareness,
/// citations, sources, and intelligent conversation management.

import 'api_enums.dart';

/// Request model for Chat V2 endpoint
class ChatRequestV2 {
  final String message;
  final String? sessionId;
  final String? userId;
  final ConversationMode? conversationMode;
  final ResponseStyle? responseStyle;
  final AggregationStrategy? aggregationStrategy;
  final RankingStrategy? rankingStrategy;
  final int? maxContextResults;
  final bool? includeSources;
  final bool? includeConfidence;
  final bool? enablePlugins;
  final bool? useLocalLlm;

  const ChatRequestV2({
    required this.message,
    this.sessionId,
    this.userId,
    this.conversationMode,
    this.responseStyle,
    this.aggregationStrategy,
    this.rankingStrategy,
    this.maxContextResults,
    this.includeSources,
    this.includeConfidence,
    this.enablePlugins,
    this.useLocalLlm,
  });

  /// Convert to JSON for API request
  Map<String, dynamic> toJson() {
    final json = <String, dynamic>{
      'message': message,
    };

    if (sessionId != null) json['session_id'] = sessionId;
    if (userId != null) json['user_id'] = userId;
    if (conversationMode != null) json['conversation_mode'] = conversationMode!.value;
    if (responseStyle != null) json['response_style'] = responseStyle!.value;
    if (aggregationStrategy != null) json['aggregation_strategy'] = aggregationStrategy!.value;
    if (rankingStrategy != null) json['ranking_strategy'] = rankingStrategy!.value;
    if (maxContextResults != null) json['max_context_results'] = maxContextResults;
    if (includeSources != null) json['include_sources'] = includeSources;
    if (includeConfidence != null) json['include_confidence'] = includeConfidence;
    if (enablePlugins != null) json['enable_plugins'] = enablePlugins;
    if (useLocalLlm != null) json['use_local_llm'] = useLocalLlm;

    return json;
  }

  /// Create a copy with updated fields
  ChatRequestV2 copyWith({
    String? message,
    String? sessionId,
    String? userId,
    ConversationMode? conversationMode,
    ResponseStyle? responseStyle,
    AggregationStrategy? aggregationStrategy,
    RankingStrategy? rankingStrategy,
    int? maxContextResults,
    bool? includeSources,
    bool? includeConfidence,
    bool? enablePlugins,
    bool? useLocalLlm,
  }) {
    return ChatRequestV2(
      message: message ?? this.message,
      sessionId: sessionId ?? this.sessionId,
      userId: userId ?? this.userId,
      conversationMode: conversationMode ?? this.conversationMode,
      responseStyle: responseStyle ?? this.responseStyle,
      aggregationStrategy: aggregationStrategy ?? this.aggregationStrategy,
      rankingStrategy: rankingStrategy ?? this.rankingStrategy,
      maxContextResults: maxContextResults ?? this.maxContextResults,
      includeSources: includeSources ?? this.includeSources,
      includeConfidence: includeConfidence ?? this.includeConfidence,
      enablePlugins: enablePlugins ?? this.enablePlugins,
      useLocalLlm: useLocalLlm ?? this.useLocalLlm,
    );
  }
}

/// Response model for Chat V2 endpoint
class ChatResponseV2 {
  final String response;
  final String sessionId;
  final String conversationMode;
  final String responseStyle;
  final double processingTimeMs;
  final int contextResultsCount;
  final double? confidenceScore;
  final List<SourceInfo>? sources;
  final List<String>? suggestions;
  final Map<String, dynamic>? metrics;

  const ChatResponseV2({
    required this.response,
    required this.sessionId,
    required this.conversationMode,
    required this.responseStyle,
    required this.processingTimeMs,
    required this.contextResultsCount,
    this.confidenceScore,
    this.sources,
    this.suggestions,
    this.metrics,
  });

  /// Create from JSON response
  factory ChatResponseV2.fromJson(Map<String, dynamic> json) {
    return ChatResponseV2(
      response: json['response'] as String,
      sessionId: json['session_id'] as String,
      conversationMode: json['conversation_mode'] as String,
      responseStyle: json['response_style'] as String,
      processingTimeMs: (json['processing_time_ms'] as num).toDouble(),
      contextResultsCount: json['context_results_count'] as int,
      confidenceScore: json['confidence_score'] != null 
          ? (json['confidence_score'] as num).toDouble() 
          : null,
      sources: json['sources'] != null
          ? (json['sources'] as List<dynamic>)
              .map((source) => SourceInfo.fromJson(source as Map<String, dynamic>))
              .toList()
          : null,
      suggestions: json['suggestions'] != null
          ? List<String>.from(json['suggestions'] as List<dynamic>)
          : null,
      metrics: json['metrics'] as Map<String, dynamic>?,
    );
  }

  /// Check if response has sources
  bool get hasSources => sources != null && sources!.isNotEmpty;

  /// Check if response has suggestions
  bool get hasSuggestions => suggestions != null && suggestions!.isNotEmpty;

  /// Check if response has high confidence
  bool get hasHighConfidence => confidenceScore != null && confidenceScore! >= 0.8;

  /// Get processing time in seconds
  double get processingTimeSeconds => processingTimeMs / 1000.0;
}

/// Source information for chat responses
class SourceInfo {
  final String id;
  final String content;
  final String sourceType;
  final double relevanceScore;
  final Map<String, dynamic> metadata;
  final String? audioId;
  final String? timestamp;
  final String? position;

  const SourceInfo({
    required this.id,
    required this.content,
    required this.sourceType,
    required this.relevanceScore,
    required this.metadata,
    this.audioId,
    this.timestamp,
    this.position,
  });

  /// Create from JSON
  factory SourceInfo.fromJson(Map<String, dynamic> json) {
    return SourceInfo(
      id: json['id'] as String,
      content: json['content'] as String,
      sourceType: json['source_type'] as String,
      relevanceScore: (json['relevance_score'] as num).toDouble(),
      metadata: json['metadata'] as Map<String, dynamic>,
      audioId: json['audio_id'] as String?,
      timestamp: json['timestamp'] as String?,
      position: json['position'] as String?,
    );
  }

  /// Get formatted timestamp if available
  String? get formattedTimestamp {
    if (timestamp == null) return null;
    try {
      final dateTime = DateTime.parse(timestamp!);
      return '${dateTime.day}/${dateTime.month}/${dateTime.year}';
    } catch (e) {
      return timestamp;
    }
  }

  /// Get preview content (truncated)
  String get previewContent {
    if (content.length <= 100) return content;
    return '${content.substring(0, 97)}...';
  }

  /// Get source type display name
  String get sourceTypeDisplayName {
    switch (sourceType.toLowerCase()) {
      case 'vector':
        return 'Semantic Match';
      case 'graph':
        return 'Knowledge Graph';
      case 'hybrid':
        return 'Combined Search';
      case 'ensemble':
        return 'Advanced Analysis';
      default:
        return sourceType;
    }
  }

  /// Get relevance percentage
  int get relevancePercentage => (relevanceScore * 100).round();
}

/// Session information for conversation management
class SessionInfo {
  final String sessionId;
  final String? userId;
  final DateTime createdAt;
  final DateTime lastUpdated;
  final int conversationTurns;
  final Map<String, dynamic> metadata;

  const SessionInfo({
    required this.sessionId,
    this.userId,
    required this.createdAt,
    required this.lastUpdated,
    required this.conversationTurns,
    required this.metadata,
  });

  /// Create from JSON
  factory SessionInfo.fromJson(Map<String, dynamic> json) {
    return SessionInfo(
      sessionId: json['session_id'] as String,
      userId: json['user_id'] as String?,
      createdAt: DateTime.parse(json['created_at'] as String),
      lastUpdated: DateTime.parse(json['last_updated'] as String),
      conversationTurns: json['conversation_turns'] as int,
      metadata: json['metadata'] as Map<String, dynamic>,
    );
  }

  /// Get session duration
  Duration get duration => lastUpdated.difference(createdAt);

  /// Get formatted duration
  String get formattedDuration {
    final duration = this.duration;
    if (duration.inHours > 0) {
      return '${duration.inHours}h ${duration.inMinutes.remainder(60)}m';
    } else if (duration.inMinutes > 0) {
      return '${duration.inMinutes}m ${duration.inSeconds.remainder(60)}s';
    } else {
      return '${duration.inSeconds}s';
    }
  }

  /// Check if session is recent (within last hour)
  bool get isRecent => DateTime.now().difference(lastUpdated).inHours < 1;
}

/// Health response for Chat V2 service
class ChatHealthResponse {
  final String service;
  final String status;
  final Map<String, dynamic> dependencies;
  final Map<String, dynamic> sessions;

  const ChatHealthResponse({
    required this.service,
    required this.status,
    required this.dependencies,
    required this.sessions,
  });

  /// Create from JSON
  factory ChatHealthResponse.fromJson(Map<String, dynamic> json) {
    return ChatHealthResponse(
      service: json['service'] as String,
      status: json['status'] as String,
      dependencies: json['dependencies'] as Map<String, dynamic>,
      sessions: json['sessions'] as Map<String, dynamic>,
    );
  }

  /// Check if service is healthy
  bool get isHealthy => status.toLowerCase() == 'healthy';

  /// Get active sessions count
  int get activeSessionsCount {
    return sessions['active_count'] as int? ?? 0;
  }
}