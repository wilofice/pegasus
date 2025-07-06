/// API enums for enhanced Pegasus backend integration
/// 
/// This file contains all the enums used across the API models
/// to ensure type safety and consistency with the backend.

/// Conversation modes for Chat V2 API
enum ConversationMode {
  standard('standard'),
  creative('creative'),
  analytical('analytical'),
  concise('concise');

  const ConversationMode(this.value);
  final String value;

  static ConversationMode fromString(String value) {
    return ConversationMode.values.firstWhere(
      (mode) => mode.value == value,
      orElse: () => ConversationMode.standard,
    );
  }
}

/// Response styles for Chat V2 API
enum ResponseStyle {
  concise('concise'),
  detailed('detailed'),
  academic('academic'),
  casual('casual'),
  professional('professional');

  const ResponseStyle(this.value);
  final String value;

  static ResponseStyle fromString(String value) {
    return ResponseStyle.values.firstWhere(
      (style) => style.value == value,
      orElse: () => ResponseStyle.professional,
    );
  }
}

/// Aggregation strategies for context search
enum AggregationStrategy {
  vector('vector'),
  graph('graph'),
  hybrid('hybrid'),
  ensemble('ensemble');

  const AggregationStrategy(this.value);
  final String value;

  static AggregationStrategy fromString(String value) {
    return AggregationStrategy.values.firstWhere(
      (strategy) => strategy.value == value,
      orElse: () => AggregationStrategy.hybrid,
    );
  }
}

/// Ranking strategies for context search
enum RankingStrategy {
  relevance('relevance'),
  temporal('temporal'),
  hybrid('hybrid'),
  ensemble('ensemble');

  const RankingStrategy(this.value);
  final String value;

  static RankingStrategy fromString(String value) {
    return RankingStrategy.values.firstWhere(
      (strategy) => strategy.value == value,
      orElse: () => RankingStrategy.ensemble,
    );
  }
}

/// Search strategies for context search
enum SearchStrategy {
  vector('vector'),
  graph('graph'),
  hybrid('hybrid'),
  ensemble('ensemble');

  const SearchStrategy(this.value);
  final String value;

  static SearchStrategy fromString(String value) {
    return SearchStrategy.values.firstWhere(
      (strategy) => strategy.value == value,
      orElse: () => SearchStrategy.hybrid,
    );
  }
}

/// Processing status for audio files
enum ProcessingStatus {
  uploaded('uploaded'),
  transcribing('transcribing'),
  pendingReview('pending_review'),
  pendingProcessing('pending_processing'),
  improving('improving'),
  completed('completed'),
  failed('failed');

  const ProcessingStatus(this.value);
  final String value;

  static ProcessingStatus fromString(String value) {
    return ProcessingStatus.values.firstWhere(
      (status) => status.value == value,
      orElse: () => ProcessingStatus.uploaded,
    );
  }

  /// Get user-friendly display name
  String get displayName {
    switch (this) {
      case ProcessingStatus.uploaded:
        return 'Uploaded';
      case ProcessingStatus.transcribing:
        return 'Transcribing';
      case ProcessingStatus.pendingReview:
        return 'Pending Review';
      case ProcessingStatus.pendingProcessing:
        return 'Pending Processing';
      case ProcessingStatus.improving:
        return 'Improving';
      case ProcessingStatus.completed:
        return 'Completed';
      case ProcessingStatus.failed:
        return 'Failed';
    }
  }

  /// Get color for UI display
  String get colorHex {
    switch (this) {
      case ProcessingStatus.uploaded:
        return '#FFA726'; // Orange
      case ProcessingStatus.transcribing:
        return '#42A5F5'; // Blue
      case ProcessingStatus.pendingReview:
        return '#FF9800'; // Amber - waiting for user action
      case ProcessingStatus.pendingProcessing:
        return '#9C27B0'; // Purple - waiting for processing
      case ProcessingStatus.improving:
        return '#66BB6A'; // Green
      case ProcessingStatus.completed:
        return '#4CAF50'; // Success Green
      case ProcessingStatus.failed:
        return '#F44336'; // Red
    }
  }

  /// Check if processing is still in progress
  bool get isInProgress {
    return this == ProcessingStatus.uploaded ||
           this == ProcessingStatus.transcribing ||
           this == ProcessingStatus.pendingReview ||
           this == ProcessingStatus.pendingProcessing ||
           this == ProcessingStatus.improving;
  }

  /// Check if processing is completed successfully
  bool get isCompleted {
    return this == ProcessingStatus.completed;
  }

  /// Check if processing has failed
  bool get isFailed {
    return this == ProcessingStatus.failed;
  }
}

/// Question types for game API
enum QuestionType {
  singleChoice('SINGLE_CHOICE'),
  multipleChoice('MULTIPLE_CHOICE'),
  freeText('FREE_TEXT');

  const QuestionType(this.value);
  final String value;

  static QuestionType fromString(String value) {
    return QuestionType.values.firstWhere(
      (type) => type.value == value,
      orElse: () => QuestionType.singleChoice,
    );
  }

  /// Get user-friendly display name
  String get displayName {
    switch (this) {
      case QuestionType.singleChoice:
        return 'Single Choice';
      case QuestionType.multipleChoice:
        return 'Multiple Choice';
      case QuestionType.freeText:
        return 'Free Text';
    }
  }
}

/// Plugin status for plugin management
enum PluginStatus {
  enabled('enabled'),
  disabled('disabled'),
  error('error'),
  loading('loading');

  const PluginStatus(this.value);
  final String value;

  static PluginStatus fromString(String value) {
    return PluginStatus.values.firstWhere(
      (status) => status.value == value,
      orElse: () => PluginStatus.disabled,
    );
  }

  /// Get user-friendly display name
  String get displayName {
    switch (this) {
      case PluginStatus.enabled:
        return 'Enabled';
      case PluginStatus.disabled:
        return 'Disabled';
      case PluginStatus.error:
        return 'Error';
      case PluginStatus.loading:
        return 'Loading';
    }
  }

  /// Get color for UI display
  String get colorHex {
    switch (this) {
      case PluginStatus.enabled:
        return '#4CAF50'; // Green
      case PluginStatus.disabled:
        return '#9E9E9E'; // Grey
      case PluginStatus.error:
        return '#F44336'; // Red
      case PluginStatus.loading:
        return '#FF9800'; // Orange
    }
  }
}

/// Plugin types for categorization
enum PluginType {
  analysis('analysis'),
  processing('processing'),
  notification('notification'),
  export('export'),
  integration('integration');

  const PluginType(this.value);
  final String value;

  static PluginType fromString(String value) {
    return PluginType.values.firstWhere(
      (type) => type.value == value,
      orElse: () => PluginType.analysis,
    );
  }

  /// Get user-friendly display name
  String get displayName {
    switch (this) {
      case PluginType.analysis:
        return 'Analysis';
      case PluginType.processing:
        return 'Processing';
      case PluginType.notification:
        return 'Notification';
      case PluginType.export:
        return 'Export';
      case PluginType.integration:
        return 'Integration';
    }
  }

  /// Get icon for UI display
  String get iconName {
    switch (this) {
      case PluginType.analysis:
        return 'analytics';
      case PluginType.processing:
        return 'settings';
      case PluginType.notification:
        return 'notifications';
      case PluginType.export:
        return 'download';
      case PluginType.integration:
        return 'link';
    }
  }
}