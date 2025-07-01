import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter/foundation.dart';
import '../models/game_model.dart';
import '../api/pegasus_api_client.dart';

// Game state class
class GameState {
  final bool isLoading;
  final String? sessionId;
  final Question? currentQuestion;
  final ValidationResponse? lastValidation;
  final GameSummary? summary;
  final String? error;
  final GameProgress? progress;
  final int currentScore;
  final bool gameCompleted;
  final Map<String, dynamic> userAnswers; // Track answers for each question

  const GameState({
    this.isLoading = false,
    this.sessionId,
    this.currentQuestion,
    this.lastValidation,
    this.summary,
    this.error,
    this.progress,
    this.currentScore = 0,
    this.gameCompleted = false,
    this.userAnswers = const {},
  });

  GameState copyWith({
    bool? isLoading,
    String? sessionId,
    Question? currentQuestion,
    ValidationResponse? lastValidation,
    GameSummary? summary,
    String? error,
    GameProgress? progress,
    int? currentScore,
    bool? gameCompleted,
    Map<String, dynamic>? userAnswers,
  }) {
    return GameState(
      isLoading: isLoading ?? this.isLoading,
      sessionId: sessionId ?? this.sessionId,
      currentQuestion: currentQuestion ?? this.currentQuestion,
      lastValidation: lastValidation ?? this.lastValidation,
      summary: summary ?? this.summary,
      error: error ?? this.error,
      progress: progress ?? this.progress,
      currentScore: currentScore ?? this.currentScore,
      gameCompleted: gameCompleted ?? this.gameCompleted,
      userAnswers: userAnswers ?? this.userAnswers,
    );
  }
}

// User answer state for the current question
class UserAnswerState {
  final List<String> selectedOptions;
  final String? customText;

  const UserAnswerState({
    this.selectedOptions = const [],
    this.customText,
  });

  UserAnswerState copyWith({
    List<String>? selectedOptions,
    String? customText,
  }) {
    return UserAnswerState(
      selectedOptions: selectedOptions ?? this.selectedOptions,
      customText: customText ?? this.customText,
    );
  }

  UserAnswer toUserAnswer(String questionId) {
    return UserAnswer(
      questionId: questionId,
      selectedOptions: selectedOptions.isNotEmpty ? selectedOptions : null,
      customText: customText?.trim().isNotEmpty == true ? customText : null,
    );
  }

  bool get hasAnswer {
    return selectedOptions.isNotEmpty || (customText?.trim().isNotEmpty == true);
  }
}

// User answer notifier
class UserAnswerNotifier extends StateNotifier<UserAnswerState> {
  UserAnswerNotifier() : super(const UserAnswerState());

  void updateSelectedOptions(List<String> options) {
    state = state.copyWith(selectedOptions: options);
  }

  void updateCustomText(String text) {
    state = state.copyWith(customText: text);
  }

  void reset() {
    state = const UserAnswerState();
  }
}

// Game notifier
class GameNotifier extends StateNotifier<GameState> {
  final PegasusApiClient _apiClient;

  GameNotifier(this._apiClient) : super(const GameState());

  // User answer state notifier
  final _userAnswerNotifier = UserAnswerNotifier();
  UserAnswerNotifier get userAnswerNotifier => _userAnswerNotifier;

  // Start a new game
  Future<void> startGame(String topic, int length, {String? difficulty}) async {
    state = state.copyWith(isLoading: true, error: null);
    
    try {
      final request = GameStartRequest(
        topic: topic,
        length: length,
        difficulty: difficulty,
      );
      
      final response = await _apiClient.startGame(request);
      
      state = state.copyWith(
        isLoading: false,
        sessionId: response.sessionId,
        currentQuestion: response.firstQuestion,
        progress: GameProgress(
          current: 0,
          total: response.totalQuestions,
          remaining: response.totalQuestions,
        ),
        currentScore: 0,
        gameCompleted: false,
        userAnswers: {},
      );
      
      // Reset user answer for new question
      _resetUserAnswer();
      
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  // Submit the current answer
  Future<void> submitAnswer() async {
    if (state.currentQuestion == null || state.sessionId == null) {
      state = state.copyWith(error: 'No active question or session');
      return;
    }

    if (!_userAnswerNotifier.state.hasAnswer) {
      state = state.copyWith(error: 'Please provide an answer');
      return;
    }

    state = state.copyWith(isLoading: true, error: null);
    
    try {
      final userAnswer = _userAnswerNotifier.state.toUserAnswer(state.currentQuestion!.id);
      final request = GameAnswerRequest(answer: userAnswer);
      
      final response = await _apiClient.submitAnswer(state.sessionId!, request);
      
      // Update user answers tracking
      final updatedAnswers = Map<String, dynamic>.from(state.userAnswers);
      updatedAnswers[state.currentQuestion!.id] = {
        'question': state.currentQuestion!.toJson(),
        'answer': userAnswer.toJson(),
        'validation': response.validation.toJson(),
      };
      
      state = state.copyWith(
        isLoading: false,
        lastValidation: response.validation,
        currentQuestion: response.nextQuestion,
        currentScore: response.currentScore,
        gameCompleted: response.gameCompleted,
        progress: GameProgress.fromMap(response.progress),
        userAnswers: updatedAnswers,
      );
      
      // If game is completed, fetch summary
      if (response.gameCompleted) {
        await _fetchGameSummary();
      } else {
        // Reset user answer for next question
        _resetUserAnswer();
      }
      
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  // Fetch game summary
  Future<void> _fetchGameSummary() async {
    if (state.sessionId == null) return;
    
    try {
      final summary = await _apiClient.getGameSummary(state.sessionId!);
      state = state.copyWith(summary: summary);
    } catch (e) {
      // Don't update error state since this is a background operation
      if (kDebugMode) print('Failed to fetch game summary: $e');
    }
  }

  // Update selected options for multiple choice questions
  void updateSelectedOptions(List<String> options) {
    _userAnswerNotifier.updateSelectedOptions(options);
  }

  // Toggle option for multiple choice questions
  void toggleOption(String option) {
    final currentOptions = List<String>.from(_userAnswerNotifier.state.selectedOptions);
    if (currentOptions.contains(option)) {
      currentOptions.remove(option);
    } else {
      currentOptions.add(option);
    }
    updateSelectedOptions(currentOptions);
  }

  // Select single option for single choice questions
  void selectSingleOption(String option) {
    updateSelectedOptions([option]);
  }

  // Update custom text for free text questions
  void updateCustomText(String text) {
    _userAnswerNotifier.updateCustomText(text);
  }

  // Reset user answer state
  void _resetUserAnswer() {
    _userAnswerNotifier.reset();
  }

  // Clear game state
  void clearGame() {
    state = const GameState();
    _resetUserAnswer();
  }

  // Clear error
  void clearError() {
    state = state.copyWith(error: null);
  }

  // Delete game session (cleanup)
  Future<void> deleteGameSession() async {
    if (state.sessionId != null) {
      try {
        await _apiClient.deleteGameSession(state.sessionId!);
      } catch (e) {
        if (kDebugMode) print('Failed to delete game session: $e');
      }
    }
    clearGame();
  }
}

// Providers
final apiClientProvider = Provider<PegasusApiClient>((ref) {
  return PegasusApiClient.defaultConfig();
});

final gameProvider = StateNotifierProvider<GameNotifier, GameState>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return GameNotifier(apiClient);
});

final userAnswerProvider = StateNotifierProvider<UserAnswerNotifier, UserAnswerState>((ref) {
  final gameNotifier = ref.watch(gameProvider.notifier);
  return gameNotifier.userAnswerNotifier;
});

final userAnswerStateProvider = Provider<UserAnswerState>((ref) {
  return ref.watch(userAnswerProvider);
});

// Computed providers for convenience
final canSubmitAnswerProvider = Provider<bool>((ref) {
  final userAnswerState = ref.watch(userAnswerStateProvider);
  final gameState = ref.watch(gameProvider);
  return userAnswerState.hasAnswer && !gameState.isLoading && !gameState.gameCompleted;
});

final progressPercentageProvider = Provider<double>((ref) {
  final gameState = ref.watch(gameProvider);
  return gameState.progress?.percentage ?? 0.0;
});

final isGameActiveProvider = Provider<bool>((ref) {
  final gameState = ref.watch(gameProvider);
  return gameState.sessionId != null && !gameState.gameCompleted;
});