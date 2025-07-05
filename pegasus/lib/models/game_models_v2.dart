/// Enhanced Game API models for comprehensive game functionality
/// 
/// These models support the game API with advanced question types,
/// validation, and comprehensive progress tracking.

import 'api_enums.dart';

/// Game start request model
class GameStartRequest {
  final String topic;
  final int length;
  final String? difficulty;

  const GameStartRequest({
    required this.topic,
    this.length = 10,
    this.difficulty = 'medium',
  });

  /// Convert to JSON for API request
  Map<String, dynamic> toJson() {
    return {
      'topic': topic,
      'length': length,
      'difficulty': difficulty,
    };
  }
}

/// Game start response model
class GameStartResponse {
  final String sessionId;
  final Question firstQuestion;
  final int totalQuestions;

  const GameStartResponse({
    required this.sessionId,
    required this.firstQuestion,
    required this.totalQuestions,
  });

  /// Create from JSON
  factory GameStartResponse.fromJson(Map<String, dynamic> json) {
    return GameStartResponse(
      sessionId: json['session_id'] as String,
      firstQuestion: Question.fromJson(json['first_question'] as Map<String, dynamic>),
      totalQuestions: json['total_questions'] as int,
    );
  }
}

/// Question model
class Question {
  final String id;
  final String text;
  final QuestionType type;
  final List<String>? options;
  final String? hint;
  final String difficulty;

  const Question({
    required this.id,
    required this.text,
    required this.type,
    this.options,
    this.hint,
    this.difficulty = 'medium',
  });

  /// Create from JSON
  factory Question.fromJson(Map<String, dynamic> json) {
    return Question(
      id: json['id'] as String,
      text: json['text'] as String,
      type: QuestionType.fromString(json['type'] as String),
      options: json['options'] != null
          ? List<String>.from(json['options'] as List<dynamic>)
          : null,
      hint: json['hint'] as String?,
      difficulty: json['difficulty'] as String? ?? 'medium',
    );
  }

  /// Convert to JSON
  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'text': text,
      'type': type.value,
      'options': options,
      'hint': hint,
      'difficulty': difficulty,
    };
  }

  /// Check if question has options (choice questions)
  bool get hasOptions => options != null && options!.isNotEmpty;

  /// Check if question allows multiple selections
  bool get allowsMultipleSelection => type == QuestionType.multipleChoice;

  /// Check if question is free text
  bool get isFreeText => type == QuestionType.freeText;

  /// Get difficulty level as number (1-5)
  int get difficultyLevel {
    switch (difficulty.toLowerCase()) {
      case 'very_easy':
      case 'very easy':
        return 1;
      case 'easy':
        return 2;
      case 'medium':
        return 3;
      case 'hard':
        return 4;
      case 'very_hard':
      case 'very hard':
        return 5;
      default:
        return 3;
    }
  }

  /// Get difficulty color for UI
  String get difficultyColor {
    switch (difficultyLevel) {
      case 1:
        return '#4CAF50'; // Green
      case 2:
        return '#8BC34A'; // Light Green
      case 3:
        return '#FF9800'; // Orange
      case 4:
        return '#FF5722'; // Deep Orange
      case 5:
        return '#F44336'; // Red
      default:
        return '#FF9800'; // Orange
    }
  }
}

/// User answer model
class UserAnswer {
  final String questionId;
  final List<String>? selectedOptions;
  final String? customText;

  const UserAnswer({
    required this.questionId,
    this.selectedOptions,
    this.customText,
  });

  /// Convert to JSON for API request
  Map<String, dynamic> toJson() {
    return {
      'question_id': questionId,
      'selected_options': selectedOptions,
      'custom_text': customText,
    };
  }

  /// Check if answer has selected options
  bool get hasSelectedOptions => 
      selectedOptions != null && selectedOptions!.isNotEmpty;

  /// Check if answer has custom text
  bool get hasCustomText => customText != null && customText!.isNotEmpty;

  /// Check if answer is empty
  bool get isEmpty => !hasSelectedOptions && !hasCustomText;

  /// Get answer summary for display
  String get answerSummary {
    if (hasSelectedOptions) {
      return selectedOptions!.join(', ');
    } else if (hasCustomText) {
      return customText!.length > 50 
          ? '${customText!.substring(0, 50)}...'
          : customText!;
    } else {
      return 'No answer';
    }
  }
}

/// Game answer request model
class GameAnswerRequest {
  final UserAnswer answer;

  const GameAnswerRequest({
    required this.answer,
  });

  /// Convert to JSON for API request
  Map<String, dynamic> toJson() {
    return {
      'answer': answer.toJson(),
    };
  }
}

/// Validation response model
class ValidationResponse {
  final bool isCorrect;
  final String explanation;
  final String? correctAnswer;
  final int scorePoints;

  const ValidationResponse({
    required this.isCorrect,
    required this.explanation,
    this.correctAnswer,
    this.scorePoints = 0,
  });

  /// Create from JSON
  factory ValidationResponse.fromJson(Map<String, dynamic> json) {
    return ValidationResponse(
      isCorrect: json['is_correct'] as bool,
      explanation: json['explanation'] as String,
      correctAnswer: json['correct_answer'] as String?,
      scorePoints: json['score_points'] as int? ?? 0,
    );
  }

  /// Get result icon for UI
  String get resultIcon => isCorrect ? '✅' : '❌';

  /// Get result color for UI
  String get resultColor => isCorrect ? '#4CAF50' : '#F44336';

  /// Get points description
  String get pointsDescription {
    if (scorePoints == 0) return 'No points';
    if (scorePoints == 1) return '1 point';
    return '$scorePoints points';
  }
}

/// Game answer response model
class GameAnswerResponse {
  final ValidationResponse validation;
  final Question? nextQuestion;
  final bool gameCompleted;
  final int currentScore;
  final Map<String, int> progress;

  const GameAnswerResponse({
    required this.validation,
    this.nextQuestion,
    this.gameCompleted = false,
    this.currentScore = 0,
    this.progress = const {},
  });

  /// Create from JSON
  factory GameAnswerResponse.fromJson(Map<String, dynamic> json) {
    return GameAnswerResponse(
      validation: ValidationResponse.fromJson(json['validation'] as Map<String, dynamic>),
      nextQuestion: json['next_question'] != null
          ? Question.fromJson(json['next_question'] as Map<String, dynamic>)
          : null,
      gameCompleted: json['game_completed'] as bool? ?? false,
      currentScore: json['current_score'] as int? ?? 0,
      progress: json['progress'] != null
          ? Map<String, int>.from(json['progress'] as Map<String, dynamic>)
          : {},
    );
  }

  /// Check if there's a next question
  bool get hasNextQuestion => nextQuestion != null;

  /// Get current question number
  int get currentQuestionNumber => progress['answered'] ?? 0;

  /// Get total questions
  int get totalQuestions => progress['total'] ?? 0;

  /// Get progress percentage
  double get progressPercentage {
    if (totalQuestions == 0) return 0.0;
    return (currentQuestionNumber / totalQuestions) * 100.0;
  }

  /// Get remaining questions
  int get remainingQuestions => totalQuestions - currentQuestionNumber;
}

/// Game summary response model
class GameSummaryResponse {
  final String sessionId;
  final String topic;
  final int totalQuestions;
  final int answeredQuestions;
  final int totalScore;
  final int maxPossibleScore;
  final double percentageScore;
  final int correctAnswers;
  final int incorrectAnswers;
  final DateTime startedAt;
  final DateTime? completedAt;
  final double? durationMinutes;

  const GameSummaryResponse({
    required this.sessionId,
    required this.topic,
    required this.totalQuestions,
    required this.answeredQuestions,
    required this.totalScore,
    required this.maxPossibleScore,
    required this.percentageScore,
    required this.correctAnswers,
    required this.incorrectAnswers,
    required this.startedAt,
    this.completedAt,
    this.durationMinutes,
  });

  /// Create from JSON
  factory GameSummaryResponse.fromJson(Map<String, dynamic> json) {
    return GameSummaryResponse(
      sessionId: json['session_id'] as String,
      topic: json['topic'] as String,
      totalQuestions: json['total_questions'] as int,
      answeredQuestions: json['answered_questions'] as int,
      totalScore: json['total_score'] as int,
      maxPossibleScore: json['max_possible_score'] as int,
      percentageScore: (json['percentage_score'] as num).toDouble(),
      correctAnswers: json['correct_answers'] as int,
      incorrectAnswers: json['incorrect_answers'] as int,
      startedAt: DateTime.parse(json['started_at'] as String),
      completedAt: json['completed_at'] != null
          ? DateTime.parse(json['completed_at'] as String)
          : null,
      durationMinutes: json['duration_minutes'] != null
          ? (json['duration_minutes'] as num).toDouble()
          : null,
    );
  }

  /// Check if game was completed
  bool get isCompleted => completedAt != null;

  /// Get completion percentage
  double get completionPercentage {
    if (totalQuestions == 0) return 0.0;
    return (answeredQuestions / totalQuestions) * 100.0;
  }

  /// Get accuracy percentage
  double get accuracyPercentage {
    if (answeredQuestions == 0) return 0.0;
    return (correctAnswers / answeredQuestions) * 100.0;
  }

  /// Get performance grade
  String get performanceGrade {
    if (percentageScore >= 90) return 'A+';
    if (percentageScore >= 85) return 'A';
    if (percentageScore >= 80) return 'A-';
    if (percentageScore >= 75) return 'B+';
    if (percentageScore >= 70) return 'B';
    if (percentageScore >= 65) return 'B-';
    if (percentageScore >= 60) return 'C+';
    if (percentageScore >= 55) return 'C';
    if (percentageScore >= 50) return 'C-';
    if (percentageScore >= 45) return 'D+';
    if (percentageScore >= 40) return 'D';
    return 'F';
  }

  /// Get performance color
  String get performanceColor {
    if (percentageScore >= 80) return '#4CAF50'; // Green
    if (percentageScore >= 60) return '#FF9800'; // Orange
    if (percentageScore >= 40) return '#FF5722'; // Deep Orange
    return '#F44336'; // Red
  }

  /// Get formatted duration
  String get formattedDuration {
    if (durationMinutes == null) return 'Unknown';
    
    final totalMinutes = durationMinutes!.round();
    final hours = totalMinutes ~/ 60;
    final minutes = totalMinutes % 60;
    
    if (hours > 0) {
      return '${hours}h ${minutes}m';
    } else {
      return '${minutes}m';
    }
  }

  /// Get time per question
  String get timePerQuestion {
    if (durationMinutes == null || answeredQuestions == 0) return 'Unknown';
    
    final secondsPerQuestion = (durationMinutes! * 60) / answeredQuestions;
    if (secondsPerQuestion < 60) {
      return '${secondsPerQuestion.round()}s';
    } else {
      return '${(secondsPerQuestion / 60).toStringAsFixed(1)}m';
    }
  }

  /// Check if performance is excellent (>= 90%)
  bool get isExcellent => percentageScore >= 90.0;

  /// Check if performance is good (>= 70%)
  bool get isGood => percentageScore >= 70.0;

  /// Check if performance needs improvement (< 60%)
  bool get needsImprovement => percentageScore < 60.0;

  /// Get unanswered questions count
  int get unansweredQuestions => totalQuestions - answeredQuestions;

  /// Check if all questions were answered
  bool get allQuestionsAnswered => answeredQuestions == totalQuestions;
}

/// Game health response model
class GameHealthResponse {
  final String status;
  final int activeSessions;
  final Map<String, dynamic> systemInfo;
  final List<String> recentErrors;

  const GameHealthResponse({
    required this.status,
    required this.activeSessions,
    required this.systemInfo,
    required this.recentErrors,
  });

  /// Create from JSON
  factory GameHealthResponse.fromJson(Map<String, dynamic> json) {
    return GameHealthResponse(
      status: json['status'] as String,
      activeSessions: json['active_sessions'] as int? ?? 0,
      systemInfo: json['system_info'] as Map<String, dynamic>? ?? {},
      recentErrors: json['recent_errors'] != null
          ? List<String>.from(json['recent_errors'] as List<dynamic>)
          : [],
    );
  }

  /// Check if game service is healthy
  bool get isHealthy => status.toLowerCase() == 'healthy';

  /// Check if there are recent errors
  bool get hasRecentErrors => recentErrors.isNotEmpty;

  /// Get system load indicator
  String get loadIndicator {
    if (activeSessions < 10) return 'Low';
    if (activeSessions < 50) return 'Medium';
    if (activeSessions < 100) return 'High';
    return 'Very High';
  }
}