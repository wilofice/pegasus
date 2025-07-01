enum QuestionType {
  singleChoice('SINGLE_CHOICE'),
  multipleChoice('MULTIPLE_CHOICE'),
  freeText('FREE_TEXT');

  const QuestionType(this.value);
  final String value;

  static QuestionType fromString(String value) {
    switch (value) {
      case 'SINGLE_CHOICE':
        return QuestionType.singleChoice;
      case 'MULTIPLE_CHOICE':
        return QuestionType.multipleChoice;
      case 'FREE_TEXT':
        return QuestionType.freeText;
      default:
        throw ArgumentError('Unknown question type: $value');
    }
  }
}

class Question {
  final String id;
  final String text;
  final QuestionType type;
  final List<String>? options;
  final String? hint;
  final String? difficulty;

  Question({
    required this.id,
    required this.text,
    required this.type,
    this.options,
    this.hint,
    this.difficulty,
  });

  factory Question.fromJson(Map<String, dynamic> json) {
    return Question(
      id: json['id'] as String,
      text: json['text'] as String,
      type: QuestionType.fromString(json['type'] as String),
      options: json['options'] != null 
          ? List<String>.from(json['options'] as List) 
          : null,
      hint: json['hint'] as String?,
      difficulty: json['difficulty'] as String?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'text': text,
      'type': type.value,
      if (options != null) 'options': options,
      if (hint != null) 'hint': hint,
      if (difficulty != null) 'difficulty': difficulty,
    };
  }
}

class UserAnswer {
  final String questionId;
  final List<String>? selectedOptions;
  final String? customText;

  UserAnswer({
    required this.questionId,
    this.selectedOptions,
    this.customText,
  });

  factory UserAnswer.fromJson(Map<String, dynamic> json) {
    return UserAnswer(
      questionId: json['question_id'] as String,
      selectedOptions: json['selected_options'] != null
          ? List<String>.from(json['selected_options'] as List)
          : null,
      customText: json['custom_text'] as String?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'question_id': questionId,
      if (selectedOptions != null) 'selected_options': selectedOptions,
      if (customText != null) 'custom_text': customText,
    };
  }
}

class ValidationResponse {
  final bool isCorrect;
  final String explanation;
  final String? correctAnswer;
  final int scorePoints;

  ValidationResponse({
    required this.isCorrect,
    required this.explanation,
    this.correctAnswer,
    required this.scorePoints,
  });

  factory ValidationResponse.fromJson(Map<String, dynamic> json) {
    return ValidationResponse(
      isCorrect: json['is_correct'] as bool,
      explanation: json['explanation'] as String,
      correctAnswer: json['correct_answer'] as String?,
      scorePoints: json['score_points'] as int,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'is_correct': isCorrect,
      'explanation': explanation,
      if (correctAnswer != null) 'correct_answer': correctAnswer,
      'score_points': scorePoints,
    };
  }
}

class GameStartRequest {
  final String topic;
  final int length;
  final String? difficulty;

  GameStartRequest({
    required this.topic,
    required this.length,
    this.difficulty,
  });

  Map<String, dynamic> toJson() {
    return {
      'topic': topic,
      'length': length,
      if (difficulty != null) 'difficulty': difficulty,
    };
  }
}

class GameStartResponse {
  final String sessionId;
  final Question firstQuestion;
  final int totalQuestions;

  GameStartResponse({
    required this.sessionId,
    required this.firstQuestion,
    required this.totalQuestions,
  });

  factory GameStartResponse.fromJson(Map<String, dynamic> json) {
    return GameStartResponse(
      sessionId: json['session_id'] as String,
      firstQuestion: Question.fromJson(json['first_question'] as Map<String, dynamic>),
      totalQuestions: json['total_questions'] as int,
    );
  }
}

class GameAnswerRequest {
  final UserAnswer answer;

  GameAnswerRequest({required this.answer});

  Map<String, dynamic> toJson() {
    return {
      'answer': answer.toJson(),
    };
  }
}

class GameAnswerResponse {
  final ValidationResponse validation;
  final Question? nextQuestion;
  final bool gameCompleted;
  final int currentScore;
  final Map<String, int> progress;

  GameAnswerResponse({
    required this.validation,
    this.nextQuestion,
    required this.gameCompleted,
    required this.currentScore,
    required this.progress,
  });

  factory GameAnswerResponse.fromJson(Map<String, dynamic> json) {
    return GameAnswerResponse(
      validation: ValidationResponse.fromJson(json['validation'] as Map<String, dynamic>),
      nextQuestion: json['next_question'] != null
          ? Question.fromJson(json['next_question'] as Map<String, dynamic>)
          : null,
      gameCompleted: json['game_completed'] as bool,
      currentScore: json['current_score'] as int,
      progress: Map<String, int>.from(json['progress'] as Map),
    );
  }
}

class GameSummary {
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

  GameSummary({
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

  factory GameSummary.fromJson(Map<String, dynamic> json) {
    return GameSummary(
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
}

class GameProgress {
  final int current;
  final int total;
  final int remaining;

  GameProgress({
    required this.current,
    required this.total,
    required this.remaining,
  });

  factory GameProgress.fromMap(Map<String, int> map) {
    return GameProgress(
      current: map['current'] ?? 0,
      total: map['total'] ?? 0,
      remaining: map['remaining'] ?? 0,
    );
  }

  double get percentage => total > 0 ? (current / total) * 100 : 0;
}