// Enhanced Message Bubble with Citations and Rich Formatting
// 
// This widget provides advanced message display capabilities including:
// - Rich markdown rendering
// - Citation footnotes with expandable details
// - Source attribution badges
// - Confidence score indicators
// - Copy/share functionality
// - Audio playback controls

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import '../models/chat_v2_models.dart';
import '../providers/chat_v2_provider.dart';
import 'citation_card.dart';
import 'confidence_indicator.dart';
import 'audio_player_widget.dart';

class EnhancedMessageBubble extends StatefulWidget {
  final EnhancedMessage message;
  final bool showTimestamp;
  final bool showConfidence;
  final VoidCallback? onCitationTap;
  final VoidCallback? onSourceTap;

  const EnhancedMessageBubble({
    super.key,
    required this.message,
    this.showTimestamp = true,
    this.showConfidence = true,
    this.onCitationTap,
    this.onSourceTap,
  });

  @override
  State<EnhancedMessageBubble> createState() => _EnhancedMessageBubbleState();
}

class _EnhancedMessageBubbleState extends State<EnhancedMessageBubble>
    with SingleTickerProviderStateMixin {
  bool _showSources = false;
  bool _showSuggestions = false;
  late AnimationController _animationController;
  late Animation<double> _fadeAnimation;

  @override
  void initState() {
    super.initState();
    _animationController = AnimationController(
      duration: const Duration(milliseconds: 300),
      vsync: this,
    );
    _fadeAnimation = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(parent: _animationController, curve: Curves.easeIn),
    );
    _animationController.forward();
  }

  @override
  void dispose() {
    _animationController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return FadeTransition(
      opacity: _fadeAnimation,
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 4, horizontal: 8),
        child: Row(
          mainAxisAlignment: widget.message.isUser 
              ? MainAxisAlignment.end 
              : MainAxisAlignment.start,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (!widget.message.isUser) ...[
              _buildAvatar(),
              const SizedBox(width: 8),
            ],
            Flexible(
              child: Column(
                crossAxisAlignment: widget.message.isUser 
                    ? CrossAxisAlignment.end 
                    : CrossAxisAlignment.start,
                children: [
                  _buildMessageBubble(),
                  if (widget.showTimestamp) _buildTimestamp(),
                  if (widget.message.hasSources && _showSources) 
                    _buildSourcesSection(),
                  if (widget.message.hasSuggestions && _showSuggestions) 
                    _buildSuggestionsSection(),
                ],
              ),
            ),
            if (widget.message.isUser) ...[
              const SizedBox(width: 8),
              _buildAvatar(),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildAvatar() {
    return Container(
      width: 32,
      height: 32,
      decoration: BoxDecoration(
        color: widget.message.isUser 
            ? Theme.of(context).primaryColor 
            : Colors.grey.shade300,
        borderRadius: BorderRadius.circular(16),
      ),
      child: Icon(
        widget.message.isUser ? Icons.person : Icons.smart_toy,
        color: widget.message.isUser 
            ? Colors.white 
            : Colors.grey.shade600,
        size: 18,
      ),
    );
  }

  Widget _buildMessageBubble() {
    return Container(
      constraints: BoxConstraints(
        maxWidth: MediaQuery.of(context).size.width * 0.75,
      ),
      decoration: BoxDecoration(
        color: widget.message.isUser
            ? Theme.of(context).primaryColor
            : Colors.grey.shade100,
        borderRadius: BorderRadius.circular(18).copyWith(
          bottomLeft: widget.message.isUser 
              ? const Radius.circular(18) 
              : const Radius.circular(4),
          bottomRight: widget.message.isUser 
              ? const Radius.circular(4) 
              : const Radius.circular(18),
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.05),
            blurRadius: 4,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildMessageContent(),
          if (!widget.message.isUser) _buildMessageActions(),
        ],
      ),
    );
  }

  Widget _buildMessageContent() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Main message content with markdown support
          _buildMessageText(),
          
          // Confidence indicator for AI responses
          if (!widget.message.isUser && 
              widget.showConfidence && 
              widget.message.confidenceScore != null)
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: ConfidenceIndicator(
                confidence: widget.message.confidenceScore!,
                size: ConfidenceIndicatorSize.small,
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildMessageText() {
    if (widget.message.isUser) {
      // Simple text for user messages
      return Text(
        widget.message.text,
        style: TextStyle(
          color: Colors.white,
          fontSize: 16,
        ),
      );
    } else {
      // Markdown rendering for AI responses
      return MarkdownBody(
        data: widget.message.text,
        selectable: true,
        styleSheet: MarkdownStyleSheet(
          p: const TextStyle(fontSize: 16, height: 1.4),
          strong: const TextStyle(fontWeight: FontWeight.bold),
          em: const TextStyle(fontStyle: FontStyle.italic),
          code: TextStyle(
            backgroundColor: Colors.grey.shade200,
            fontFamily: 'monospace',
            fontSize: 14,
          ),
          codeblockDecoration: BoxDecoration(
            color: Colors.grey.shade100,
            borderRadius: BorderRadius.circular(8),
          ),
          blockquoteDecoration: BoxDecoration(
            color: Colors.blue.shade50,
            border: Border(
              left: BorderSide(color: Colors.blue.shade300, width: 4),
            ),
          ),
        ),
        onTapLink: (text, href, title) {
          // Handle link taps
          if (href != null) {
            _handleLinkTap(href);
          }
        },
      );
    }
  }

  Widget _buildMessageActions() {
    if (widget.message.isUser) return const SizedBox.shrink();

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        border: Border(
          top: BorderSide(color: Colors.grey.shade200, width: 0.5),
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Copy button
          IconButton(
            icon: const Icon(Icons.copy, size: 16),
            onPressed: _copyMessage,
            tooltip: 'Copy message',
            constraints: const BoxConstraints(),
            padding: const EdgeInsets.all(4),
          ),
          
          // Share button
          IconButton(
            icon: const Icon(Icons.share, size: 16),
            onPressed: _shareMessage,
            tooltip: 'Share message',
            constraints: const BoxConstraints(),
            padding: const EdgeInsets.all(4),
          ),
          
          // Sources button
          if (widget.message.hasSources)
            IconButton(
              icon: Icon(
                _showSources ? Icons.source : Icons.source_outlined,
                size: 16,
                color: _showSources ? Theme.of(context).primaryColor : null,
              ),
              onPressed: () {
                setState(() => _showSources = !_showSources);
                widget.onSourceTap?.call();
              },
              tooltip: '${widget.message.sources?.length} sources',
              constraints: const BoxConstraints(),
              padding: const EdgeInsets.all(4),
            ),
          
          // Suggestions button
          if (widget.message.hasSuggestions)
            IconButton(
              icon: Icon(
                _showSuggestions ? Icons.lightbulb : Icons.lightbulb_outline,
                size: 16,
                color: _showSuggestions ? Colors.amber : null,
              ),
              onPressed: () {
                setState(() => _showSuggestions = !_showSuggestions);
              },
              tooltip: '${widget.message.suggestions?.length} suggestions',
              constraints: const BoxConstraints(),
              padding: const EdgeInsets.all(4),
            ),
          
          // Audio playback button
          IconButton(
            icon: const Icon(Icons.volume_up, size: 16),
            onPressed: _playAudio,
            tooltip: 'Play audio response',
            constraints: const BoxConstraints(),
            padding: const EdgeInsets.all(4),
          ),
        ],
      ),
    );
  }

  Widget _buildTimestamp() {
    return Padding(
      padding: const EdgeInsets.only(top: 4, left: 8, right: 8),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            widget.message.displayTime,
            style: TextStyle(
              fontSize: 12,
              color: Colors.grey.shade600,
            ),
          ),
          if (widget.message.processingTimeMs != null) ...[
            const SizedBox(width: 8),
            Icon(
              Icons.timer,
              size: 12,
              color: Colors.grey.shade600,
            ),
            const SizedBox(width: 2),
            Text(
              '${widget.message.processingTimeMs!.round()}ms',
              style: TextStyle(
                fontSize: 12,
                color: Colors.grey.shade600,
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildSourcesSection() {
    return Container(
      margin: const EdgeInsets.only(top: 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 8),
            child: Row(
              children: [
                Icon(
                  Icons.source,
                  size: 16,
                  color: Theme.of(context).primaryColor,
                ),
                const SizedBox(width: 4),
                Text(
                  'Sources (${widget.message.sources?.length})',
                  style: TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w500,
                    color: Theme.of(context).primaryColor,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 8),
          ...widget.message.sources!.map((source) => Padding(
            padding: const EdgeInsets.only(bottom: 4),
            child: CitationCard(
              source: source,
              onTap: () => widget.onCitationTap?.call(),
            ),
          )),
        ],
      ),
    );
  }

  Widget _buildSuggestionsSection() {
    return Container(
      margin: const EdgeInsets.only(top: 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 8),
            child: Row(
              children: [
                const Icon(
                  Icons.lightbulb,
                  size: 16,
                  color: Colors.amber,
                ),
                const SizedBox(width: 4),
                Text(
                  'Follow-up suggestions',
                  style: TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w500,
                    color: Colors.amber.shade700,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 4,
            children: widget.message.suggestions!.map((suggestion) => 
              ActionChip(
                label: Text(
                  suggestion,
                  style: const TextStyle(fontSize: 12),
                ),
                onPressed: () => _handleSuggestionTap(suggestion),
                backgroundColor: Colors.amber.shade50,
                side: BorderSide(color: Colors.amber.shade200),
                padding: const EdgeInsets.symmetric(horizontal: 8),
              ),
            ).toList(),
          ),
        ],
      ),
    );
  }

  void _copyMessage() {
    Clipboard.setData(ClipboardData(text: widget.message.text));
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Message copied to clipboard'),
        duration: Duration(seconds: 2),
      ),
    );
  }

  void _shareMessage() {
    // For now, copy to clipboard. In production, use share_plus package
    _copyMessage();
  }

  void _playAudio() {
    // Show audio player in a modal
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => Container(
        margin: const EdgeInsets.all(16),
        padding: const EdgeInsets.all(16),
        decoration: const BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.all(Radius.circular(16)),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.volume_up),
                const SizedBox(width: 8),
                const Text(
                  'Audio Response',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.w600),
                ),
                const Spacer(),
                IconButton(
                  icon: const Icon(Icons.close),
                  onPressed: () => Navigator.of(context).pop(),
                ),
              ],
            ),
            const SizedBox(height: 16),
            // For now, show a placeholder. In production, this would use
            // Text-to-Speech to generate audio from the message text
            AudioPlayerWidget(
              transcript: widget.message.text,
              showTranscript: true,
              showWaveform: true,
            ),
            const SizedBox(height: 16),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.blue.shade50,
                borderRadius: BorderRadius.circular(8),
              ),
              child: const Row(
                children: [
                  Icon(Icons.info_outline, size: 16),
                  SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      'Audio generation from text responses coming soon!',
                      style: TextStyle(fontSize: 12),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  void _handleLinkTap(String href) {
    // Handle markdown link taps
    print('Link tapped: $href');
  }

  void _handleSuggestionTap(String suggestion) {
    // In a real implementation, this would send the suggestion as a new message
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('Suggestion: $suggestion'),
        action: SnackBarAction(
          label: 'Send',
          onPressed: () {
            // Send suggestion as message
          },
        ),
      ),
    );
  }
}