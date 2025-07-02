import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/plugin_provider.dart';
import '../models/plugin_model.dart';
import '../widgets/review_reflection_widgets.dart';
import '../theme.dart';

class ReviewReflectionScreen extends ConsumerStatefulWidget {
  final String audioId;
  final String? audioTitle;

  const ReviewReflectionScreen({
    super.key,
    required this.audioId,
    this.audioTitle,
  });

  @override
  ConsumerState<ReviewReflectionScreen> createState() => _ReviewReflectionScreenState();
}

class _ReviewReflectionScreenState extends ConsumerState<ReviewReflectionScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;
  
  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 4, vsync: this);
    
    // Load plugin results when screen opens
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(pluginProvider.notifier).loadPluginResults(
        widget.audioId, 
        pluginName: 'review_reflection',
      );
    });
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final pluginState = ref.watch(pluginProvider);
    final reviewData = ref.watch(reviewReflectionDataProvider);

    return Scaffold(
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Review & Reflection'),
            if (widget.audioTitle != null)
              Text(
                widget.audioTitle!,
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: Colors.white70,
                ),
              ),
          ],
        ),
        backgroundColor: PegasusTheme.primaryColor,
        foregroundColor: Colors.white,
        elevation: 0,
        actions: [
          if (reviewData == null && !pluginState.isExecuting)
            IconButton(
              icon: const Icon(Icons.refresh),
              onPressed: () => _executeAnalysis(),
              tooltip: 'Run Analysis',
            ),
          if (pluginState.isExecuting)
            Container(
              margin: const EdgeInsets.only(right: 16),
              child: const Center(
                child: SizedBox(
                  width: 20,
                  height: 20,
                  child: CircularProgressIndicator(
                    strokeWidth: 2,
                    valueColor: AlwaysStoppedAnimation(Colors.white),
                  ),
                ),
              ),
            ),
        ],
        bottom: reviewData != null
            ? TabBar(
                controller: _tabController,
                indicatorColor: Colors.white,
                labelColor: Colors.white,
                unselectedLabelColor: Colors.white70,
                tabs: const [
                  Tab(text: 'Overview', icon: Icon(Icons.dashboard, size: 18)),
                  Tab(text: 'Insights', icon: Icon(Icons.lightbulb, size: 18)),
                  Tab(text: 'Actions', icon: Icon(Icons.task_alt, size: 18)),
                  Tab(text: 'Metrics', icon: Icon(Icons.analytics, size: 18)),
                ],
              )
            : null,
      ),
      body: _buildBody(pluginState, reviewData),
    );
  }

  Widget _buildBody(PluginState pluginState, ReviewReflectionData? reviewData) {
    if (pluginState.error != null) {
      return _buildErrorState(pluginState.error!);
    }

    if (pluginState.isLoading) {
      return _buildLoadingState();
    }

    if (reviewData == null) {
      return _buildEmptyState();
    }

    return TabBarView(
      controller: _tabController,
      children: [
        _buildOverviewTab(reviewData),
        _buildInsightsTab(reviewData),
        _buildRecommendationsTab(reviewData),
        _buildMetricsTab(reviewData),
      ],
    );
  }

  Widget _buildLoadingState() {
    return const Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          CircularProgressIndicator(),
          SizedBox(height: 16),
          Text('Loading analysis results...'),
        ],
      ),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.psychology,
            size: 64,
            color: Colors.grey[400],
          ),
          const SizedBox(height: 16),
          Text(
            'No Analysis Available',
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
              color: Colors.grey[600],
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'Run the Review & Reflection analysis to get insights about this conversation.',
            textAlign: TextAlign.center,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
              color: Colors.grey[500],
            ),
          ),
          const SizedBox(height: 24),
          ElevatedButton.icon(
            onPressed: _executeAnalysis,
            icon: const Icon(Icons.play_arrow),
            label: const Text('Run Analysis'),
            style: ElevatedButton.styleFrom(
              backgroundColor: PegasusTheme.primaryColor,
              foregroundColor: Colors.white,
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildErrorState(String error) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.error_outline,
              size: 64,
              color: Colors.red[400],
            ),
            const SizedBox(height: 16),
            Text(
              'Analysis Failed',
              style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                color: Colors.red[600],
              ),
            ),
            const SizedBox(height: 8),
            Text(
              error,
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                color: Colors.grey[600],
              ),
            ),
            const SizedBox(height: 24),
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                OutlinedButton(
                  onPressed: () => ref.read(pluginProvider.notifier).clearError(),
                  child: const Text('Dismiss'),
                ),
                const SizedBox(width: 16),
                ElevatedButton.icon(
                  onPressed: _executeAnalysis,
                  icon: const Icon(Icons.refresh),
                  label: const Text('Retry'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: PegasusTheme.primaryColor,
                    foregroundColor: Colors.white,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildOverviewTab(ReviewReflectionData reviewData) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          ReviewSummaryCard(summary: reviewData.summary),
          const SizedBox(height: 16),
          InsightsCategoriesOverview(insights: reviewData.insights),
          const SizedBox(height: 16),
          QuickStatsCard(
            insights: reviewData.insights,
            metrics: reviewData.metrics,
          ),
        ],
      ),
    );
  }

  Widget _buildInsightsTab(ReviewReflectionData reviewData) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: InsightsListView(insights: reviewData.insights),
    );
  }

  Widget _buildRecommendationsTab(ReviewReflectionData reviewData) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: RecommendationsListView(recommendations: reviewData.recommendations),
    );
  }

  Widget _buildMetricsTab(ReviewReflectionData reviewData) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          AnalyticsMetricsCard(metrics: reviewData.metrics),
          const SizedBox(height: 16),
          ConfigurationCard(config: reviewData.configUsed),
        ],
      ),
    );
  }

  void _executeAnalysis() {
    ref.read(pluginProvider.notifier).executeReviewReflectionPlugin(
      widget.audioId,
      config: {
        'min_confidence': 0.6,
        'max_insights': 15,
        'enable_action_items': true,
        'enable_emotional_analysis': true,
        'enable_learning_insights': true,
      },
    );
  }
}