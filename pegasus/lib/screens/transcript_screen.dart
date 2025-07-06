import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../api/pegasus_api_client.dart';
import 'review_reflection_screen.dart';

// Providers for transcript screen
final transcriptDataProvider = StateProvider<Map<String, dynamic>?>((ref) => null);
final bothTranscriptsProvider = StateProvider<Map<String, String?>>((ref) => {});
final isLoadingProvider = StateProvider<bool>((ref) => true);
final selectedTagsProvider = StateProvider<List<String>>((ref) => []);  // Changed to List<String>
final availableTagsProvider = StateProvider<List<String>>((ref) => []);
final customTagControllerProvider = StateProvider<TextEditingController>((ref) => TextEditingController());

// New providers for editing
final isEditingProvider = StateProvider<bool>((ref) => false);
final editedTranscriptProvider = StateProvider<String?>((ref) => null);
final transcriptControllerProvider = StateProvider<TextEditingController>((ref) => TextEditingController());

class TranscriptScreen extends ConsumerStatefulWidget {
  final String audioId;
  
  const TranscriptScreen({Key? key, required this.audioId}) : super(key: key);

  @override
  ConsumerState<TranscriptScreen> createState() => _TranscriptScreenState();
}

class _TranscriptScreenState extends ConsumerState<TranscriptScreen> with TickerProviderStateMixin {
  final PegasusApiClient _apiClient = PegasusApiClient.defaultConfig();
  late TabController _tabController;
  
  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);  // Changed to 3 tabs
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _loadData();
    });
  }
  
  @override
  void dispose() {
    _tabController.dispose();
    ref.read(customTagControllerProvider).dispose();
    ref.read(transcriptControllerProvider).dispose();
    super.dispose();
  }
  
  Future<void> _loadData() async {
    ref.read(isLoadingProvider.notifier).state = true;
    
    try {
      // Load transcript data (improved version)
      final transcriptData = await _apiClient.getTranscript(widget.audioId);
      ref.read(transcriptDataProvider.notifier).state = transcriptData;
      
      // Load both transcripts if processing is complete
      if (transcriptData != null && transcriptData['status'] == 'completed') {
        final bothTranscripts = await _apiClient.getBothTranscripts(widget.audioId);
        ref.read(bothTranscriptsProvider.notifier).state = bothTranscripts;
      }
      
      // Load audio file details to get current tags
      final audioData = await _apiClient.getAudioFile(widget.audioId);
      if (audioData != null && audioData['tags'] != null) {
        ref.read(selectedTagsProvider.notifier).state = List<String>.from(audioData['tags'] as List);
      }
      
      // Initialize transcript editor if in PENDING_REVIEW status
      if (transcriptData != null && transcriptData['status'] == 'pending_review') {
        final improvedTranscript = transcriptData['transcript'] as String? ?? '';
        ref.read(editedTranscriptProvider.notifier).state = improvedTranscript;
        ref.read(transcriptControllerProvider.notifier).state.text = improvedTranscript;
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
    final selectedTags = ref.read(selectedTagsProvider);
    final customController = ref.read(customTagControllerProvider);
    
    List<String> tagsToSave = [];
    if (selectedTags.isNotEmpty) {
      tagsToSave = selectedTags;
    } else if (customController.text.isNotEmpty) {
      tagsToSave = [customController.text.trim()];
    }
    
    if (tagsToSave.isEmpty) {
      _showErrorSnackBar('Please select or enter a tag');
      return;
    }
    
    try {
      final success = await _apiClient.updateAudioTags(widget.audioId, tags: tagsToSave);
      if (success) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Tags "${tagsToSave.join(', ')}" saved successfully'),
            backgroundColor: Colors.green,
          ),
        );
        
        // Add to available tags if they're new
        final availableTags = ref.read(availableTagsProvider);
        final newTags = tagsToSave.where((tag) => !availableTags.contains(tag)).toList();
        if (newTags.isNotEmpty) {
          ref.read(availableTagsProvider.notifier).state = [...availableTags, ...newTags];
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

  void _navigateToReviewReflection() {
    final transcriptData = ref.read(transcriptDataProvider);
    final audioTitle = transcriptData?['file_name'] as String?;
    
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => ReviewReflectionScreen(
          audioId: widget.audioId,
          audioTitle: audioTitle,
        ),
      ),
    );
  }
  
  @override
  Widget build(BuildContext context) {
    final isLoading = ref.watch(isLoadingProvider);
    final transcriptData = ref.watch(transcriptDataProvider);
    final bothTranscripts = ref.watch(bothTranscriptsProvider);
    final selectedTags = ref.watch(selectedTagsProvider);
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
        actions: [
          IconButton(
            icon: const Icon(Icons.psychology),
            tooltip: 'Review & Reflection',
            onPressed: () => _navigateToReviewReflection(),
          ),
        ],
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
          _buildTranscriptTab(transcriptData, bothTranscripts),
          _buildTagsTab(selectedTags, availableTags, customController),
        ],
      ),
    );
  }
  
  Widget _buildTranscriptTab(Map<String, dynamic> transcriptData, Map<String, String?> bothTranscripts) {
    final status = transcriptData['status'] as String?;
    final improvedTranscript = transcriptData['transcript'] as String?;
    final originalTranscript = bothTranscripts['original'];
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
    
    if (improvedTranscript == null || improvedTranscript.isEmpty) {
      return const Center(
        child: Text('No transcript available'),
      );
    }
    
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // AI-Improved Transcript Section
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
            decoration: BoxDecoration(
              color: Colors.green.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: Colors.green, width: 1),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(Icons.auto_fix_high, size: 16, color: Colors.green),
                const SizedBox(width: 6),
                Text(
                  'AI-Improved Transcript',
                  style: TextStyle(
                    color: Colors.green,
                    fontWeight: FontWeight.w600,
                    fontSize: 12,
                  ),
                ),
              ],
            ),
          ),
          
          const SizedBox(height: 16),
          
          // Improved transcript text
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.green.withValues(alpha: 0.05),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: Colors.green.withValues(alpha: 0.3)),
            ),
            child: SelectableText(
              improvedTranscript,
              style: Theme.of(context).textTheme.bodyLarge?.copyWith(height: 1.6),
            ),
          ),
          
          const SizedBox(height: 16),
          
          // Action buttons row
          Row(
            children: [
              Expanded(
                child: ElevatedButton.icon(
                  onPressed: () => _copyToClipboard(improvedTranscript),
                  icon: const Icon(Icons.copy),
                  label: const Text('Copy'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.green,
                    foregroundColor: Colors.white,
                  ),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: ElevatedButton.icon(
                  onPressed: () => _navigateToReviewReflection(),
                  icon: const Icon(Icons.psychology),
                  label: const Text('Analyze'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Colors.purple,
                    foregroundColor: Colors.white,
                  ),
                ),
              ),
            ],
          ),
          
          // Original Transcript Section (if available)
          if (originalTranscript != null && originalTranscript.isNotEmpty) ...[
            const SizedBox(height: 32),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
              decoration: BoxDecoration(
                color: Colors.blue.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: Colors.blue, width: 1),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.mic, size: 16, color: Colors.blue),
                  const SizedBox(width: 6),
                  Text(
                    'Original Transcript',
                    style: TextStyle(
                      color: Colors.blue,
                      fontWeight: FontWeight.w600,
                      fontSize: 12,
                    ),
                  ),
                ],
              ),
            ),
            
            const SizedBox(height: 16),
            
            // Original transcript text
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.blue.withValues(alpha: 0.05),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: Colors.blue.withValues(alpha: 0.3)),
              ),
              child: SelectableText(
                originalTranscript,
                style: Theme.of(context).textTheme.bodyLarge?.copyWith(height: 1.6),
              ),
            ),
            
            const SizedBox(height: 16),
            
            // Copy original transcript button
            SizedBox(
              width: double.infinity,
              child: OutlinedButton.icon(
                onPressed: () => _copyToClipboard(originalTranscript),
                icon: const Icon(Icons.copy),
                label: const Text('Copy Original Transcript'),
                style: OutlinedButton.styleFrom(
                  foregroundColor: Colors.blue,
                  side: BorderSide(color: Colors.blue),
                ),
              ),
            ),
          ],
          
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
                  Text('AI Enhanced: Yes'),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }
  
  Widget _buildTagsTab(List<String> selectedTags, List<String> availableTags, TextEditingController customController) {
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
          
          // Current tags display
          if (selectedTags.isNotEmpty) ...[
            Text(
              'Current Tags:',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: selectedTags.map((tag) => Container(
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
                      tag,
                      style: const TextStyle(
                        color: Colors.green,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                ],
              ),
            )).toList(),
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
                final isSelected = selectedTags.contains(tag);
                return FilterChip(
                  label: Text(tag),
                  selected: isSelected,
                  onSelected: (selected) {
                    if (selected) {
                      ref.read(selectedTagsProvider.notifier).state = [tag];
                      customController.clear();
                    } else {
                      ref.read(selectedTagsProvider.notifier).state = [];
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
                ref.read(selectedTagsProvider.notifier).state = [];
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
                  ref.read(selectedTagsProvider.notifier).state = [tag];
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