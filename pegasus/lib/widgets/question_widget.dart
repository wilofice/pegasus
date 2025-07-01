import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/game_model.dart';
import '../providers/game_provider.dart';

class QuestionWidget extends ConsumerStatefulWidget {
  final Question question;
  final VoidCallback? onAnswerChanged;

  const QuestionWidget({
    super.key,
    required this.question,
    this.onAnswerChanged,
  });

  @override
  ConsumerState<QuestionWidget> createState() => _QuestionWidgetState();
}

class _QuestionWidgetState extends ConsumerState<QuestionWidget> {
  late TextEditingController _textController;

  @override
  void initState() {
    super.initState();
    _textController = TextEditingController();
  }

  @override
  void dispose() {
    _textController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final userAnswerState = ref.watch(userAnswerStateProvider);
    final gameNotifier = ref.read(gameProvider.notifier);

    return Card(
      elevation: 4,
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Question text
            Text(
              widget.question.text,
              style: const TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
            ),
            
            // Question hint
            if (widget.question.hint != null) ...[
              const SizedBox(height: 8),
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: Colors.blue.shade50,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: Colors.blue.shade200),
                ),
                child: Row(
                  children: [
                    Icon(Icons.lightbulb_outline, 
                         color: Colors.blue.shade600, size: 16),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        'Hint: ${widget.question.hint}',
                        style: TextStyle(
                          fontSize: 14,
                          color: Colors.blue.shade700,
                          fontStyle: FontStyle.italic,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
            
            const SizedBox(height: 16),
            
            // Question type badge
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: BoxDecoration(
                color: _getQuestionTypeColor().withOpacity(0.1),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: _getQuestionTypeColor().withOpacity(0.3)),
              ),
              child: Text(
                _getQuestionTypeLabel(),
                style: TextStyle(
                  fontSize: 12,
                  color: _getQuestionTypeColor(),
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
            
            const SizedBox(height: 16),
            
            // Answer input based on question type
            Expanded(
              child: _buildAnswerInput(userAnswerState, gameNotifier),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildAnswerInput(UserAnswerState userAnswerState, GameNotifier gameNotifier) {
    switch (widget.question.type) {
      case QuestionType.singleChoice:
        return _buildSingleChoiceInput(userAnswerState, gameNotifier);
      case QuestionType.multipleChoice:
        return _buildMultipleChoiceInput(userAnswerState, gameNotifier);
      case QuestionType.freeText:
        return _buildFreeTextInput(userAnswerState, gameNotifier);
    }
  }

  Widget _buildSingleChoiceInput(UserAnswerState userAnswerState, GameNotifier gameNotifier) {
    final options = widget.question.options ?? [];
    final selectedOption = userAnswerState.selectedOptions.isNotEmpty
        ? userAnswerState.selectedOptions.first
        : null;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Select one option:',
          style: TextStyle(fontSize: 16, fontWeight: FontWeight.w500),
        ),
        const SizedBox(height: 12),
        Expanded(
          child: ListView.builder(
            itemCount: options.length,
            itemBuilder: (context, index) {
              final option = options[index];
              final isSelected = selectedOption == option;
              
              return Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Container(
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(
                      color: isSelected 
                          ? Theme.of(context).primaryColor 
                          : Colors.grey.shade300,
                      width: isSelected ? 2 : 1,
                    ),
                    color: isSelected 
                        ? Theme.of(context).primaryColor.withOpacity(0.1)
                        : null,
                  ),
                  child: RadioListTile<String>(
                    title: Text(option),
                    value: option,
                    groupValue: selectedOption,
                    onChanged: (value) {
                      if (value != null) {
                        gameNotifier.selectSingleOption(value);
                        widget.onAnswerChanged?.call();
                      }
                    },
                    activeColor: Theme.of(context).primaryColor,
                  ),
                ),
              );
            },
          ),
        ),
      ],
    );
  }

  Widget _buildMultipleChoiceInput(UserAnswerState userAnswerState, GameNotifier gameNotifier) {
    final options = widget.question.options ?? [];
    final selectedOptions = userAnswerState.selectedOptions;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Select one or more options:',
          style: TextStyle(fontSize: 16, fontWeight: FontWeight.w500),
        ),
        const SizedBox(height: 12),
        Expanded(
          child: ListView.builder(
            itemCount: options.length,
            itemBuilder: (context, index) {
              final option = options[index];
              final isSelected = selectedOptions.contains(option);
              
              return Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Container(
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(
                      color: isSelected 
                          ? Theme.of(context).primaryColor 
                          : Colors.grey.shade300,
                      width: isSelected ? 2 : 1,
                    ),
                    color: isSelected 
                        ? Theme.of(context).primaryColor.withOpacity(0.1)
                        : null,
                  ),
                  child: CheckboxListTile(
                    title: Text(option),
                    value: isSelected,
                    onChanged: (checked) {
                      gameNotifier.toggleOption(option);
                      widget.onAnswerChanged?.call();
                    },
                    activeColor: Theme.of(context).primaryColor,
                  ),
                ),
              );
            },
          ),
        ),
        if (selectedOptions.isNotEmpty) ...[
          const SizedBox(height: 8),
          Text(
            'Selected: ${selectedOptions.length} option${selectedOptions.length != 1 ? 's' : ''}',
            style: TextStyle(
              fontSize: 14,
              color: Theme.of(context).primaryColor,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ],
    );
  }

  Widget _buildFreeTextInput(UserAnswerState userAnswerState, GameNotifier gameNotifier) {
    // Update text controller if the state changes externally
    if (_textController.text != (userAnswerState.customText ?? '')) {
      _textController.text = userAnswerState.customText ?? '';
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Enter your answer:',
          style: TextStyle(fontSize: 16, fontWeight: FontWeight.w500),
        ),
        const SizedBox(height: 12),
        Expanded(
          child: TextField(
            controller: _textController,
            maxLines: null,
            expands: true,
            textAlignVertical: TextAlignVertical.top,
            decoration: const InputDecoration(
              hintText: 'Type your answer here...',
              border: OutlineInputBorder(),
              contentPadding: EdgeInsets.all(16),
            ),
            onChanged: (text) {
              gameNotifier.updateCustomText(text);
              widget.onAnswerChanged?.call();
            },
          ),
        ),
        const SizedBox(height: 8),
        Text(
          'Characters: ${_textController.text.length}',
          style: TextStyle(
            fontSize: 12,
            color: Colors.grey.shade600,
          ),
        ),
      ],
    );
  }

  Color _getQuestionTypeColor() {
    switch (widget.question.type) {
      case QuestionType.singleChoice:
        return Colors.blue;
      case QuestionType.multipleChoice:
        return Colors.green;
      case QuestionType.freeText:
        return Colors.orange;
    }
  }

  String _getQuestionTypeLabel() {
    switch (widget.question.type) {
      case QuestionType.singleChoice:
        return 'Single Choice';
      case QuestionType.multipleChoice:
        return 'Multiple Choice';
      case QuestionType.freeText:
        return 'Free Text';
    }
  }
}