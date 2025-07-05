/// Confidence Indicator Widget for Response Quality
/// 
/// This widget displays confidence scores for AI responses with:
/// - Visual progress indicators
/// - Color-coded confidence levels
/// - Tooltip explanations
/// - Multiple size variants

import 'package:flutter/material.dart';

enum ConfidenceIndicatorSize {
  small,
  medium,
  large,
}

class ConfidenceIndicator extends StatelessWidget {
  final double confidence;
  final ConfidenceIndicatorSize size;
  final bool showLabel;
  final bool showTooltip;
  final String? customLabel;

  const ConfidenceIndicator({
    super.key,
    required this.confidence,
    this.size = ConfidenceIndicatorSize.medium,
    this.showLabel = true,
    this.showTooltip = true,
    this.customLabel,
  });

  @override
  Widget build(BuildContext context) {
    final widget = _buildIndicator(context);
    
    if (showTooltip) {
      return Tooltip(
        message: _getTooltipMessage(),
        child: widget,
      );
    } else {
      return widget;
    }
  }

  Widget _buildIndicator(BuildContext context) {
    final dimensions = _getDimensions();
    final color = _getConfidenceColor();
    
    return Container(
      padding: EdgeInsets.symmetric(
        horizontal: dimensions.padding,
        vertical: dimensions.padding * 0.5,
      ),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(dimensions.borderRadius),
        border: Border.all(
          color: color.withOpacity(0.3),
          width: 1,
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Confidence icon
          Icon(
            _getConfidenceIcon(),
            size: dimensions.iconSize,
            color: color,
          ),
          
          SizedBox(width: dimensions.spacing),
          
          // Progress indicator
          Container(
            width: dimensions.progressWidth,
            height: dimensions.progressHeight,
            decoration: BoxDecoration(
              color: Colors.grey.shade200,
              borderRadius: BorderRadius.circular(dimensions.progressHeight / 2),
            ),
            child: FractionallySizedBox(
              alignment: Alignment.centerLeft,
              widthFactor: confidence.clamp(0.0, 1.0),
              child: Container(
                decoration: BoxDecoration(
                  color: color,
                  borderRadius: BorderRadius.circular(dimensions.progressHeight / 2),
                ),
              ),
            ),
          ),
          
          // Label
          if (showLabel) ...[
            SizedBox(width: dimensions.spacing),
            Text(
              customLabel ?? _getConfidenceLabel(),
              style: TextStyle(
                fontSize: dimensions.fontSize,
                fontWeight: FontWeight.w500,
                color: color,
              ),
            ),
          ],
        ],
      ),
    );
  }

  IndicatorDimensions _getDimensions() {
    switch (size) {
      case ConfidenceIndicatorSize.small:
        return const IndicatorDimensions(
          iconSize: 12,
          fontSize: 10,
          progressWidth: 30,
          progressHeight: 3,
          padding: 4,
          spacing: 4,
          borderRadius: 8,
        );
      case ConfidenceIndicatorSize.medium:
        return const IndicatorDimensions(
          iconSize: 16,
          fontSize: 12,
          progressWidth: 40,
          progressHeight: 4,
          padding: 6,
          spacing: 6,
          borderRadius: 10,
        );
      case ConfidenceIndicatorSize.large:
        return const IndicatorDimensions(
          iconSize: 20,
          fontSize: 14,
          progressWidth: 60,
          progressHeight: 6,
          padding: 8,
          spacing: 8,
          borderRadius: 12,
        );
    }
  }

  Color _getConfidenceColor() {
    if (confidence >= 0.9) return Colors.green.shade600;
    if (confidence >= 0.8) return Colors.green.shade400;
    if (confidence >= 0.7) return Colors.lime.shade600;
    if (confidence >= 0.6) return Colors.orange.shade500;
    if (confidence >= 0.5) return Colors.orange.shade700;
    if (confidence >= 0.4) return Colors.red.shade400;
    return Colors.red.shade600;
  }

  IconData _getConfidenceIcon() {
    if (confidence >= 0.8) return Icons.check_circle;
    if (confidence >= 0.6) return Icons.info;
    if (confidence >= 0.4) return Icons.warning;
    return Icons.error;
  }

  String _getConfidenceLabel() {
    final percentage = (confidence * 100).round();
    return '$percentage%';
  }

  String _getTooltipMessage() {
    final percentage = (confidence * 100).round();
    final level = _getConfidenceLevel();
    
    return 'Confidence: $percentage% ($level)\n'
           'This indicates how certain the AI is about the response accuracy.';
  }

  String _getConfidenceLevel() {
    if (confidence >= 0.9) return 'Very High';
    if (confidence >= 0.8) return 'High';
    if (confidence >= 0.7) return 'Good';
    if (confidence >= 0.6) return 'Moderate';
    if (confidence >= 0.5) return 'Fair';
    if (confidence >= 0.4) return 'Low';
    return 'Very Low';
  }
}

class IndicatorDimensions {
  final double iconSize;
  final double fontSize;
  final double progressWidth;
  final double progressHeight;
  final double padding;
  final double spacing;
  final double borderRadius;

  const IndicatorDimensions({
    required this.iconSize,
    required this.fontSize,
    required this.progressWidth,
    required this.progressHeight,
    required this.padding,
    required this.spacing,
    required this.borderRadius,
  });
}

/// Confidence Level Badge - Simplified version for compact display
class ConfidenceBadge extends StatelessWidget {
  final double confidence;
  final bool showPercentage;

  const ConfidenceBadge({
    super.key,
    required this.confidence,
    this.showPercentage = true,
  });

  @override
  Widget build(BuildContext context) {
    final color = _getConfidenceColor();
    final level = _getConfidenceLevel();
    
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(
          color: color.withOpacity(0.3),
          width: 1,
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            _getConfidenceIcon(),
            size: 10,
            color: color,
          ),
          const SizedBox(width: 3),
          Text(
            showPercentage 
                ? '${(confidence * 100).round()}%'
                : level,
            style: TextStyle(
              fontSize: 9,
              fontWeight: FontWeight.w600,
              color: color,
            ),
          ),
        ],
      ),
    );
  }

  Color _getConfidenceColor() {
    if (confidence >= 0.8) return Colors.green;
    if (confidence >= 0.6) return Colors.orange;
    if (confidence >= 0.4) return Colors.red;
    return Colors.grey;
  }

  IconData _getConfidenceIcon() {
    if (confidence >= 0.8) return Icons.check_circle;
    if (confidence >= 0.6) return Icons.info;
    if (confidence >= 0.4) return Icons.warning;
    return Icons.error;
  }

  String _getConfidenceLevel() {
    if (confidence >= 0.9) return 'High';
    if (confidence >= 0.7) return 'Good';
    if (confidence >= 0.5) return 'Fair';
    if (confidence >= 0.3) return 'Low';
    return 'Poor';
  }
}

/// Animated Confidence Meter for detailed views
class ConfidenceMeter extends StatefulWidget {
  final double confidence;
  final String title;
  final bool animated;

  const ConfidenceMeter({
    super.key,
    required this.confidence,
    this.title = 'Response Confidence',
    this.animated = true,
  });

  @override
  State<ConfidenceMeter> createState() => _ConfidenceMeterState();
}

class _ConfidenceMeterState extends State<ConfidenceMeter>
    with SingleTickerProviderStateMixin {
  late AnimationController _animationController;
  late Animation<double> _animation;

  @override
  void initState() {
    super.initState();
    _animationController = AnimationController(
      duration: const Duration(milliseconds: 1000),
      vsync: this,
    );
    _animation = Tween<double>(
      begin: 0.0,
      end: widget.confidence,
    ).animate(CurvedAnimation(
      parent: _animationController,
      curve: Curves.easeInOut,
    ));

    if (widget.animated) {
      _animationController.forward();
    }
  }

  @override
  void dispose() {
    _animationController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _animation,
      builder: (context, child) {
        final currentValue = widget.animated ? _animation.value : widget.confidence;
        final color = _getConfidenceColor(currentValue);
        
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              widget.title,
              style: const TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.w500,
              ),
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(
                  child: Container(
                    height: 8,
                    decoration: BoxDecoration(
                      color: Colors.grey.shade200,
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: FractionallySizedBox(
                      alignment: Alignment.centerLeft,
                      widthFactor: currentValue.clamp(0.0, 1.0),
                      child: Container(
                        decoration: BoxDecoration(
                          color: color,
                          borderRadius: BorderRadius.circular(4),
                        ),
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Text(
                  '${(currentValue * 100).round()}%',
                  style: TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                    color: color,
                  ),
                ),
              ],
            ),
          ],
        );
      },
    );
  }

  Color _getConfidenceColor(double confidence) {
    if (confidence >= 0.8) return Colors.green;
    if (confidence >= 0.6) return Colors.orange;
    if (confidence >= 0.4) return Colors.red;
    return Colors.grey;
  }
}