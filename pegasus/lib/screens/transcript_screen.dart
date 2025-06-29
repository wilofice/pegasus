import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../api/pegasus_api_client.dart';

// Providers for transcript screen
final transcriptDataProvider = StateProvider<Map<String, dynamic>?>((ref) => null);
final isLoadingProvider = StateProvider<bool>((ref) => true);
final selectedTagProvider = StateProvider<String?>((ref) => null);
final availableTagsProvider = StateProvider<List<String>>((ref) => []);
final customTagControllerProvider = StateProvider<TextEditingController>((ref) => TextEditingController());

class TranscriptScreen extends ConsumerStatefulWidget {
  final String audioId;
  
  const TranscriptScreen({Key? key, required this.audioId}) : super(key: key);

  @override
  ConsumerState<TranscriptScreen> createState() => _TranscriptScreenState();
}

class _TranscriptScreenState extends ConsumerState<TranscriptScreen> with TickerProviderStateMixin {
  final PegasusApiClient _apiClient = PegasusApiClient(baseUrl: 'http://192.168.1.15:9000', token: 'empty');
  late TabController _tabController;
  
  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _loadData();
    });
  }
  
  @override
  void dispose() {
    _tabController.dispose();
    ref.read(customTagControllerProvider).dispose();
    super.dispose();
  }
  
  Future<void> _loadData() async {
    ref.read(isLoadingProvider.notifier).state = true;
    
    try {
      // Load transcript data
      final transcriptData = await _apiClient.getTranscript(widget.audioId);
      ref.read(transcriptDataProvider.notifier).state = transcriptData;
      
      // Load audio file details to get current tag
      final audioData = await _apiClient.getAudioFile(widget.audioId);
      if (audioData != null && audioData['tag'] != null) {
        ref.read(selectedTagProvider.notifier).state = audioData['tag'] as String;
      }
      
      // Load available tags
      final tagsData = await _apiClient.getAvailableTags();
      ref.read(availableTagsProvider.notifier).state = tagsData['tags'] ?? [];
      
    } catch (e) {
      _showErrorSnackBar('Failed to load transcript: $e');
    } finally {
      ref.read(isLoadingProvider.notifier).state = false;
    }
  }
  
  Future<void> _saveTag() async {
    final selectedTag = ref.read(selectedTagProvider);
    final customController = ref.read(customTagControllerProvider);
    
    String? tagToSave;
    if (selectedTag != null && selectedTag.isNotEmpty) {
      tagToSave = selectedTag;
    } else if (customController.text.isNotEmpty) {
      tagToSave = customController.text.trim();
    }
    
    if (tagToSave == null || tagToSave.isEmpty) {
      _showErrorSnackBar('Please select or enter a tag');
      return;
    }
    
    try {
      final success = await _apiClient.updateAudioTags(widget.audioId, tag: tagToSave);
      if (success) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Tag "$tagToSave" saved successfully'),
            backgroundColor: Colors.green,
          ),
        );
        
        // Add to available tags if it's new
        final availableTags = ref.read(availableTagsProvider);
        if (!availableTags.contains(tagToSave)) {
          ref.read(availableTagsProvider.notifier).state = [...availableTags, tagToSave];
        }
      } else {
        _showErrorSnackBar('Failed to save tag');
      }
    } catch (e) {
      _showErrorSnackBar('Error saving tag: $e');
    }
  }
  
  void _copyToClipboard(String text) {
    Clipboard.setData(ClipboardData(text: text));
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Copied to clipboard'),
        duration: Duration(seconds: 2),
      ),
    );
  }
  
  void _showErrorSnackBar(String message) {
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(message),
          backgroundColor: Colors.red,
        ),
      );
    }
  }
  
  @override
  Widget build(BuildContext context) {
    final isLoading = ref.watch(isLoadingProvider);
    final transcriptData = ref.watch(transcriptDataProvider);
    final selectedTag = ref.watch(selectedTagProvider);
    final availableTags = ref.watch(availableTagsProvider);
    final customController = ref.watch(customTagControllerProvider);
    
    if (isLoading) {
      return Scaffold(
        appBar: AppBar(
          title: const Text('Loading...'),
        ),
        body: const Center(
          child: CircularProgressIndicator(),
        ),
      );
    }
    
    if (transcriptData == null) {
      return Scaffold(
        appBar: AppBar(
          title: const Text('Transcript'),
        ),
        body: const Center(
          child: Text('No transcript available'),
        ),
      );
    }
    
    return Scaffold(
      appBar: AppBar(
        title: const Text('Transcript & Tags'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
        bottom: TabBar(
          controller: _tabController,
          tabs: const [
            Tab(icon: Icon(Icons.text_snippet), text: 'Transcript'),
            Tab(icon: Icon(Icons.tag), text: 'Tags'),
          ],
        ),
      ),
      body: TabBarView(
        controller: _tabController,
        children: [
          _buildTranscriptTab(transcriptData),
          _buildTagsTab(selectedTag, availableTags, customController),
        ],
      ),
    );
  }
  
  Widget _buildTranscriptTab(Map<String, dynamic> transcriptData) {
    final status = transcriptData['status'] as String?;
    final originalTranscript = transcriptData['transcript'] as String?;
    final isImproved = transcriptData['is_improved'] as bool? ?? false;
    
    if (status != 'completed') {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const CircularProgressIndicator(),
            const SizedBox(height: 16),
            Text(
              'Processing status: ${status ?? 'Unknown'}',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            if (transcriptData['message'] != null)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Text(
                  transcriptData['message'] as String,
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
              ),
          ],
        ),
      );
    }
    
    if (originalTranscript == null || originalTranscript.isEmpty) {
      return const Center(
        child: Text('No transcript available'),
      );
    }
    
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Transcript type indicator
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
            decoration: BoxDecoration(
              color: isImproved ? Colors.green.withValues(alpha: 0.1) : Colors.blue.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(
                color: isImproved ? Colors.green : Colors.blue,
                width: 1,
              ),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(
                  isImproved ? Icons.auto_fix_high : Icons.mic,
                  size: 16,
                  color: isImproved ? Colors.green : Colors.blue,
                ),
                const SizedBox(width: 6),
                Text(
                  isImproved ? 'AI-Improved Transcript' : 'Original Transcript',
                  style: TextStyle(
                    color: isImproved ? Colors.green : Colors.blue,
                    fontWeight: FontWeight.w600,
                    fontSize: 12,
                  ),
                ),
              ],
            ),
          ),
          
          const SizedBox(height: 16),
          
          // Transcript text
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Theme.of(context).colorScheme.surfaceContainerHighest.withValues(alpha: 0.3),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                color: Theme.of(context).colorScheme.outline.withValues(alpha: 0.3),
              ),
            ),
            child: SelectableText(
              originalTranscript,
              style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                height: 1.6,
              ),
            ),
          ),
          
          const SizedBox(height: 16),
          
          // Action buttons
          Row(
            children: [
              Expanded(
                child: ElevatedButton.icon(
                  onPressed: () => _copyToClipboard(originalTranscript),
                  icon: const Icon(Icons.copy),
                  label: const Text('Copy to Clipboard'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.blue,
                    foregroundColor: Colors.white,
                  ),
                ),
              ),
            ],
          ),
          
          // Transcript metadata
          if (transcriptData['transcription_engine'] != null) ...[
            const SizedBox(height: 24),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Theme.of(context).colorScheme.surfaceContainerHighest.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Transcription Details',
                    style: Theme.of(context).textTheme.titleSmall?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text('Engine: ${transcriptData['transcription_engine']}'),
                  if (isImproved) Text('Enhanced: Yes'),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }
  
  Widget _buildTagsTab(String? selectedTag, List<String> availableTags, TextEditingController customController) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Tag this audio recording',
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'Tags help organize your audio files and enable special processing based on the content type.',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
              color: Theme.of(context).colorScheme.onSurface.withValues(alpha: 0.7),
            ),
          ),
          
          const SizedBox(height: 24),
          
          // Current tag display
          if (selectedTag != null && selectedTag.isNotEmpty) ...[
            Text(
              'Current Tag:',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 8),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              decoration: BoxDecoration(
                color: Colors.green.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(20),
                border: Border.all(color: Colors.green),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(Icons.tag, size: 16, color: Colors.green),
                  const SizedBox(width: 6),
                  Text(
                    selectedTag,
                    style: const TextStyle(
                      color: Colors.green,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 24),
          ],
          
          // Quick select tags
          if (availableTags.isNotEmpty) ...[
            Text(
              'Quick Select:',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: availableTags.map((tag) {
                final isSelected = tag == selectedTag;
                return FilterChip(
                  label: Text(tag),
                  selected: isSelected,
                  onSelected: (selected) {
                    if (selected) {
                      ref.read(selectedTagProvider.notifier).state = tag;
                      customController.clear();
                    } else {
                      ref.read(selectedTagProvider.notifier).state = null;
                    }
                  },
                  backgroundColor: isSelected ? Colors.blue.withValues(alpha: 0.1) : null,
                  selectedColor: Colors.blue.withValues(alpha: 0.2),
                  checkmarkColor: Colors.blue,
                );
              }).toList(),
            ),
            const SizedBox(height: 24),
          ],
          
          // Custom tag input
          Text(
            'Or create a new tag:',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: customController,
            decoration: const InputDecoration(
              labelText: 'Enter custom tag',
              hintText: 'e.g., Work, Family, Meeting, Groceries',
              border: OutlineInputBorder(),
              prefixIcon: Icon(Icons.tag),
            ),
            onChanged: (value) {
              if (value.isNotEmpty) {
                ref.read(selectedTagProvider.notifier).state = null;
              }
            },
            onSubmitted: (value) {
              if (value.isNotEmpty) {
                _saveTag();
              }
            },
          ),
          
          const SizedBox(height: 24),
          
          // Common tag suggestions
          Text(
            'Suggested Tags:',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: ['Work', 'Family', 'Meeting', 'Groceries', 'Personal', 'Ideas', 'Notes']
                .where((tag) => !availableTags.contains(tag))
                .map((tag) {
              return ActionChip(
                label: Text(tag),
                onPressed: () {
                  ref.read(selectedTagProvider.notifier).state = tag;
                  customController.clear();
                },
                backgroundColor: Colors.grey.withValues(alpha: 0.1),
              );
            }).toList(),
          ),
          
          const SizedBox(height: 32),
          
          // Save button
          SizedBox(
            width: double.infinity,
            child: ElevatedButton.icon(
              onPressed: _saveTag,
              icon: const Icon(Icons.save),
              label: const Text('Save Tag'),
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.green,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(vertical: 16),
              ),
            ),
          ),
          
          const SizedBox(height: 16),
          
          // Info box
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.blue.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: Colors.blue.withValues(alpha: 0.3)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(Icons.info_outline, color: Colors.blue, size: 20),
                    const SizedBox(width: 8),
                    Text(
                      'Tag-based Processing',
                      style: Theme.of(context).textTheme.titleSmall?.copyWith(
                        fontWeight: FontWeight.bold,
                        color: Colors.blue,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Text(
                  'Different tags will trigger specialized processing:\n'
                  '• Work: Meeting summaries and action items\n'
                  '• Family: Personal notes and reminders\n'
                  '• Groceries: Shopping list extraction\n'
                  '• And more coming soon!',
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: Colors.blue.withValues(alpha: 0.8),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}