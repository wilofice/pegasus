/// Citation Card Widget for Source Attribution
/// 
/// This widget displays source information with metadata including:
/// - Source preview with metadata
/// - Relevance score display
/// - Link to original audio/transcript
/// - Timestamp information
/// - Audio playback from source

import 'package:flutter/material.dart';
import '../models/chat_v2_models.dart';

class CitationCard extends StatefulWidget {
  final SourceInfo source;
  final VoidCallback? onTap;
  final bool showRelevanceScore;
  final bool showMetadata;
  final bool compact;

  const CitationCard({
    super.key,
    required this.source,
    this.onTap,
    this.showRelevanceScore = true,
    this.showMetadata = true,
    this.compact = false,
  });

  @override
  State<CitationCard> createState() => _CitationCardState();
}

class _CitationCardState extends State<CitationCard> {
  bool _isExpanded = false;

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: InkWell(
        onTap: () {
          if (widget.compact) {
            setState(() => _isExpanded = !_isExpanded);
          }
          widget.onTap?.call();
        },
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _buildHeader(),
              const SizedBox(height: 8),
              _buildContent(),
              if (!widget.compact || _isExpanded) ...[
                if (widget.showMetadata) ...[
                  const SizedBox(height: 8),
                  _buildMetadata(),
                ],
                const SizedBox(height: 8),
                _buildActions(),
              ],
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return Row(
      children: [
        // Source type icon
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
          decoration: BoxDecoration(
            color: _getSourceTypeColor().withOpacity(0.1),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(
              color: _getSourceTypeColor().withOpacity(0.3),
              width: 1,
            ),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                _getSourceTypeIcon(),
                size: 14,
                color: _getSourceTypeColor(),
              ),
              const SizedBox(width: 4),
              Text(
                widget.source.sourceTypeDisplayName,
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w500,
                  color: _getSourceTypeColor(),
                ),
              ),
            ],
          ),
        ),
        
        const Spacer(),
        
        // Relevance score
        if (widget.showRelevanceScore)
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
            decoration: BoxDecoration(
              color: _getRelevanceColor().withOpacity(0.1),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Text(
              '${widget.source.relevancePercentage}%',
              style: TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w600,
                color: _getRelevanceColor(),
              ),
            ),
          ),
        
        // Expand button for compact mode
        if (widget.compact) ...[
          const SizedBox(width: 8),
          Icon(
            _isExpanded ? Icons.expand_less : Icons.expand_more,
            size: 20,
            color: Colors.grey.shade600,
          ),
        ],
      ],
    );
  }

  Widget _buildContent() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          widget.compact && !_isExpanded 
              ? widget.source.previewContent
              : widget.source.content,
          style: const TextStyle(
            fontSize: 14,
            height: 1.4,
          ),
          maxLines: widget.compact && !_isExpanded ? 2 : null,
          overflow: widget.compact && !_isExpanded 
              ? TextOverflow.ellipsis 
              : null,
        ),
      ],
    );
  }

  Widget _buildMetadata() {
    final metadataItems = <Widget>[];
    
    // Timestamp
    if (widget.source.formattedTimestamp != null) {
      metadataItems.add(
        _buildMetadataItem(
          Icons.access_time,
          'Date',
          widget.source.formattedTimestamp!,
        ),
      );
    }
    
    // Audio ID
    if (widget.source.audioId != null) {
      metadataItems.add(
        _buildMetadataItem(
          Icons.audiotrack,
          'Audio',
          '${widget.source.audioId!.substring(0, 8)}...',
        ),
      );
    }
    
    // Position
    if (widget.source.position != null) {
      metadataItems.add(
        _buildMetadataItem(
          Icons.location_on,
          'Position',
          widget.source.position!,
        ),
      );
    }

    if (metadataItems.isEmpty) return const SizedBox.shrink();

    return Container(
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: Colors.grey.shade50,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        children: [
          for (int i = 0; i < metadataItems.length; i++) ...[
            metadataItems[i],
            if (i < metadataItems.length - 1) 
              const SizedBox(height: 4),
          ],
        ],
      ),
    );
  }

  Widget _buildMetadataItem(IconData icon, String label, String value) {
    return Row(
      children: [
        Icon(
          icon,
          size: 14,
          color: Colors.grey.shade600,
        ),
        const SizedBox(width: 6),
        Text(
          '$label:',
          style: TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.w500,
            color: Colors.grey.shade700,
          ),
        ),
        const SizedBox(width: 4),
        Expanded(
          child: Text(
            value,
            style: TextStyle(
              fontSize: 12,
              color: Colors.grey.shade800,
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildActions() {
    return Row(
      children: [
        // View original button
        TextButton.icon(
          onPressed: _viewOriginal,
          icon: const Icon(Icons.open_in_new, size: 16),
          label: const Text('View Original'),
          style: TextButton.styleFrom(
            textStyle: const TextStyle(fontSize: 12),
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            minimumSize: Size.zero,
            tapTargetSize: MaterialTapTargetSize.shrinkWrap,
          ),
        ),
        
        const SizedBox(width: 8),
        
        // Play audio button (if audio source)
        if (widget.source.audioId != null)
          TextButton.icon(
            onPressed: _playAudio,
            icon: const Icon(Icons.play_arrow, size: 16),
            label: const Text('Play'),
            style: TextButton.styleFrom(
              textStyle: const TextStyle(fontSize: 12),
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              minimumSize: Size.zero,
              tapTargetSize: MaterialTapTargetSize.shrinkWrap,
            ),
          ),
        
        const Spacer(),
        
        // Relevance score badge (detailed view)
        if (!widget.compact)
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            decoration: BoxDecoration(
              color: _getRelevanceColor().withOpacity(0.1),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                color: _getRelevanceColor().withOpacity(0.3),
                width: 1,
              ),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(
                  Icons.trending_up,
                  size: 12,
                  color: _getRelevanceColor(),
                ),
                const SizedBox(width: 4),
                Text(
                  '${widget.source.relevancePercentage}% relevant',
                  style: TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.w500,
                    color: _getRelevanceColor(),
                  ),
                ),
              ],
            ),
          ),
      ],
    );
  }

  Color _getSourceTypeColor() {
    switch (widget.source.sourceType.toLowerCase()) {
      case 'vector':
        return Colors.blue;
      case 'graph':
        return Colors.green;
      case 'hybrid':
        return Colors.purple;
      case 'ensemble':
        return Colors.orange;
      default:
        return Colors.grey;
    }
  }

  IconData _getSourceTypeIcon() {
    switch (widget.source.sourceType.toLowerCase()) {
      case 'vector':
        return Icons.search;
      case 'graph':
        return Icons.account_tree;
      case 'hybrid':
        return Icons.merge_type;
      case 'ensemble':
        return Icons.auto_awesome;
      default:
        return Icons.source;
    }
  }

  Color _getRelevanceColor() {
    final score = widget.source.relevanceScore;
    if (score >= 0.8) return Colors.green;
    if (score >= 0.6) return Colors.orange;
    if (score >= 0.4) return Colors.red;
    return Colors.grey;
  }

  void _viewOriginal() {
    // Navigate to original source
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('Opening source: ${widget.source.id}'),
        duration: const Duration(seconds: 2),
      ),
    );
  }

  void _playAudio() {
    // Play audio from this source
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('Playing audio: ${widget.source.audioId}'),
        duration: const Duration(seconds: 2),
      ),
    );
  }
}