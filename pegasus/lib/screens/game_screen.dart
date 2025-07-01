import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../providers/game_provider.dart';
import '../widgets/question_widget.dart';
import '../widgets/game_progress_widget.dart';
import '../widgets/validation_result_widget.dart';
import 'game_summary_screen.dart';

class GameScreen extends ConsumerStatefulWidget {
  const GameScreen({super.key});

  @override
  ConsumerState<GameScreen> createState() => _GameScreenState();
}

class _GameScreenState extends ConsumerState<GameScreen> {
  final TextEditingController _topicController = TextEditingController();
  final TextEditingController _lengthController = TextEditingController(text: '10');
  String _selectedDifficulty = 'medium';

  @override
  void dispose() {
    _topicController.dispose();
    _lengthController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final gameState = ref.watch(gameProvider);
    final gameNotifier = ref.read(gameProvider.notifier);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Learning Game'),
        actions: [
          if (gameState.sessionId != null)
            IconButton(
              icon: const Icon(Icons.close),
              onPressed: () => _showEndGameDialog(context, gameNotifier),
            ),
        ],
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: gameState.sessionId == null
              ? _buildGameSetup(context, gameNotifier)
              : _buildGamePlay(context, gameState, gameNotifier),
        ),
      ),
    );
  }

  Widget _buildGameSetup(BuildContext context, GameNotifier gameNotifier) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const Text(
          'Start a New Learning Game',
          style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: 32),
        TextField(
          controller: _topicController,
          decoration: const InputDecoration(
            labelText: 'Topic',
            hintText: 'e.g., History of Italy, Python Programming, Science',
            border: OutlineInputBorder(),
          ),
          maxLines: 2,
        ),
        const SizedBox(height: 16),
        Row(
          children: [
            Expanded(
              child: TextField(
                controller: _lengthController,
                decoration: const InputDecoration(
                  labelText: 'Number of Questions',
                  border: OutlineInputBorder(),
                ),
                keyboardType: TextInputType.number,
              ),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: DropdownButtonFormField<String>(
                value: _selectedDifficulty,
                decoration: const InputDecoration(
                  labelText: 'Difficulty',
                  border: OutlineInputBorder(),
                ),
                items: const [
                  DropdownMenuItem(value: 'easy', child: Text('Easy')),
                  DropdownMenuItem(value: 'medium', child: Text('Medium')),
                  DropdownMenuItem(value: 'hard', child: Text('Hard')),
                ],
                onChanged: (value) {
                  if (value != null) {
                    setState(() {
                      _selectedDifficulty = value;
                    });
                  }
                },
              ),
            ),
          ],
        ),
        const SizedBox(height: 32),
        Consumer(
          builder: (context, ref, child) {
            final gameState = ref.watch(gameProvider);
            return ElevatedButton(
              onPressed: gameState.isLoading ? null : () => _startGame(gameNotifier),
              child: gameState.isLoading
                  ? const Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        SizedBox(
                          width: 20,
                          height: 20,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        ),
                        SizedBox(width: 8),
                        Text('Starting Game...'),
                      ],
                    )
                  : const Text('Start Game'),
            );
          },
        ),
        const SizedBox(height: 16),
        Consumer(
          builder: (context, ref, child) {
            final gameState = ref.watch(gameProvider);
            if (gameState.error != null) {
              return Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.red.shade100,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: Colors.red.shade300),
                ),
                child: Row(
                  children: [
                    Icon(Icons.error, color: Colors.red.shade700),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        gameState.error!,
                        style: TextStyle(color: Colors.red.shade700),
                      ),
                    ),
                    IconButton(
                      icon: const Icon(Icons.close),
                      onPressed: () => ref.read(gameProvider.notifier).clearError(),
                    ),
                  ],
                ),
              );
            }
            return const SizedBox.shrink();
          },
        ),
      ],
    );
  }

  Widget _buildGamePlay(BuildContext context, GameState gameState, GameNotifier gameNotifier) {
    if (gameState.gameCompleted) {
      return _buildGameCompleted(context, gameState, gameNotifier);
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // Progress indicator
        if (gameState.progress != null)
          GameProgressWidget(progress: gameState.progress!),
        const SizedBox(height: 16),
        
        // Score display
        Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: Theme.of(context).primaryColor.withValues(alpha: 0.1),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Text(
            'Score: ${gameState.currentScore}',
            style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            textAlign: TextAlign.center,
          ),
        ),
        const SizedBox(height: 16),

        // Validation result from last question
        if (gameState.lastValidation != null) ...[
          ValidationResultWidget(validation: gameState.lastValidation!),
          const SizedBox(height: 16),
        ],

        // Current question
        if (gameState.currentQuestion != null)
          Expanded(
            child: QuestionWidget(
              question: gameState.currentQuestion!,
              onAnswerChanged: () {
                // Trigger rebuild to update submit button state
                setState(() {});
              },
            ),
          ),

        const SizedBox(height: 16),

        // Submit button
        Consumer(
          builder: (context, ref, child) {
            final canSubmit = ref.watch(canSubmitAnswerProvider);
            return ElevatedButton(
              onPressed: canSubmit ? () => gameNotifier.submitAnswer() : null,
              child: gameState.isLoading
                  ? const Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        SizedBox(
                          width: 20,
                          height: 20,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        ),
                        SizedBox(width: 8),
                        Text('Submitting...'),
                      ],
                    )
                  : const Text('Submit Answer'),
            );
          },
        ),

        // Error display
        if (gameState.error != null) ...[
          const SizedBox(height: 16),
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Colors.red.shade100,
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: Colors.red.shade300),
            ),
            child: Row(
              children: [
                Icon(Icons.error, color: Colors.red.shade700),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    gameState.error!,
                    style: TextStyle(color: Colors.red.shade700),
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.close),
                  onPressed: () => gameNotifier.clearError(),
                ),
              ],
            ),
          ),
        ],
      ],
    );
  }

  Widget _buildGameCompleted(BuildContext context, GameState gameState, GameNotifier gameNotifier) {
    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        const Icon(
          Icons.celebration,
          size: 64,
          color: Colors.amber,
        ),
        const SizedBox(height: 16),
        const Text(
          'Game Completed!',
          style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 16),
        Text(
          'Final Score: ${gameState.currentScore}',
          style: const TextStyle(fontSize: 20),
        ),
        if (gameState.progress != null)
          Text(
            'Questions: ${gameState.progress!.current}/${gameState.progress!.total}',
            style: const TextStyle(fontSize: 16),
          ),
        const SizedBox(height: 32),
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceEvenly,
          children: [
            ElevatedButton(
              onPressed: () => Navigator.of(context).push(
                MaterialPageRoute(
                  builder: (context) => GameSummaryScreen(sessionId: gameState.sessionId!),
                ),
              ),
              child: const Text('View Summary'),
            ),
            ElevatedButton(
              onPressed: () => gameNotifier.clearGame(),
              child: const Text('New Game'),
            ),
          ],
        ),
      ],
    );
  }

  void _startGame(GameNotifier gameNotifier) {
    final topic = _topicController.text.trim();
    final lengthText = _lengthController.text.trim();

    if (topic.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please enter a topic')),
      );
      return;
    }

    final length = int.tryParse(lengthText);
    if (length == null || length < 1 || length > 50) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please enter a valid number of questions (1-50)')),
      );
      return;
    }

    gameNotifier.startGame(topic, length, difficulty: _selectedDifficulty);
  }

  void _showEndGameDialog(BuildContext context, GameNotifier gameNotifier) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('End Game'),
        content: const Text('Are you sure you want to end the current game?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () {
              Navigator.of(context).pop();
              gameNotifier.deleteGameSession();
            },
            child: const Text('End Game'),
          ),
        ],
      ),
    );
  }
}