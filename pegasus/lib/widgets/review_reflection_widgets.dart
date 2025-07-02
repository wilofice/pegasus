import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart';
import '../models/plugin_model.dart';
import '../theme.dart';

/// Widget to display the conversation summary
class ReviewSummaryCard extends StatelessWidget {
  final ReviewReflectionSummary summary;

  const ReviewSummaryCard({super.key, required this.summary});

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  Icons.summarize,
                  color: PegasusTheme.primaryColor,
                  size: 20,
                ),
                const SizedBox(width: 8),
                Text(
                  'Conversation Summary',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            _buildSummaryRow('Type', summary.conversationType, Icons.category),
            _buildSummaryRow('Sentiment', summary.overallSentiment, Icons.sentiment_satisfied),
            _buildSummaryRow('Primary Focus', summary.primaryFocus, Icons.center_focus_strong),
            const SizedBox(height: 12),
            _buildProgressIndicator(
              'Analysis Completeness',
              summary.analysisCompleteness,
              Icons.analytics,
            ),
            _buildProgressIndicator(
              'Confidence Level',
              summary.confidenceLevel,
              Icons.verified,
            ),
            const SizedBox(height: 12),
            if (summary.keyThemes.isNotEmpty) ...[
              Row(
                children: [
                  Icon(Icons.label, size: 16, color: Colors.grey[600]),
                  const SizedBox(width: 8),
                  Text(
                    'Key Themes',
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              Wrap(
                spacing: 8,
                runSpacing: 4,
                children: summary.keyThemes.map((theme) => Chip(
                  label: Text(theme),
                  backgroundColor: PegasusTheme.primaryColor.withOpacity(0.1),
                  labelStyle: TextStyle(
                    color: PegasusTheme.primaryColor,
                    fontSize: 12,
                  ),
                )).toList(),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildSummaryRow(String label, String value, IconData icon) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          Icon(icon, size: 16, color: Colors.grey[600]),
          const SizedBox(width: 8),
          Text(
            '$label: ',
            style: const TextStyle(fontWeight: FontWeight.w500),
          ),
          Expanded(
            child: Text(
              value,
              style: TextStyle(color: Colors.grey[700]),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildProgressIndicator(String label, double value, IconData icon) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, size: 16, color: Colors.grey[600]),
              const SizedBox(width: 8),
              Text(
                label,
                style: const TextStyle(fontWeight: FontWeight.w500),
              ),
              const Spacer(),
              Text(
                '${(value * 100).toInt()}%',
                style: TextStyle(
                  color: Colors.grey[700],
                  fontWeight: FontWeight.w500,
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),
          LinearProgressIndicator(
            value: value,
            backgroundColor: Colors.grey[300],
            valueColor: AlwaysStoppedAnimation(PegasusTheme.primaryColor),
          ),
        ],
      ),
    );
  }
}

/// Widget to display insights categories overview
class InsightsCategoriesOverview extends StatelessWidget {
  final List<ReviewReflectionInsight> insights;

  const InsightsCategoriesOverview({super.key, required this.insights});

  @override
  Widget build(BuildContext context) {
    final categoryGroups = <String, List<ReviewReflectionInsight>>{};
    for (final insight in insights) {
      categoryGroups.putIfAbsent(insight.category, () => []).add(insight);
    }

    return Card(
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  Icons.category,
                  color: PegasusTheme.primaryColor,
                  size: 20,
                ),
                const SizedBox(width: 8),
                Text(
                  'Insights by Category',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            ...categoryGroups.entries.map((entry) => _buildCategoryTile(
              context,
              entry.key,
              entry.value,
            )),
          ],
        ),
      ),
    );
  }

  Widget _buildCategoryTile(
    BuildContext context,
    String category,
    List<ReviewReflectionInsight> categoryInsights,
  ) {
    final avgConfidence = categoryInsights.isNotEmpty
        ? categoryInsights.map((i) => i.confidence).reduce((a, b) => a + b) / categoryInsights.length
        : 0.0;

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          Container(
            width: 12,
            height: 12,
            decoration: BoxDecoration(
              color: _getCategoryColor(category),
              shape: BoxShape.circle,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              category,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
            decoration: BoxDecoration(
              color: Colors.grey[200],
              borderRadius: BorderRadius.circular(12),
            ),
            child: Text(
              '${categoryInsights.length}',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
          const SizedBox(width: 8),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
            decoration: BoxDecoration(
              color: _getConfidenceColor(avgConfidence).withOpacity(0.1),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Text(
              '${(avgConfidence * 100).toInt()}%',
              style: TextStyle(
                color: _getConfidenceColor(avgConfidence),
                fontSize: 12,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Color _getCategoryColor(String category) {
    switch (category.toLowerCase()) {
      case 'communication style':
        return Colors.blue;
      case 'action items':
        return Colors.green;
      case 'emotional tone':
        return Colors.orange;
      case 'learning opportunities':
        return Colors.purple;
      case 'decision making':
        return Colors.red;
      case 'stakeholder engagement':
        return Colors.teal;
      default:
        return Colors.grey;
    }
  }

  Color _getConfidenceColor(double confidence) {
    if (confidence >= 0.8) return Colors.green;
    if (confidence >= 0.6) return Colors.orange;
    return Colors.red;
  }
}

/// Widget to display quick statistics
class QuickStatsCard extends StatelessWidget {
  final List<ReviewReflectionInsight> insights;
  final ReviewReflectionMetrics metrics;

  const QuickStatsCard({
    super.key,
    required this.insights,
    required this.metrics,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  Icons.bar_chart,
                  color: PegasusTheme.primaryColor,
                  size: 20,
                ),
                const SizedBox(width: 8),
                Text(
                  'Quick Statistics',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: _buildStatItem(
                    context,
                    'Total Insights',
                    insights.length.toString(),
                    Icons.lightbulb,
                    Colors.amber,
                  ),
                ),
                Expanded(
                  child: _buildStatItem(
                    context,
                    'Avg Confidence',
                    '${(metrics.averageConfidence * 100).toInt()}%',
                    Icons.verified,
                    Colors.green,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(
                  child: _buildStatItem(
                    context,
                    'Words Analyzed',
                    metrics.transcriptLength.toString(),
                    Icons.text_fields,
                    Colors.blue,
                  ),
                ),
                Expanded(
                  child: _buildStatItem(
                    context,
                    'Entities Found',
                    metrics.entitiesAnalyzed.toString(),
                    Icons.label,
                    Colors.purple,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildStatItem(
    BuildContext context,
    String label,
    String value,
    IconData icon,
    Color color,
  ) {
    return Container(
      margin: const EdgeInsets.all(4),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        children: [
          Icon(icon, color: color, size: 24),
          const SizedBox(height: 8),
          Text(
            value,
            style: Theme.of(context).textTheme.titleLarge?.copyWith(
              fontWeight: FontWeight.bold,
              color: color,
            ),
          ),
          Text(
            label,
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
              color: Colors.grey[600],
            ),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }
}

/// Widget to display the list of insights
class InsightsListView extends StatelessWidget {
  final List<ReviewReflectionInsight> insights;

  const InsightsListView({super.key, required this.insights});

  @override
  Widget build(BuildContext context) {
    if (insights.isEmpty) {
      return const Center(
        child: Text('No insights available'),
      );
    }

    return Column(
      children: insights.map((insight) => InsightCard(insight: insight)).toList(),
    );
  }
}

/// Widget to display a single insight
class InsightCard extends StatelessWidget {
  final ReviewReflectionInsight insight;

  const InsightCard({super.key, required this.insight});

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      elevation: 1,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: _getCategoryColor(insight.category).withOpacity(0.1),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text(
                    insight.category,
                    style: TextStyle(
                      color: _getCategoryColor(insight.category),
                      fontSize: 12,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
                const Spacer(),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: _getConfidenceColor(insight.confidence).withOpacity(0.1),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text(
                    '${(insight.confidence * 100).toInt()}%',
                    style: TextStyle(
                      color: _getConfidenceColor(insight.confidence),
                      fontSize: 12,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Text(
              insight.insight,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                fontWeight: FontWeight.w500,
              ),
            ),
            if (insight.evidence.isNotEmpty) ...[
              const SizedBox(height: 12),
              Text(
                'Evidence:',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  fontWeight: FontWeight.bold,
                  color: Colors.grey[700],
                ),
              ),
              const SizedBox(height: 4),
              ...insight.evidence.map((evidence) => Padding(
                padding: const EdgeInsets.only(left: 8, top: 2),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('• ', style: TextStyle(color: Colors.grey[600])),
                    Expanded(
                      child: Text(
                        evidence,
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: Colors.grey[600],
                        ),
                      ),
                    ),
                  ],
                ),
              )),
            ],
            if (insight.actionItems.isNotEmpty) ...[
              const SizedBox(height: 12),
              Text(
                'Suggested Actions:',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  fontWeight: FontWeight.bold,
                  color: Colors.grey[700],
                ),
              ),
              const SizedBox(height: 4),
              ...insight.actionItems.map((action) => Padding(
                padding: const EdgeInsets.only(left: 8, top: 2),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(Icons.arrow_right, size: 16, color: Colors.grey[600]),
                    Expanded(
                      child: Text(
                        action,
                        style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: Colors.grey[600],
                        ),
                      ),
                    ),
                  ],
                ),
              )),
            ],
          ],
        ),
      ),
    );
  }

  Color _getCategoryColor(String category) {
    switch (category.toLowerCase()) {
      case 'communication style':
        return Colors.blue;
      case 'action items':
        return Colors.green;
      case 'emotional tone':
        return Colors.orange;
      case 'learning opportunities':
        return Colors.purple;
      case 'decision making':
        return Colors.red;
      case 'stakeholder engagement':
        return Colors.teal;
      default:
        return Colors.grey;
    }
  }

  Color _getConfidenceColor(double confidence) {
    if (confidence >= 0.8) return Colors.green;
    if (confidence >= 0.6) return Colors.orange;
    return Colors.red;
  }
}

/// Widget to display recommendations
class RecommendationsListView extends StatelessWidget {
  final List<ReviewReflectionRecommendation> recommendations;

  const RecommendationsListView({super.key, required this.recommendations});

  @override
  Widget build(BuildContext context) {
    if (recommendations.isEmpty) {
      return const Center(
        child: Text('No recommendations available'),
      );
    }

    return Column(
      children: recommendations.map((rec) => RecommendationCard(recommendation: rec)).toList(),
    );
  }
}

/// Widget to display a single recommendation
class RecommendationCard extends StatelessWidget {
  final ReviewReflectionRecommendation recommendation;

  const RecommendationCard({super.key, required this.recommendation});

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      elevation: 1,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: _getPriorityColor(recommendation.priority).withOpacity(0.1),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text(
                    recommendation.priority.toUpperCase(),
                    style: TextStyle(
                      color: _getPriorityColor(recommendation.priority),
                      fontSize: 12,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    recommendation.category,
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                Icon(Icons.schedule, size: 16, color: Colors.grey[600]),
                const SizedBox(width: 4),
                Text(
                  recommendation.timeframe,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: Colors.grey[600],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Text(
              recommendation.rationale,
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            if (recommendation.actions.isNotEmpty) ...[
              const SizedBox(height: 12),
              Text(
                'Actions:',
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 4),
              ...recommendation.actions.map((action) => Padding(
                padding: const EdgeInsets.only(left: 8, top: 4),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Container(
                      margin: const EdgeInsets.only(top: 6),
                      width: 6,
                      height: 6,
                      decoration: BoxDecoration(
                        color: _getPriorityColor(recommendation.priority),
                        shape: BoxShape.circle,
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        action,
                        style: Theme.of(context).textTheme.bodyMedium,
                      ),
                    ),
                  ],
                ),
              )),
            ],
          ],
        ),
      ),
    );
  }

  Color _getPriorityColor(String priority) {
    switch (priority.toLowerCase()) {
      case 'high':
        return Colors.red;
      case 'medium':
        return Colors.orange;
      case 'low':
        return Colors.green;
      default:
        return Colors.grey;
    }
  }
}

/// Widget to display analytics metrics
class AnalyticsMetricsCard extends StatelessWidget {
  final ReviewReflectionMetrics metrics;

  const AnalyticsMetricsCard({super.key, required this.metrics});

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  Icons.analytics,
                  color: PegasusTheme.primaryColor,
                  size: 20,
                ),
                const SizedBox(width: 8),
                Text(
                  'Analysis Metrics',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            _buildMetricRow('Total Insights Generated', metrics.totalInsightsGenerated.toString()),
            _buildMetricRow('Insights Above Threshold', metrics.insightsAboveThreshold.toString()),
            _buildMetricRow('Confidence Threshold', '${(metrics.confidenceThreshold * 100).toInt()}%'),
            _buildMetricRow('Average Confidence', '${(metrics.averageConfidence * 100).toInt()}%'),
            _buildMetricRow('Transcript Length', '${metrics.transcriptLength} words'),
            _buildMetricRow('Entities Analyzed', metrics.entitiesAnalyzed.toString()),
            _buildMetricRow('Content Chunks', metrics.chunksAnalyzed.toString()),
            if (metrics.categoriesFound.isNotEmpty) ...[
              const SizedBox(height: 8),
              Text(
                'Categories Found:',
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 4),
              Wrap(
                spacing: 4,
                runSpacing: 4,
                children: metrics.categoriesFound.map((category) => Chip(
                  label: Text(
                    category,
                    style: const TextStyle(fontSize: 10),
                  ),
                  backgroundColor: Colors.grey[200],
                  materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                )).toList(),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildMetricRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            label,
            style: const TextStyle(fontWeight: FontWeight.w500),
          ),
          Text(
            value,
            style: TextStyle(
              color: Colors.grey[700],
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }
}

/// Widget to display configuration used
class ConfigurationCard extends StatelessWidget {
  final Map<String, dynamic> config;

  const ConfigurationCard({super.key, required this.config});

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  Icons.settings,
                  color: PegasusTheme.primaryColor,
                  size: 20,
                ),
                const SizedBox(width: 8),
                Text(
                  'Configuration Used',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            ...config.entries.map((entry) => _buildConfigRow(
              _formatConfigKey(entry.key),
              _formatConfigValue(entry.value),
            )),
          ],
        ),
      ),
    );
  }

  Widget _buildConfigRow(String key, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            key,
            style: const TextStyle(fontWeight: FontWeight.w500),
          ),
          Text(
            value,
            style: TextStyle(
              color: Colors.grey[700],
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }

  String _formatConfigKey(String key) {
    return key
        .split('_')
        .map((word) => word[0].toUpperCase() + word.substring(1))
        .join(' ');
  }

  String _formatConfigValue(dynamic value) {
    if (value is bool) {
      return value ? 'Enabled' : 'Disabled';
    }
    if (value is double && value <= 1.0) {
      return '${(value * 100).toInt()}%';
    }
    return value.toString();
  }
}