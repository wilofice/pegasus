// Context Search models for intelligent content retrieval
// 
// These models support the context search API that provides semantic
// and graph-based content discovery with advanced ranking strategies.

import 'api_enums.dart';

/// Request model for context search
class ContextSearchRequest {
  final String query;
  final int maxResults;
  final SearchStrategy strategy;
  final double? vectorWeight;
  final double? graphWeight;
  final bool includeRelated;
  final bool includeAudio;
  final bool includeDocuments;
  final Map<String, dynamic>? filters;

  const ContextSearchRequest({
    required this.query,
    this.maxResults = 20,
    this.strategy = SearchStrategy.hybrid,
    this.vectorWeight,
    this.graphWeight,
    this.includeRelated = true,
    this.includeAudio = true,
    this.includeDocuments = true,
    this.filters,
  });

  /// Convert to JSON for API request
  Map<String, dynamic> toJson() {
    final json = <String, dynamic>{
      'query': query,
      'max_results': maxResults,
      'strategy': strategy.value,
      'include_related': includeRelated,
      'include_audio': includeAudio,
      'include_documents': includeDocuments,
    };

    if (vectorWeight != null) json['vector_weight'] = vectorWeight;
    if (graphWeight != null) json['graph_weight'] = graphWeight;
    if (filters != null) json['filters'] = filters;

    return json;
  }

  /// Convert to query parameters for GET request
  Map<String, String> toQueryParams() {
    final params = <String, String>{
      'query': query,
      'max_results': maxResults.toString(),
      'strategy': strategy.value,
      'include_related': includeRelated.toString(),
    };

    if (vectorWeight != null) params['vector_weight'] = vectorWeight.toString();
    if (graphWeight != null) params['graph_weight'] = graphWeight.toString();

    return params;
  }

  /// Create a copy with updated fields
  ContextSearchRequest copyWith({
    String? query,
    int? maxResults,
    SearchStrategy? strategy,
    double? vectorWeight,
    double? graphWeight,
    bool? includeRelated,
    Map<String, dynamic>? filters,
  }) {
    return ContextSearchRequest(
      query: query ?? this.query,
      maxResults: maxResults ?? this.maxResults,
      strategy: strategy ?? this.strategy,
      vectorWeight: vectorWeight ?? this.vectorWeight,
      graphWeight: graphWeight ?? this.graphWeight,
      includeRelated: includeRelated ?? this.includeRelated,
      filters: filters ?? this.filters,
    );
  }
}

/// Response model for context search
class ContextSearchResponse {
  final List<ContextResult> results;
  final int totalResults;
  final Map<String, dynamic> queryMetadata;
  final String aggregationStrategy;
  final double processingTimeMs;

  const ContextSearchResponse({
    required this.results,
    required this.totalResults,
    required this.queryMetadata,
    required this.aggregationStrategy,
    required this.processingTimeMs,
  });

  /// Create from JSON response
  factory ContextSearchResponse.fromJson(Map<String, dynamic> json) {
    return ContextSearchResponse(
      results: (json['results'] as List<dynamic>)
          .map((result) => ContextResult.fromJson(result as Map<String, dynamic>))
          .toList(),
      totalResults: json['total_results'] as int,
      queryMetadata: json['query_metadata'] as Map<String, dynamic>,
      aggregationStrategy: json['aggregation_strategy'] as String,
      processingTimeMs: (json['processing_time_ms'] as num).toDouble(),
    );
  }

  /// Check if results are available
  bool get hasResults => results.isNotEmpty;

  /// Get processing time in seconds
  double get processingTimeSeconds => processingTimeMs / 1000.0;

  /// Get results grouped by source type
  Map<String, List<ContextResult>> get resultsBySourceType {
    final grouped = <String, List<ContextResult>>{};
    for (final result in results) {
      grouped.putIfAbsent(result.sourceType, () => []).add(result);
    }
    return grouped;
  }

  /// Get high-confidence results (>= 0.8)
  List<ContextResult> get highConfidenceResults {
    return results.where((result) => result.relevanceScore >= 0.8).toList();
  }

  /// Get average relevance score
  double get averageRelevanceScore {
    if (results.isEmpty) return 0.0;
    return results.map((r) => r.relevanceScore).reduce((a, b) => a + b) / results.length;
  }
}

/// Individual context result
class ContextResult {
  final String id;
  final String content;
  final String sourceType;
  final double relevanceScore;
  final Map<String, dynamic> metadata;
  final double? vectorSimilarity;
  final List<Map<String, dynamic>>? graphRelationships;
  final int? graphDistance;
  final double? semanticRelevance;
  final double? structuralRelevance;

  const ContextResult({
    required this.id,
    required this.content,
    required this.sourceType,
    required this.relevanceScore,
    required this.metadata,
    this.vectorSimilarity,
    this.graphRelationships,
    this.graphDistance,
    this.semanticRelevance,
    this.structuralRelevance,
  });

  /// Create from JSON
  factory ContextResult.fromJson(Map<String, dynamic> json) {
    return ContextResult(
      id: json['id'] as String,
      content: json['content'] as String,
      sourceType: json['source_type'] as String,
      relevanceScore: (json['relevance_score'] as num).toDouble(),
      metadata: json['metadata'] as Map<String, dynamic>,
      vectorSimilarity: json['vector_similarity'] != null 
          ? (json['vector_similarity'] as num).toDouble() 
          : null,
      graphRelationships: json['graph_relationships'] != null
          ? List<Map<String, dynamic>>.from(json['graph_relationships'] as List<dynamic>)
          : null,
      graphDistance: json['graph_distance'] as int?,
      semanticRelevance: json['semantic_relevance'] != null
          ? (json['semantic_relevance'] as num).toDouble()
          : null,
      structuralRelevance: json['structural_relevance'] != null
          ? (json['structural_relevance'] as num).toDouble()
          : null,
    );
  }

  /// Get preview content (truncated)
  String get previewContent {
    if (content.length <= 150) return content;
    return '${content.substring(0, 147)}...';
  }

  /// Get source type display name
  String get sourceTypeDisplayName {
    switch (sourceType.toLowerCase()) {
      case 'vector':
        return 'Semantic Search';
      case 'graph':
        return 'Knowledge Graph';
      case 'hybrid':
        return 'Combined Search';
      case 'ensemble':
        return 'Advanced Analysis';
      case 'related':
        return 'Related Content';
      default:
        return sourceType;
    }
  }

  /// Get relevance percentage
  int get relevancePercentage => (relevanceScore * 100).round();

  /// Get audio ID from metadata if available
  String? get audioId => metadata['audio_id'] as String?;

  /// Get timestamp from metadata if available
  String? get timestamp => metadata['timestamp'] as String?;

  /// Get formatted timestamp
  String? get formattedTimestamp {
    if (timestamp == null) return null;
    try {
      final dateTime = DateTime.parse(timestamp!);
      return '${dateTime.day}/${dateTime.month}/${dateTime.year} ${dateTime.hour.toString().padLeft(2, '0')}:${dateTime.minute.toString().padLeft(2, '0')}';
    } catch (e) {
      return timestamp;
    }
  }

  /// Get chunk index from metadata if available
  int? get chunkIndex => metadata['chunk_index'] as int?;

  /// Get language from metadata if available
  String? get language => metadata['language'] as String?;

  /// Get tags from metadata if available
  List<String> get tags {
    final tagsData = metadata['tags'];
    if (tagsData is List) {
      return List<String>.from(tagsData);
    }
    return [];
  }

  /// Get category from metadata if available
  String? get category => metadata['category'] as String?;

  /// Check if result has graph relationships
  bool get hasGraphRelationships => 
      graphRelationships != null && graphRelationships!.isNotEmpty;

  /// Get matched entities from graph relationships
  List<String> get matchedEntities {
    if (!hasGraphRelationships) return [];
    
    final entities = <String>[];
    for (final relationship in graphRelationships!) {
      final matchedEntity = relationship['matched_entity'] as String?;
      if (matchedEntity != null) {
        entities.add(matchedEntity);
      }
    }
    return entities;
  }

  /// Get related entities from graph relationships
  List<String> get relatedEntities {
    if (!hasGraphRelationships) return [];
    
    final entities = <String>[];
    for (final relationship in graphRelationships!) {
      final relatedList = relationship['related_entities'] as List<dynamic>?;
      if (relatedList != null) {
        entities.addAll(List<String>.from(relatedList));
      }
    }
    return entities;
  }

  /// Check if this is a high-quality result
  bool get isHighQuality => relevanceScore >= 0.8;

  /// Check if this is a medium-quality result
  bool get isMediumQuality => relevanceScore >= 0.5 && relevanceScore < 0.8;

  /// Check if this is a low-quality result
  bool get isLowQuality => relevanceScore < 0.5;
}

/// Search strategies information
class SearchStrategiesInfo {
  final Map<String, String> strategies;
  final String defaultStrategy;
  final Map<String, String> descriptions;

  const SearchStrategiesInfo({
    required this.strategies,
    required this.defaultStrategy,
    required this.descriptions,
  });

  /// Create from JSON
  factory SearchStrategiesInfo.fromJson(Map<String, dynamic> json) {
    return SearchStrategiesInfo(
      strategies: Map<String, String>.from(json['strategies'] as Map<String, dynamic>),
      defaultStrategy: json['default_strategy'] as String,
      descriptions: Map<String, String>.from(json['descriptions'] as Map<String, dynamic>),
    );
  }

  /// Get available strategy names
  List<String> get availableStrategies => strategies.keys.toList();
}

/// Context health response
class ContextHealthResponse {
  final String status;
  final Map<String, dynamic> services;
  final double responseTimeMs;

  const ContextHealthResponse({
    required this.status,
    required this.services,
    required this.responseTimeMs,
  });

  /// Create from JSON
  factory ContextHealthResponse.fromJson(Map<String, dynamic> json) {
    return ContextHealthResponse(
      status: json['status'] as String,
      services: json['services'] as Map<String, dynamic>,
      responseTimeMs: (json['response_time_ms'] as num).toDouble(),
    );
  }

  /// Check if all services are healthy
  bool get isHealthy => status.toLowerCase() == 'healthy';

  /// Get service status
  String? getServiceStatus(String serviceName) {
    return services[serviceName]?['status'] as String?;
  }

  /// Check if specific service is healthy
  bool isServiceHealthy(String serviceName) {
    return getServiceStatus(serviceName)?.toLowerCase() == 'healthy';
  }
}

/// Context search result with aggregated information
class ContextSearchResult {
  final String id;
  final String summary;
  final List<ContextResult> sources;
  final SearchStrategy searchStrategy;
  final double overallConfidence;
  final double processingTimeMs;
  final Map<String, dynamic>? metadata;

  const ContextSearchResult({
    required this.id,
    required this.summary,
    required this.sources,
    required this.searchStrategy,
    required this.overallConfidence,
    required this.processingTimeMs,
    this.metadata,
  });

  /// Get the primary source (highest relevance)
  ContextResult get primarySource => sources.first;

  /// Check if result has multiple sources
  bool get hasMultipleSources => sources.length > 1;

  /// Get high-confidence sources only
  List<ContextResult> get highConfidenceSources => 
      sources.where((s) => s.isHighQuality).toList();

  /// Create from JSON
  factory ContextSearchResult.fromJson(Map<String, dynamic> json) {
    return ContextSearchResult(
      id: json['id'] as String,
      summary: json['summary'] as String,
      sources: (json['sources'] as List<dynamic>)
          .map((s) => ContextResult.fromJson(s as Map<String, dynamic>))
          .toList(),
      searchStrategy: SearchStrategy.values.firstWhere(
        (s) => s.value == json['search_strategy'],
        orElse: () => SearchStrategy.hybrid,
      ),
      overallConfidence: (json['overall_confidence'] as num).toDouble(),
      processingTimeMs: (json['processing_time_ms'] as num).toDouble(),
      metadata: json['metadata'] as Map<String, dynamic>?,
    );
  }
}