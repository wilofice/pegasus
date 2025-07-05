// Suggestion Chips Widget for Follow-up Questions
// 
// This widget displays interactive suggestion chips that users can tap
// to continue conversations with relevant follow-up questions.
// Features include:
// - Animated chip appearance
// - Category-based styling
// - Smart suggestion filtering
// - Custom action handling

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

enum SuggestionCategory {
  followUp,
  clarification, 
  deepDive,
  related,
  action,
}

class SuggestionChipData {
  final String text;
  final SuggestionCategory category;
  final IconData? icon;
  final VoidCallback? onTap;
  final bool enabled;

  const SuggestionChipData({
    required this.text,
    required this.category,
    this.icon,
    this.onTap,
    this.enabled = true,
  });

  /// Get display color for category
  Color get categoryColor {
    switch (category) {
      case SuggestionCategory.followUp:
        return Colors.blue;
      case SuggestionCategory.clarification:
        return Colors.orange;
      case SuggestionCategory.deepDive:
        return Colors.purple;
      case SuggestionCategory.related:
        return Colors.green;
      case SuggestionCategory.action:
        return Colors.red;
    }
  }

  /// Get category label
  String get categoryLabel {
    switch (category) {
      case SuggestionCategory.followUp:
        return 'Follow-up';
      case SuggestionCategory.clarification:
        return 'Clarify';
      case SuggestionCategory.deepDive:
        return 'Deep Dive';
      case SuggestionCategory.related:
        return 'Related';
      case SuggestionCategory.action:
        return 'Action';
    }
  }
}

class SuggestionChips extends StatefulWidget {
  final List<SuggestionChipData> suggestions;
  final Function(SuggestionChipData)? onSuggestionTap;
  final bool showCategories;
  final bool animated;
  final EdgeInsets padding;
  final double spacing;
  final int? maxSuggestions;

  const SuggestionChips({
    super.key,
    required this.suggestions,
    this.onSuggestionTap,
    this.showCategories = false,
    this.animated = true,
    this.padding = const EdgeInsets.all(16),
    this.spacing = 8,
    this.maxSuggestions,
  });

  @override
  State<SuggestionChips> createState() => _SuggestionChipsState();
}

class _SuggestionChipsState extends State<SuggestionChips>
    with TickerProviderStateMixin {
  late List<AnimationController> _animationControllers;
  late List<Animation<double>> _scaleAnimations;
  late List<Animation<double>> _fadeAnimations;

  @override
  void initState() {
    super.initState();
    _initializeAnimations();
  }

  void _initializeAnimations() {
    final suggestionCount = widget.maxSuggestions != null
        ? widget.suggestions.length.clamp(0, widget.maxSuggestions!)
        : widget.suggestions.length;

    _animationControllers = List.generate(
      suggestionCount,
      (index) => AnimationController(
        duration: Duration(milliseconds: 300 + (index * 100)),
        vsync: this,
      ),
    );

    _scaleAnimations = _animationControllers.map((controller) =>
        Tween<double>(begin: 0.0, end: 1.0).animate(CurvedAnimation(
          parent: controller,
          curve: Curves.elasticOut,
        ))).toList();

    _fadeAnimations = _animationControllers.map((controller) =>
        Tween<double>(begin: 0.0, end: 1.0).animate(CurvedAnimation(
          parent: controller,
          curve: Curves.easeIn,
        ))).toList();

    if (widget.animated) {
      _startAnimations();
    } else {
      for (final controller in _animationControllers) {
        controller.value = 1.0;
      }
    }
  }

  void _startAnimations() {
    for (int i = 0; i < _animationControllers.length; i++) {
      Future.delayed(Duration(milliseconds: i * 100), () {
        if (mounted) {
          _animationControllers[i].forward();
        }
      });
    }
  }

  @override
  void dispose() {
    for (final controller in _animationControllers) {
      controller.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (widget.suggestions.isEmpty) {
      return const SizedBox.shrink();
    }

    final displaySuggestions = widget.maxSuggestions != null
        ? widget.suggestions.take(widget.maxSuggestions!).toList()
        : widget.suggestions;

    if (widget.showCategories) {
      return _buildCategorizedSuggestions(displaySuggestions);
    } else {
      return _buildSimpleSuggestions(displaySuggestions);
    }
  }

  Widget _buildSimpleSuggestions(List<SuggestionChipData> suggestions) {
    return Container(
      padding: widget.padding,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                Icons.lightbulb_outline,
                size: 16,
                color: Colors.amber.shade600,
              ),
              const SizedBox(width: 8),
              Text(
                'Suggested follow-ups',
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w500,
                  color: Colors.grey.shade700,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: widget.spacing,
            runSpacing: widget.spacing,
            children: suggestions.asMap().entries.map((entry) {
              final index = entry.key;
              final suggestion = entry.value;
              
              if (index < _animationControllers.length) {
                return AnimatedBuilder(
                  animation: _animationControllers[index],
                  builder: (context, child) {
                    return Transform.scale(
                      scale: _scaleAnimations[index].value,
                      child: Opacity(
                        opacity: _fadeAnimations[index].value,
                        child: _buildSuggestionChip(suggestion),
                      ),
                    );
                  },
                );
              } else {
                return _buildSuggestionChip(suggestion);
              }
            }).toList(),
          ),
        ],
      ),
    );
  }

  Widget _buildCategorizedSuggestions(List<SuggestionChipData> suggestions) {
    final groupedSuggestions = <SuggestionCategory, List<SuggestionChipData>>{};
    
    for (final suggestion in suggestions) {
      groupedSuggestions.putIfAbsent(suggestion.category, () => []);
      groupedSuggestions[suggestion.category]!.add(suggestion);
    }

    return Container(
      padding: widget.padding,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Suggestions by category',
            style: TextStyle(
              fontSize: 16,
              fontWeight: FontWeight.w600,
              color: Colors.grey.shade800,
            ),
          ),
          const SizedBox(height: 16),
          ...groupedSuggestions.entries.map((entry) => 
            _buildCategorySection(entry.key, entry.value),
          ),
        ],
      ),
    );
  }

  Widget _buildCategorySection(SuggestionCategory category, List<SuggestionChipData> suggestions) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 4,
                height: 16,
                decoration: BoxDecoration(
                  color: suggestions.first.categoryColor,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
              const SizedBox(width: 8),
              Text(
                suggestions.first.categoryLabel,
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w600,
                  color: suggestions.first.categoryColor,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: widget.spacing,
            runSpacing: widget.spacing,
            children: suggestions.map((suggestion) => 
              _buildSuggestionChip(suggestion),
            ).toList(),
          ),
        ],
      ),
    );
  }

  Widget _buildSuggestionChip(SuggestionChipData suggestion) {
    return ActionChip(
      label: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (suggestion.icon != null) ...[ 
            Icon(
              suggestion.icon,
              size: 16,
              color: suggestion.categoryColor,
            ),
            const SizedBox(width: 6),
          ],
          Flexible(
            child: Text(
              suggestion.text,
              style: TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.w500,
                color: suggestion.enabled 
                    ? suggestion.categoryColor
                    : Colors.grey.shade500,
              ),
            ),
          ),
        ],
      ),
      onPressed: suggestion.enabled 
          ? () => _handleSuggestionTap(suggestion)
          : null,
      backgroundColor: suggestion.enabled
          ? suggestion.categoryColor.withOpacity(0.1)
          : Colors.grey.shade100,
      side: BorderSide(
        color: suggestion.enabled
            ? suggestion.categoryColor.withOpacity(0.3)
            : Colors.grey.shade300,
        width: 1,
      ),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      elevation: suggestion.enabled ? 2 : 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(20),
      ),
    );
  }

  void _handleSuggestionTap(SuggestionChipData suggestion) {
    // Call custom handler first
    suggestion.onTap?.call();
    
    // Then call widget-level handler
    widget.onSuggestionTap?.call(suggestion);
    
    // Add visual feedback
    _provideTapFeedback();
  }

  void _provideTapFeedback() {
    HapticFeedback.lightImpact();
  }
}

/// Pre-built suggestion chips for common use cases
class CommonSuggestions {
  static List<SuggestionChipData> conversationStarters = [
    SuggestionChipData(
      text: "Tell me more about this",
      category: SuggestionCategory.followUp,
      icon: Icons.expand_more,
    ),
    SuggestionChipData(
      text: "Can you clarify that?",
      category: SuggestionCategory.clarification,
      icon: Icons.help_outline,
    ),
    SuggestionChipData(
      text: "Show me examples",
      category: SuggestionCategory.deepDive,
      icon: Icons.list_alt,
    ),
    SuggestionChipData(
      text: "What else should I know?",
      category: SuggestionCategory.related,
      icon: Icons.explore,
    ),
  ];

  static List<SuggestionChipData> technicalQuestions = [
    SuggestionChipData(
      text: "How does this work?",
      category: SuggestionCategory.deepDive,
      icon: Icons.settings,
    ),
    SuggestionChipData(
      text: "What are the alternatives?",
      category: SuggestionCategory.related,
      icon: Icons.compare_arrows,
    ),
    SuggestionChipData(
      text: "Show me the implementation",
      category: SuggestionCategory.action,
      icon: Icons.code,
    ),
    SuggestionChipData(
      text: "Are there any limitations?",
      category: SuggestionCategory.clarification,
      icon: Icons.warning_amber,
    ),
  ];

  static List<SuggestionChipData> contextualSuggestions(String topic) {
    return [
      SuggestionChipData(
        text: "More about $topic",
        category: SuggestionCategory.deepDive,
        icon: Icons.zoom_in,
      ),
      SuggestionChipData(
        text: "Related to $topic",
        category: SuggestionCategory.related,
        icon: Icons.link,
      ),
      SuggestionChipData(
        text: "Examples of $topic",
        category: SuggestionCategory.action,
        icon: Icons.playlist_add_check,
      ),
    ];
  }
}

/// Feedback chip for user actions
class FeedbackChips extends StatelessWidget {
  final VoidCallback? onThumbsUp;
  final VoidCallback? onThumbsDown;
  final VoidCallback? onShare;
  final VoidCallback? onSave;

  const FeedbackChips({
    super.key,
    this.onThumbsUp,
    this.onThumbsDown,
    this.onShare,
    this.onSave,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        if (onThumbsUp != null)
          IconButton(
            icon: const Icon(Icons.thumb_up_outlined, size: 18),
            onPressed: onThumbsUp,
            tooltip: 'Helpful',
            constraints: const BoxConstraints(),
            padding: const EdgeInsets.all(8),
          ),
        if (onThumbsDown != null)
          IconButton(
            icon: const Icon(Icons.thumb_down_outlined, size: 18),
            onPressed: onThumbsDown,
            tooltip: 'Not helpful',
            constraints: const BoxConstraints(),
            padding: const EdgeInsets.all(8),
          ),
        if (onShare != null)
          IconButton(
            icon: const Icon(Icons.share_outlined, size: 18),
            onPressed: onShare,
            tooltip: 'Share',
            constraints: const BoxConstraints(),
            padding: const EdgeInsets.all(8),
          ),
        if (onSave != null)
          IconButton(
            icon: const Icon(Icons.bookmark_border, size: 18),
            onPressed: onSave,
            tooltip: 'Save',
            constraints: const BoxConstraints(),
            padding: const EdgeInsets.all(8),
          ),
      ],
    );
  }
}