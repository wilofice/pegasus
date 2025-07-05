import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/game_model.dart';
import '../providers/game_provider.dart';

class GameSummaryScreen extends ConsumerStatefulWidget {
  final String sessionId;

  const GameSummaryScreen({
    super.key,
    required this.sessionId,
  });

  @override
  ConsumerState<GameSummaryScreen> createState() => _GameSummaryScreenState();
}

class _GameSummaryScreenState extends ConsumerState<GameSummaryScreen> {
  GameSummary? _summary;
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadSummary();
  }

  Future<void> _loadSummary() async {
    try {
      final apiClient = ref.read(apiClientProvider);
      final summary = await apiClient.getGameSummary(widget.sessionId);
      setState(() {
        _summary = summary;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Game Summary'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () {
              setState(() {
                _isLoading = true;
                _error = null;
              });
              _loadSummary();
            },
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? _buildErrorView()
              : _summary != null
                  ? _buildSummaryView()
                  : const Center(child: Text('No summary available')),
    );
  }

  Widget _buildErrorView() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(
              Icons.error_outline,
              size: 64,
              color: Colors.red,
            ),
            const SizedBox(height: 16),
            const Text(
              'Failed to Load Summary',
              style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            Text(
              _error!,
              textAlign: TextAlign.center,
              style: const TextStyle(color: Colors.grey),
            ),
            const SizedBox(height: 24),
            ElevatedButton(
              onPressed: () {
                setState(() {
                  _isLoading = true;
                  _error = null;
                });
                _loadSummary();
              },
              child: const Text('Retry'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSummaryView() {
    final summary = _summary!;
    final scorePercentage = summary.percentageScore;
    final isGoodScore = scorePercentage >= 70;
    final isExcellentScore = scorePercentage >= 90;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header with celebration icon and topic
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(24),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: isExcellentScore
                    ? [Colors.amber.shade300, Colors.amber.shade600]
                    : isGoodScore
                        ? [Colors.green.shade300, Colors.green.shade600]
                        : [Colors.blue.shade300, Colors.blue.shade600],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Column(
              children: [
                Icon(
                  isExcellentScore
                      ? Icons.emoji_events
                      : isGoodScore
                          ? Icons.celebration
                          : Icons.lightbulb,
                  size: 48,
                  color: Colors.white,
                ),
                const SizedBox(height: 12),
                Text(
                  summary.topic,
                  style: const TextStyle(
                    fontSize: 24,
                    fontWeight: FontWeight.bold,
                    color: Colors.white,
                  ),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 8),
                Text(
                  isExcellentScore
                      ? 'Outstanding Performance!'
                      : isGoodScore
                          ? 'Great Job!'
                          : 'Good Effort!',
                  style: const TextStyle(
                    fontSize: 16,
                    color: Colors.white,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),

          // Score section
          _buildSectionCard(
            title: 'Final Score',
            child: Column(
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      '${summary.totalScore} / ${summary.maxPossibleScore}',
                      style: const TextStyle(fontSize: 32, fontWeight: FontWeight.bold),
                    ),
                    Text(
                      '${scorePercentage.toStringAsFixed(1)}%',
                      style: TextStyle(
                        fontSize: 24,
                        fontWeight: FontWeight.bold,
                        color: isExcellentScore
                            ? Colors.amber.shade700
                            : isGoodScore
                                ? Colors.green.shade700
                                : Colors.blue.shade700,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                LinearProgressIndicator(
                  value: scorePercentage / 100,
                  backgroundColor: Colors.grey.shade300,
                  valueColor: AlwaysStoppedAnimation<Color>(
                    isExcellentScore
                        ? Colors.amber.shade600
                        : isGoodScore
                            ? Colors.green.shade600
                            : Colors.blue.shade600,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),

          // Question statistics
          _buildSectionCard(
            title: 'Question Statistics',
            child: Column(
              children: [
                _buildStatRow('Total Questions', summary.totalQuestions.toString()),
                _buildStatRow('Questions Answered', summary.answeredQuestions.toString()),
                _buildStatRow('Correct Answers', summary.correctAnswers.toString()),
                _buildStatRow('Incorrect Answers', summary.incorrectAnswers.toString()),
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(
                      child: _buildStatCard(
                        'Accuracy',
                        summary.answeredQuestions > 0
                            ? '${((summary.correctAnswers / summary.answeredQuestions) * 100).toStringAsFixed(1)}%'
                            : '0%',
                        Colors.green,
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: _buildStatCard(
                        'Completion',
                        summary.totalQuestions > 0
                            ? '${((summary.answeredQuestions / summary.totalQuestions) * 100).toStringAsFixed(1)}%'
                            : '0%',
                        Colors.blue,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),

          // Time statistics
          if (summary.durationMinutes != null)
            _buildSectionCard(
              title: 'Time Statistics',
              child: Column(
                children: [
                  _buildStatRow('Started', _formatDateTime(summary.startedAt)),
                  if (summary.completedAt != null)
                    _buildStatRow('Completed', _formatDateTime(summary.completedAt!)),
                  _buildStatRow('Duration', _formatDuration(summary.durationMinutes!)),
                  if (summary.answeredQuestions > 0)
                    _buildStatRow(
                      'Avg. Time per Question',
                      _formatDuration(summary.durationMinutes! / summary.answeredQuestions),
                    ),
                ],
              ),
            ),
          const SizedBox(height: 24),

          // Action buttons
          Row(
            children: [
              Expanded(
                child: ElevatedButton.icon(
                  onPressed: () {
                    ref.read(gameProvider.notifier).clearGame();
                    Navigator.of(context).popUntil((route) => route.isFirst);
                  },
                  icon: const Icon(Icons.play_arrow),
                  label: const Text('New Game'),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: () => Navigator.of(context).pop(),
                  icon: const Icon(Icons.arrow_back),
                  label: const Text('Back'),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildSectionCard({required String title, required Widget child}) {
    return Card(
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: const TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 12),
            child,
          ],
        ),
      ),
    );
  }

  Widget _buildStatRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label),
          Text(
            value,
            style: const TextStyle(fontWeight: FontWeight.bold),
          ),
        ],
      ),
    );
  }

  Widget _buildStatCard(String label, String value, Color color) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Column(
        children: [
          Text(
            value,
            style: TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.bold,
              color: color,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            label,
            style: TextStyle(
              fontSize: 12,
              color: color.withOpacity(0.8),
            ),
          ),
        ],
      ),
    );
  }

  String _formatDateTime(DateTime dateTime) {
    return '${dateTime.day}/${dateTime.month}/${dateTime.year} '
           '${dateTime.hour.toString().padLeft(2, '0')}:'
           '${dateTime.minute.toString().padLeft(2, '0')}';
  }

  String _formatDuration(double minutes) {
    if (minutes < 1) {
      return '${(minutes * 60).round()}s';
    } else if (minutes < 60) {
      return '${minutes.toStringAsFixed(1)}m';
    } else {
      final hours = minutes ~/ 60;
      final remainingMinutes = minutes % 60;
      return '${hours}h ${remainingMinutes.toStringAsFixed(0)}m';
    }
  }
}