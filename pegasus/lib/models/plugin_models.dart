/// Plugin API models for plugin system integration
/// 
/// These models support the plugin system API for managing and executing
/// plugins, viewing results, and monitoring plugin performance.

import 'api_enums.dart';

/// Plugin information model
class PluginInfo {
  final String name;
  final String version;
  final String description;
  final String author;
  final PluginType type;
  final PluginStatus status;
  final List<String> dependencies;
  final List<String> tags;
  final Map<String, dynamic> config;
  final String? lastError;
  final DateTime createdAt;
  final DateTime updatedAt;

  const PluginInfo({
    required this.name,
    required this.version,
    required this.description,
    required this.author,
    required this.type,
    required this.status,
    required this.dependencies,
    required this.tags,
    required this.config,
    this.lastError,
    required this.createdAt,
    required this.updatedAt,
  });

  /// Create from JSON
  factory PluginInfo.fromJson(Map<String, dynamic> json) {
    return PluginInfo(
      name: json['name'] as String,
      version: json['version'] as String,
      description: json['description'] as String,
      author: json['author'] as String,
      type: PluginType.fromString(json['type'] as String),
      status: PluginStatus.fromString(json['status'] as String),
      dependencies: List<String>.from(json['dependencies'] as List<dynamic>),
      tags: List<String>.from(json['tags'] as List<dynamic>),
      config: json['config'] as Map<String, dynamic>,
      lastError: json['last_error'] as String?,
      createdAt: DateTime.parse(json['created_at'] as String),
      updatedAt: DateTime.parse(json['updated_at'] as String),
    );
  }

  /// Convert to JSON
  Map<String, dynamic> toJson() {
    return {
      'name': name,
      'version': version,
      'description': description,
      'author': author,
      'type': type.value,
      'status': status.value,
      'dependencies': dependencies,
      'tags': tags,
      'config': config,
      'last_error': lastError,
      'created_at': createdAt.toIso8601String(),
      'updated_at': updatedAt.toIso8601String(),
    };
  }

  /// Check if plugin is enabled and working
  bool get isOperational => status == PluginStatus.enabled && lastError == null;

  /// Check if plugin has errors
  bool get hasErrors => status == PluginStatus.error || lastError != null;

  /// Check if plugin can be executed
  bool get canExecute => status == PluginStatus.enabled;

  /// Get display name for UI
  String get displayName => name.split('_').map((word) => 
      word[0].toUpperCase() + word.substring(1)).join(' ');

  /// Get short description (truncated)
  String get shortDescription {
    if (description.length <= 100) return description;
    return '${description.substring(0, 97)}...';
  }

  /// Check if plugin has been updated recently (within 7 days)
  bool get isRecentlyUpdated => 
      DateTime.now().difference(updatedAt).inDays <= 7;

  /// Get configuration value
  T? getConfigValue<T>(String key) {
    return config[key] as T?;
  }
}

/// Plugin execution request model
class PluginExecutionRequest {
  final String audioId;
  final List<String>? pluginTypes;
  final Map<String, dynamic>? pluginConfig;

  const PluginExecutionRequest({
    required this.audioId,
    this.pluginTypes,
    this.pluginConfig,
  });

  /// Convert to JSON for API request
  Map<String, dynamic> toJson() {
    final json = <String, dynamic>{
      'audio_id': audioId,
    };

    if (pluginTypes != null) json['plugin_types'] = pluginTypes;
    if (pluginConfig != null) json['plugin_config'] = pluginConfig;

    return json;
  }
}

/// Single plugin execution request model
class SinglePluginExecutionRequest {
  final String audioId;
  final String pluginName;
  final Map<String, dynamic>? pluginConfig;

  const SinglePluginExecutionRequest({
    required this.audioId,
    required this.pluginName,
    this.pluginConfig,
  });

  /// Convert to JSON for API request
  Map<String, dynamic> toJson() {
    final json = <String, dynamic>{
      'audio_id': audioId,
      'plugin_name': pluginName,
    };

    if (pluginConfig != null) json['plugin_config'] = pluginConfig;

    return json;
  }
}

/// Plugin execution response model
class PluginExecutionResponse {
  final String taskId;
  final String message;
  final String audioId;
  final String? estimatedCompletionTime;

  const PluginExecutionResponse({
    required this.taskId,
    required this.message,
    required this.audioId,
    this.estimatedCompletionTime,
  });

  /// Create from JSON
  factory PluginExecutionResponse.fromJson(Map<String, dynamic> json) {
    return PluginExecutionResponse(
      taskId: json['task_id'] as String,
      message: json['message'] as String,
      audioId: json['audio_id'] as String,
      estimatedCompletionTime: json['estimated_completion_time'] as String?,
    );
  }

  /// Get estimated completion time as DateTime if available
  DateTime? get estimatedCompletionDateTime {
    if (estimatedCompletionTime == null) return null;
    try {
      return DateTime.parse(estimatedCompletionTime!);
    } catch (e) {
      return null;
    }
  }

  /// Check if execution is successful
  bool get isSuccessful => message.toLowerCase().contains('success');
}

/// Plugin execution update model (for real-time updates)
class PluginExecutionUpdate {
  final String taskId;
  final String audioId;
  final String pluginName;
  final String status;
  final int? progress;
  final String? message;
  final Map<String, dynamic>? data;
  final DateTime timestamp;

  const PluginExecutionUpdate({
    required this.taskId,
    required this.audioId,
    required this.pluginName,
    required this.status,
    this.progress,
    this.message,
    this.data,
    required this.timestamp,
  });

  /// Create from JSON
  factory PluginExecutionUpdate.fromJson(Map<String, dynamic> json) {
    return PluginExecutionUpdate(
      taskId: json['task_id'] as String,
      audioId: json['audio_id'] as String,
      pluginName: json['plugin_name'] as String,
      status: json['status'] as String,
      progress: json['progress'] as int?,
      message: json['message'] as String?,
      data: json['data'] as Map<String, dynamic>?,
      timestamp: DateTime.parse(json['timestamp'] as String),
    );
  }

  /// Check if execution is in progress
  bool get isInProgress => 
      status.toLowerCase() == 'running' || status.toLowerCase() == 'processing';

  /// Check if execution is completed
  bool get isCompleted => status.toLowerCase() == 'completed';

  /// Check if execution has failed
  bool get isFailed => status.toLowerCase() == 'failed' || status.toLowerCase() == 'error';

  /// Get progress percentage (0-100)
  int get progressPercentage => progress ?? 0;
}

/// Plugin results model
class PluginResults {
  final String audioId;
  final String pluginName;
  final Map<String, dynamic> results;
  final String status;
  final DateTime executedAt;
  final double? executionTimeMs;
  final String? error;

  const PluginResults({
    required this.audioId,
    required this.pluginName,
    required this.results,
    required this.status,
    required this.executedAt,
    this.executionTimeMs,
    this.error,
  });

  /// Create from JSON
  factory PluginResults.fromJson(Map<String, dynamic> json) {
    return PluginResults(
      audioId: json['audio_id'] as String,
      pluginName: json['plugin_name'] as String,
      results: json['results'] as Map<String, dynamic>,
      status: json['status'] as String,
      executedAt: DateTime.parse(json['executed_at'] as String),
      executionTimeMs: json['execution_time_ms'] != null
          ? (json['execution_time_ms'] as num).toDouble()
          : null,
      error: json['error'] as String?,
    );
  }

  /// Check if results are successful
  bool get isSuccessful => status.toLowerCase() == 'completed' && error == null;

  /// Check if execution failed
  bool get isFailed => status.toLowerCase() == 'failed' || error != null;

  /// Get execution time in seconds
  double? get executionTimeSeconds => 
      executionTimeMs != null ? executionTimeMs! / 1000.0 : null;

  /// Get result value by key
  T? getResult<T>(String key) {
    return results[key] as T?;
  }

  /// Get nested result value
  T? getNestedResult<T>(List<String> keys) {
    dynamic current = results;
    for (final key in keys) {
      if (current is Map<String, dynamic>) {
        current = current[key];
      } else {
        return null;
      }
    }
    return current as T?;
  }
}

/// Plugin system status overview
class PluginSystemStatus {
  final int totalPlugins;
  final int enabledPlugins;
  final int disabledPlugins;
  final int errorPlugins;
  final Map<String, int> pluginsByType;
  final List<String> recentErrors;
  final Map<String, dynamic> systemInfo;

  const PluginSystemStatus({
    required this.totalPlugins,
    required this.enabledPlugins,
    required this.disabledPlugins,
    required this.errorPlugins,
    required this.pluginsByType,
    required this.recentErrors,
    required this.systemInfo,
  });

  /// Create from JSON
  factory PluginSystemStatus.fromJson(Map<String, dynamic> json) {
    return PluginSystemStatus(
      totalPlugins: json['total_plugins'] as int,
      enabledPlugins: json['enabled_plugins'] as int,
      disabledPlugins: json['disabled_plugins'] as int,
      errorPlugins: json['error_plugins'] as int,
      pluginsByType: Map<String, int>.from(json['plugins_by_type'] as Map<String, dynamic>),
      recentErrors: List<String>.from(json['recent_errors'] as List<dynamic>),
      systemInfo: json['system_info'] as Map<String, dynamic>,
    );
  }

  /// Get operational plugin percentage
  double get operationalPercentage {
    if (totalPlugins == 0) return 100.0;
    return (enabledPlugins / totalPlugins) * 100.0;
  }

  /// Check if system is healthy (>= 80% plugins operational)
  bool get isHealthy => operationalPercentage >= 80.0;

  /// Get status summary
  String get statusSummary {
    if (isHealthy) {
      return 'System Healthy';
    } else if (operationalPercentage >= 50.0) {
      return 'System Degraded';
    } else {
      return 'System Critical';
    }
  }

  /// Check if there are recent errors
  bool get hasRecentErrors => recentErrors.isNotEmpty;
}

/// Available plugin types information
class AvailablePluginTypes {
  final Map<String, String> types;
  final Map<String, String> descriptions;
  final Map<String, List<String>> useCases;

  const AvailablePluginTypes({
    required this.types,
    required this.descriptions,
    required this.useCases,
  });

  /// Create from JSON
  factory AvailablePluginTypes.fromJson(Map<String, dynamic> json) {
    return AvailablePluginTypes(
      types: Map<String, String>.from(json['types'] as Map<String, dynamic>),
      descriptions: Map<String, String>.from(json['descriptions'] as Map<String, dynamic>),
      useCases: json['use_cases'] != null
          ? (json['use_cases'] as Map<String, dynamic>).map(
              (key, value) => MapEntry(key, List<String>.from(value as List<dynamic>)),
            )
          : {},
    );
  }

  /// Get available type names
  List<String> get availableTypes => types.keys.toList();

  /// Get description for type
  String? getDescription(String type) => descriptions[type];

  /// Get use cases for type
  List<String> getUseCases(String type) => useCases[type] ?? [];
}

/// Plugin health response
class PluginHealthResponse {
  final String status;
  final int enabledPlugins;
  final int totalPlugins;
  final List<String> recentErrors;
  final Map<String, dynamic> metrics;

  const PluginHealthResponse({
    required this.status,
    required this.enabledPlugins,
    required this.totalPlugins,
    required this.recentErrors,
    required this.metrics,
  });

  /// Create from JSON
  factory PluginHealthResponse.fromJson(Map<String, dynamic> json) {
    return PluginHealthResponse(
      status: json['status'] as String,
      enabledPlugins: json['enabled_plugins'] as int,
      totalPlugins: json['total_plugins'] as int,
      recentErrors: List<String>.from(json['recent_errors'] as List<dynamic>),
      metrics: json['metrics'] as Map<String, dynamic>,
    );
  }

  /// Check if plugin system is healthy
  bool get isHealthy => status.toLowerCase() == 'healthy';

  /// Get plugin availability percentage
  double get availabilityPercentage {
    if (totalPlugins == 0) return 100.0;
    return (enabledPlugins / totalPlugins) * 100.0;
  }

  /// Check if there are recent errors
  bool get hasRecentErrors => recentErrors.isNotEmpty;
}