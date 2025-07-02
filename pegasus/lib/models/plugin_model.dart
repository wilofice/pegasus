/// Models for plugin execution results and insights
class PluginResult {
  final String pluginName;
  final String? executionTime;
  final double processingTimeMs;
  final Map<String, dynamic> resultData;

  PluginResult({
    required this.pluginName,
    this.executionTime,
    required this.processingTimeMs,
    required this.resultData,
  });

  factory PluginResult.fromJson(Map<String, dynamic> json) {
    return PluginResult(
      pluginName: json['plugin_name'] as String,
      executionTime: json['execution_time'] as String?,
      processingTimeMs: (json['processing_time_ms'] as num?)?.toDouble() ?? 0.0,
      resultData: json['result_data'] as Map<String, dynamic>? ?? {},
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'plugin_name': pluginName,
      'execution_time': executionTime,
      'processing_time_ms': processingTimeMs,
      'result_data': resultData,
    };
  }
}

class ReviewReflectionInsight {
  final String category;
  final String insight;
  final double confidence;
  final List<String> evidence;
  final List<String> actionItems;

  ReviewReflectionInsight({
    required this.category,
    required this.insight,
    required this.confidence,
    required this.evidence,
    required this.actionItems,
  });

  factory ReviewReflectionInsight.fromJson(Map<String, dynamic> json) {
    return ReviewReflectionInsight(
      category: json['category'] as String,
      insight: json['insight'] as String,
      confidence: (json['confidence'] as num).toDouble(),
      evidence: List<String>.from(json['evidence'] as List? ?? []),
      actionItems: List<String>.from(json['action_items'] as List? ?? []),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'category': category,
      'insight': insight,
      'confidence': confidence,
      'evidence': evidence,
      'action_items': actionItems,
    };
  }
}

class ReviewReflectionSummary {
  final String conversationType;
  final List<String> keyThemes;
  final String overallSentiment;
  final double confidenceLevel;
  final int totalInsights;
  final int wordCount;
  final double analysisCompleteness;
  final String primaryFocus;

  ReviewReflectionSummary({
    required this.conversationType,
    required this.keyThemes,
    required this.overallSentiment,
    required this.confidenceLevel,
    required this.totalInsights,
    required this.wordCount,
    required this.analysisCompleteness,
    required this.primaryFocus,
  });

  factory ReviewReflectionSummary.fromJson(Map<String, dynamic> json) {
    return ReviewReflectionSummary(
      conversationType: json['conversation_type'] as String? ?? 'Unknown',
      keyThemes: List<String>.from(json['key_themes'] as List? ?? []),
      overallSentiment: json['overall_sentiment'] as String? ?? 'Neutral',
      confidenceLevel: (json['confidence_level'] as num?)?.toDouble() ?? 0.0,
      totalInsights: json['total_insights'] as int? ?? 0,
      wordCount: json['word_count'] as int? ?? 0,
      analysisCompleteness: (json['analysis_completeness'] as num?)?.toDouble() ?? 0.0,
      primaryFocus: json['primary_focus'] as String? ?? 'Unknown',
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'conversation_type': conversationType,
      'key_themes': keyThemes,
      'overall_sentiment': overallSentiment,
      'confidence_level': confidenceLevel,
      'total_insights': totalInsights,
      'word_count': wordCount,
      'analysis_completeness': analysisCompleteness,
      'primary_focus': primaryFocus,
    };
  }
}

class ReviewReflectionRecommendation {
  final String priority;
  final String timeframe;
  final String category;
  final List<String> actions;
  final String rationale;

  ReviewReflectionRecommendation({
    required this.priority,
    required this.timeframe,
    required this.category,
    required this.actions,
    required this.rationale,
  });

  factory ReviewReflectionRecommendation.fromJson(Map<String, dynamic> json) {
    return ReviewReflectionRecommendation(
      priority: json['priority'] as String,
      timeframe: json['timeframe'] as String,
      category: json['category'] as String,
      actions: List<String>.from(json['actions'] as List? ?? []),
      rationale: json['rationale'] as String,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'priority': priority,
      'timeframe': timeframe,
      'category': category,
      'actions': actions,
      'rationale': rationale,
    };
  }
}

class ReviewReflectionMetrics {
  final int totalInsightsGenerated;
  final int insightsAboveThreshold;
  final double confidenceThreshold;
  final double averageConfidence;
  final List<String> categoriesFound;
  final int transcriptLength;
  final int entitiesAnalyzed;
  final int chunksAnalyzed;

  ReviewReflectionMetrics({
    required this.totalInsightsGenerated,
    required this.insightsAboveThreshold,
    required this.confidenceThreshold,
    required this.averageConfidence,
    required this.categoriesFound,
    required this.transcriptLength,
    required this.entitiesAnalyzed,
    required this.chunksAnalyzed,
  });

  factory ReviewReflectionMetrics.fromJson(Map<String, dynamic> json) {
    return ReviewReflectionMetrics(
      totalInsightsGenerated: json['total_insights_generated'] as int? ?? 0,
      insightsAboveThreshold: json['insights_above_threshold'] as int? ?? 0,
      confidenceThreshold: (json['confidence_threshold'] as num?)?.toDouble() ?? 0.0,
      averageConfidence: (json['average_confidence'] as num?)?.toDouble() ?? 0.0,
      categoriesFound: List<String>.from(json['categories_found'] as List? ?? []),
      transcriptLength: json['transcript_length'] as int? ?? 0,
      entitiesAnalyzed: json['entities_analyzed'] as int? ?? 0,
      chunksAnalyzed: json['chunks_analyzed'] as int? ?? 0,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'total_insights_generated': totalInsightsGenerated,
      'insights_above_threshold': insightsAboveThreshold,
      'confidence_threshold': confidenceThreshold,
      'average_confidence': averageConfidence,
      'categories_found': categoriesFound,
      'transcript_length': transcriptLength,
      'entities_analyzed': entitiesAnalyzed,
      'chunks_analyzed': chunksAnalyzed,
    };
  }
}

class ReviewReflectionData {
  final List<ReviewReflectionInsight> insights;
  final ReviewReflectionSummary summary;
  final List<ReviewReflectionRecommendation> recommendations;
  final ReviewReflectionMetrics metrics;
  final Map<String, dynamic> configUsed;

  ReviewReflectionData({
    required this.insights,
    required this.summary,
    required this.recommendations,
    required this.metrics,
    required this.configUsed,
  });

  factory ReviewReflectionData.fromJson(Map<String, dynamic> json) {
    return ReviewReflectionData(
      insights: (json['insights'] as List?)
          ?.map((i) => ReviewReflectionInsight.fromJson(i as Map<String, dynamic>))
          .toList() ?? [],
      summary: ReviewReflectionSummary.fromJson(json['summary'] as Map<String, dynamic>? ?? {}),
      recommendations: (json['recommendations'] as List?)
          ?.map((r) => ReviewReflectionRecommendation.fromJson(r as Map<String, dynamic>))
          .toList() ?? [],
      metrics: ReviewReflectionMetrics.fromJson(json['metrics'] as Map<String, dynamic>? ?? {}),
      configUsed: json['config_used'] as Map<String, dynamic>? ?? {},
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'insights': insights.map((i) => i.toJson()).toList(),
      'summary': summary.toJson(),
      'recommendations': recommendations.map((r) => r.toJson()).toList(),
      'metrics': metrics.toJson(),
      'config_used': configUsed,
    };
  }
}

class PluginExecutionResponse {
  final String audioId;
  final int totalResults;
  final List<PluginResult> results;

  PluginExecutionResponse({
    required this.audioId,
    required this.totalResults,
    required this.results,
  });

  factory PluginExecutionResponse.fromJson(Map<String, dynamic> json) {
    return PluginExecutionResponse(
      audioId: json['audio_id'] as String,
      totalResults: json['total_results'] as int? ?? 0,
      results: (json['results'] as List?)
          ?.map((r) => PluginResult.fromJson(r as Map<String, dynamic>))
          .toList() ?? [],
    );
  }

  /// Get the review reflection data if available
  ReviewReflectionData? getReviewReflectionData() {
    final reviewResult = results.firstWhere(
      (result) => result.pluginName == 'review_reflection',
      orElse: () => PluginResult(
        pluginName: '',
        processingTimeMs: 0,
        resultData: {},
      ),
    );
    
    if (reviewResult.pluginName.isEmpty) return null;
    
    return ReviewReflectionData.fromJson(reviewResult.resultData);
  }

  Map<String, dynamic> toJson() {
    return {
      'audio_id': audioId,
      'total_results': totalResults,
      'results': results.map((r) => r.toJson()).toList(),
    };
  }
}