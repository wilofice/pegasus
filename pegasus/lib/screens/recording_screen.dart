import 'dart:async';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:path_provider/path_provider.dart';
import 'package:flutter_sound/flutter_sound.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:just_audio/just_audio.dart';
import '../services/prefs_service.dart';
import '../api/pegasus_api_client.dart';

// Providers for recording state
final isRecordingProvider = StateProvider<bool>((ref) => false);
final recordingTimeProvider = StateProvider<int>((ref) => 0);
final recordingFileProvider = StateProvider<String?>((ref) => null);
final maxRecordingTimeProvider = StateProvider<int>((ref) => 60);
final isPlayingProvider = StateProvider<bool>((ref) => false);
final isUploadingProvider = StateProvider<bool>((ref) => false);
final uploadedAudioIdProvider = StateProvider<String?>((ref) => null);
final audioProcessingStatusProvider = StateProvider<String?>((ref) => null);
final recordingLanguageProvider = StateProvider<String>((ref) => 'en');

class RecordingScreen extends ConsumerStatefulWidget {
  const RecordingScreen({Key? key}) : super(key: key);

  @override
  ConsumerState<RecordingScreen> createState() => _RecordingScreenState();
}

class _RecordingScreenState extends ConsumerState<RecordingScreen> {
  FlutterSoundRecorder? _recorder;
  final AudioPlayer _audioPlayer = AudioPlayer();
  final PrefsService _prefsService = PrefsService();
  final PegasusApiClient _apiClient = PegasusApiClient.defaultConfig();
  
  Timer? _recordingTimer;
  Timer? _statusCheckTimer;
  
  @override
  void initState() {
    super.initState();
    _initRecorder();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _loadPreferences();
    });
  }
  
  @override
  void dispose() {
    _recordingTimer?.cancel();
    _statusCheckTimer?.cancel();
    _recorder?.closeRecorder();
    _audioPlayer.dispose();
    super.dispose();
  }
  
  Future<void> _initRecorder() async {
    _recorder = FlutterSoundRecorder();
    await _recorder!.openRecorder();
  }
  
  Future<void> _loadPreferences() async {
    final maxTime = await _prefsService.getMaxRecordingSec();
    ref.read(maxRecordingTimeProvider.notifier).state = maxTime;
    
    // Load saved language preference
    final language = await _prefsService.getRecordingLanguage();
    ref.read(recordingLanguageProvider.notifier).state = language;
  }
  
  Future<String> _buildFilePath() async {
    final dir = await getApplicationDocumentsDirectory();
    final timestamp = DateTime.now().millisecondsSinceEpoch;
    return '${dir.path}/recording_$timestamp.m4a';
  }
  
  Future<void> _startRecording() async {
    try {
      // Check permissions
      final permission = await Permission.microphone.request();
      if (permission == PermissionStatus.granted) {
        final filePath = await _buildFilePath();
        final quality = await _prefsService.getAudioQuality();
        final config = _prefsService.getRecordingConfig(quality);
        
        await _recorder!.startRecorder(
          toFile: filePath,
          codec: Codec.aacMP4,
          bitRate: config['bitRate'],
          sampleRate: config['samplingRate'],
        );
        
        ref.read(isRecordingProvider.notifier).state = true;
        ref.read(recordingTimeProvider.notifier).state = 0;
        ref.read(recordingFileProvider.notifier).state = filePath;
        
        _startTimer();
        
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Recording started'),
              backgroundColor: Colors.green,
              duration: Duration(seconds: 2),
            ),
          );
        }
      } else {
        _showPermissionDeniedDialog();
      }
    } catch (e) {
      _showErrorSnackBar('Failed to start recording: $e');
    }
  }
  
  Future<void> _stopRecording() async {
    try {
      _recordingTimer?.cancel();
      await _recorder!.stopRecorder();
      
      ref.read(isRecordingProvider.notifier).state = false;
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Recording saved (${ref.read(recordingTimeProvider)}s)'),
            backgroundColor: Colors.blue,
            action: SnackBarAction(
              label: 'PLAY',
              onPressed: _playRecording,
            ),
          ),
        );
      }
      
      // Auto-upload if enabled
      final autoUpload = await _prefsService.getAutoUploadAudio();
      if (autoUpload) {
        _uploadRecording();
      }
    } catch (e) {
      _showErrorSnackBar('Failed to stop recording: $e');
    }
  }
  
  void _startTimer() {
    final maxTime = ref.read(maxRecordingTimeProvider);
    _recordingTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
      final currentTime = ref.read(recordingTimeProvider) + 1;
      ref.read(recordingTimeProvider.notifier).state = currentTime;
      
      if (currentTime >= maxTime) {
        _stopRecording();
      }
    });
  }
  
  Future<void> _playRecording() async {
    final filePath = ref.read(recordingFileProvider);
    if (filePath == null || !File(filePath).existsSync()) {
      _showErrorSnackBar('No recording found');
      return;
    }
    
    try {
      if (ref.read(isPlayingProvider)) {
        await _audioPlayer.stop();
        ref.read(isPlayingProvider.notifier).state = false;
      } else {
        await _audioPlayer.setFilePath(filePath);
        ref.read(isPlayingProvider.notifier).state = true;
        
        await _audioPlayer.play();
        
        // Listen for completion
        _audioPlayer.playerStateStream.listen((state) {
          if (state.processingState == ProcessingState.completed) {
            ref.read(isPlayingProvider.notifier).state = false;
          }
        });
      }
    } catch (e) {
      ref.read(isPlayingProvider.notifier).state = false;
      _showErrorSnackBar('Failed to play recording: $e');
    }
  }
  
  Future<void> _uploadRecording() async {
    final filePath = ref.read(recordingFileProvider);
    if (filePath == null || !File(filePath).existsSync()) {
      _showErrorSnackBar('No recording to upload');
      return;
    }
    
    ref.read(isUploadingProvider.notifier).state = true;
    
    try {
      // Get the selected language
      final language = ref.read(recordingLanguageProvider);
      
      // Upload to Pegasus backend with language
      final result = await _apiClient.uploadAudioFile(
        File(filePath),
        language: language,
      );
      
      // Store the audio file ID
      final audioId = result['id'] as String?;
      if (audioId != null) {
        ref.read(uploadedAudioIdProvider.notifier).state = audioId;
        ref.read(audioProcessingStatusProvider.notifier).state = result['processing_status'] as String?;
        
        // Start checking status if still processing
        final status = result['processing_status'] as String?;
        if (status != null && !['completed', 'failed'].contains(status)) {
          _startStatusChecking(audioId);
        }
      }
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Recording uploaded successfully'),
            backgroundColor: Colors.green,
          ),
        );
      }
    } catch (e) {
      _showErrorSnackBar('Upload failed: $e');
    } finally {
      ref.read(isUploadingProvider.notifier).state = false;
    }
  }
  
  void _startStatusChecking(String audioId) {
    _statusCheckTimer?.cancel();
    _statusCheckTimer = Timer.periodic(const Duration(seconds: 5), (timer) async {
      try {
        final audioData = await _apiClient.getAudioFile(audioId);
        if (audioData != null) {
          final status = audioData['processing_status'] as String?;
          ref.read(audioProcessingStatusProvider.notifier).state = status;
          
          // Stop checking if processing is complete
          if (status != null && ['completed', 'failed'].contains(status)) {
            timer.cancel();
          }
        }
      } catch (e) {
        // Continue checking on error
      }
    });
  }
  
  void _viewTranscript() {
    final audioId = ref.read(uploadedAudioIdProvider);
    if (audioId != null) {
      Navigator.pushNamed(
        context, 
        '/transcript',
        arguments: {'audioId': audioId},
      );
    }
  }
  
  Future<void> _deleteRecording() async {
    final filePath = ref.read(recordingFileProvider);
    if (filePath != null && File(filePath).existsSync()) {
      try {
        await File(filePath).delete();
        ref.read(recordingFileProvider.notifier).state = null;
        ref.read(recordingTimeProvider.notifier).state = 0;
        
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Recording deleted')),
          );
        }
      } catch (e) {
        _showErrorSnackBar('Failed to delete recording: $e');
      }
    }
  }
  
  void _showPermissionDeniedDialog() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Permission Required'),
        content: const Text(
          'Microphone permission is required to record audio. Please enable it in your device settings.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('OK'),
          ),
        ],
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
  
  String _formatTime(int seconds) {
    final minutes = seconds ~/ 60;
    final remainingSeconds = seconds % 60;
    return '${minutes.toString().padLeft(2, '0')}:${remainingSeconds.toString().padLeft(2, '0')}';
  }
  
  Widget _buildProcessingStatusWidget(String? status) {
    if (status == null) return const SizedBox.shrink();
    
    Color statusColor;
    IconData statusIcon;
    String statusText;
    bool showProgress = false;
    
    switch (status.toLowerCase()) {
      case 'uploaded':
        statusColor = Colors.blue;
        statusIcon = Icons.upload_file;
        statusText = 'Uploaded';
        break;
      case 'transcribing':
        statusColor = Colors.orange;
        statusIcon = Icons.mic;
        statusText = 'Transcribing...';
        showProgress = true;
        break;
      case 'improving':
        statusColor = Colors.purple;
        statusIcon = Icons.auto_fix_high;
        statusText = 'Improving with AI...';
        showProgress = true;
        break;
      case 'completed':
        statusColor = Colors.green;
        statusIcon = Icons.check_circle;
        statusText = 'Processing Complete';
        break;
      case 'failed':
        statusColor = Colors.red;
        statusIcon = Icons.error;
        statusText = 'Processing Failed';
        break;
      default:
        statusColor = Colors.grey;
        statusIcon = Icons.help;
        statusText = 'Unknown Status';
    }
    
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      decoration: BoxDecoration(
        color: statusColor.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: statusColor, width: 1),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (showProgress)
            SizedBox(
              width: 16,
              height: 16,
              child: CircularProgressIndicator(
                strokeWidth: 2,
                color: statusColor,
              ),
            )
          else
            Icon(statusIcon, color: statusColor, size: 16),
          const SizedBox(width: 8),
          Text(
            statusText,
            style: TextStyle(
              color: statusColor,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
  
  @override
  Widget build(BuildContext context) {
    final isRecording = ref.watch(isRecordingProvider);
    final recordingTime = ref.watch(recordingTimeProvider);
    final maxTime = ref.watch(maxRecordingTimeProvider);
    final hasRecording = ref.watch(recordingFileProvider) != null;
    final isPlaying = ref.watch(isPlayingProvider);
    final isUploading = ref.watch(isUploadingProvider);
    final uploadedAudioId = ref.watch(uploadedAudioIdProvider);
    final processingStatus = ref.watch(audioProcessingStatusProvider);
    
    return Scaffold(
      appBar: AppBar(
        title: const Text('Audio Recorder'),
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
        actions: [
          IconButton(
            icon: const Icon(Icons.settings),
            onPressed: () => _showSettingsDialog(),
          ),
        ],
      ),
      body: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            // Timer display
            Container(
              padding: const EdgeInsets.all(32),
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: isRecording 
                    ? Colors.red.withValues(alpha: 0.1)
                    : Theme.of(context).colorScheme.surfaceContainerHighest.withValues(alpha: 0.3),
                border: Border.all(
                  color: isRecording ? Colors.red : Theme.of(context).colorScheme.outline,
                  width: 2,
                ),
              ),
              child: Column(
                children: [
                  Text(
                    _formatTime(recordingTime),
                    style: Theme.of(context).textTheme.headlineLarge?.copyWith(
                      fontWeight: FontWeight.bold,
                      color: isRecording ? Colors.red : null,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Max: ${_formatTime(maxTime)}',
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                ],
              ),
            ),
            
            const SizedBox(height: 48),
            
            // Status text
            Text(
              isRecording 
                  ? 'Recording in progress...'
                  : hasRecording 
                      ? 'Recording completed'
                      : 'Ready to record',
              style: Theme.of(context).textTheme.titleMedium,
              textAlign: TextAlign.center,
            ),
            
            // Processing status indicator
            if (uploadedAudioId != null) ...[
              const SizedBox(height: 16),
              _buildProcessingStatusWidget(processingStatus),
            ],
            
            const SizedBox(height: 32),
            
            // Main record button
            SizedBox(
              width: 120,
              height: 120,
              child: ElevatedButton(
                onPressed: isRecording ? _stopRecording : _startRecording,
                style: ElevatedButton.styleFrom(
                  shape: const CircleBorder(),
                  backgroundColor: isRecording ? Colors.red : Colors.green,
                  foregroundColor: Colors.white,
                  elevation: 8,
                ),
                child: Icon(
                  isRecording ? Icons.stop : Icons.mic,
                  size: 48,
                ),
              ),
            ),
            
            const SizedBox(height: 32),
            
            // Action buttons
            if (hasRecording) ...[
              Wrap(
                alignment: WrapAlignment.center,
                spacing: 8,
                runSpacing: 8,
                children: [
                  // Play button
                  ElevatedButton.icon(
                    onPressed: isRecording ? null : _playRecording,
                    icon: Icon(isPlaying ? Icons.stop : Icons.play_arrow),
                    label: Text(isPlaying ? 'Stop' : 'Play'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.blue,
                      foregroundColor: Colors.white,
                    ),
                  ),
                  
                  // Upload button
                  ElevatedButton.icon(
                    onPressed: (isRecording || isUploading) ? null : _uploadRecording,
                    icon: isUploading 
                        ? const SizedBox(
                            width: 16,
                            height: 16,
                            child: CircularProgressIndicator(
                              strokeWidth: 2,
                              color: Colors.white,
                            ),
                          )
                        : const Icon(Icons.upload),
                    label: Text(isUploading ? 'Uploading...' : 'Upload'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.orange,
                      foregroundColor: Colors.white,
                    ),
                  ),
                  
                  // Transcript button (only show when processing is complete)
                  if (uploadedAudioId != null && processingStatus == 'completed')
                    ElevatedButton.icon(
                      onPressed: _viewTranscript,
                      icon: const Icon(Icons.text_snippet),
                      label: const Text('View Transcript'),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.green,
                        foregroundColor: Colors.white,
                      ),
                    ),
                  
                  // Delete button
                  ElevatedButton.icon(
                    onPressed: isRecording ? null : _deleteRecording,
                    icon: const Icon(Icons.delete),
                    label: const Text('Delete'),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.red,
                      foregroundColor: Colors.white,
                    ),
                  ),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }
  
  void _showSettingsDialog() {
    showDialog(
      context: context,
      builder: (context) => _SettingsDialog(prefsService: _prefsService),
    );
  }
}

class _SettingsDialog extends StatefulWidget {
  final PrefsService prefsService;
  
  const _SettingsDialog({required this.prefsService});
  
  @override
  State<_SettingsDialog> createState() => _SettingsDialogState();
}

class _SettingsDialogState extends State<_SettingsDialog> {
  late int _maxDuration;
  late bool _autoUpload;
  late String _audioQuality;
  late String _recordingLanguage;
  
  @override
  void initState() {
    super.initState();
    _loadSettings();
  }
  
  Future<void> _loadSettings() async {
    _maxDuration = await widget.prefsService.getMaxRecordingSec();
    _autoUpload = await widget.prefsService.getAutoUploadAudio();
    _audioQuality = await widget.prefsService.getAudioQuality();
    _recordingLanguage = await widget.prefsService.getRecordingLanguage();
    setState(() {});
  }
  
  Future<void> _saveSettings() async {
    await widget.prefsService.setMaxRecordingSec(_maxDuration);
    await widget.prefsService.setAutoUploadAudio(_autoUpload);
    await widget.prefsService.setAudioQuality(_audioQuality);
    await widget.prefsService.setRecordingLanguage(_recordingLanguage);
  }
  
  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Recording Settings'),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Max duration
          ListTile(
            title: const Text('Max Duration'),
            subtitle: Slider(
              value: _maxDuration.toDouble(),
              min: 10,
              max: 300,
              divisions: 29,
              label: '${_maxDuration}s',
              onChanged: (value) {
                setState(() {
                  _maxDuration = value.round();
                });
              },
            ),
            trailing: Text('${_maxDuration}s'),
          ),
          
          // Auto upload
          SwitchListTile(
            title: const Text('Auto Upload'),
            subtitle: const Text('Upload recordings automatically'),
            value: _autoUpload,
            onChanged: (value) {
              setState(() {
                _autoUpload = value;
              });
            },
          ),
          
          // Audio quality
          ListTile(
            title: const Text('Audio Quality'),
            subtitle: DropdownButton<String>(
              value: _audioQuality,
              items: const [
                DropdownMenuItem(value: 'low', child: Text('Low (64 kbps)')),
                DropdownMenuItem(value: 'medium', child: Text('Medium (128 kbps)')),
                DropdownMenuItem(value: 'high', child: Text('High (256 kbps)')),
              ],
              onChanged: (value) {
                if (value != null) {
                  setState(() {
                    _audioQuality = value;
                  });
                }
              },
            ),
          ),
          
          // Recording language
          ListTile(
            title: const Text('Recording Language'),
            subtitle: DropdownButton<String>(
              value: _recordingLanguage,
              items: const [
                DropdownMenuItem(value: 'en', child: Text('English')),
                DropdownMenuItem(value: 'fr', child: Text('French')),
              ],
              onChanged: (value) {
                if (value != null) {
                  setState(() {
                    _recordingLanguage = value;
                  });
                }
              },
            ),
          ),
        ],
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Cancel'),
        ),
        TextButton(
          onPressed: () async {
            await _saveSettings();
            if (mounted) {
              Navigator.of(context).pop();
            }
          },
          child: const Text('Save'),
        ),
      ],
    );
  }
}