/// Audio Player Widget for Voice Responses and Citations
/// 
/// This widget provides audio playback capabilities including:
/// - Audio response playback from TTS
/// - Source audio playback from citations
/// - Playback controls (play, pause, seek, speed)
/// - Waveform visualization
/// - Audio transcript synchronization

import 'package:flutter/material.dart';
import 'package:just_audio/just_audio.dart';
import 'dart:async';
import 'dart:ui';

enum AudioPlayerState {
  idle,
  loading,
  playing,
  paused,
  completed,
  error,
}

class AudioPlayerWidget extends StatefulWidget {
  final String? audioUrl;
  final String? audioData; // Base64 encoded audio data
  final String? transcript;
  final bool showTranscript;
  final bool showWaveform;
  final bool autoPlay;
  final VoidCallback? onPlayComplete;
  final Function(Duration)? onPositionChanged;

  const AudioPlayerWidget({
    super.key,
    this.audioUrl,
    this.audioData,
    this.transcript,
    this.showTranscript = true,
    this.showWaveform = false,
    this.autoPlay = false,
    this.onPlayComplete,
    this.onPositionChanged,
  });

  @override
  State<AudioPlayerWidget> createState() => _AudioPlayerWidgetState();
}

class _AudioPlayerWidgetState extends State<AudioPlayerWidget>
    with TickerProviderStateMixin {
  late AudioPlayer _audioPlayer;
  late AnimationController _waveAnimationController;
  late Animation<double> _waveAnimation;
  
  AudioPlayerState _playerState = AudioPlayerState.idle;
  Duration _duration = Duration.zero;
  Duration _position = Duration.zero;
  double _playbackSpeed = 1.0;
  bool _showTranscript = false;
  
  StreamSubscription<Duration?>? _durationSubscription;
  StreamSubscription<Duration>? _positionSubscription;
  StreamSubscription<PlayerState>? _playerStateSubscription;

  @override
  void initState() {
    super.initState();
    _initializePlayer();
    _initializeAnimations();
    _setupListeners();
    
    if (widget.autoPlay && _hasAudioSource()) {
      _loadAndPlay();
    }
  }

  void _initializePlayer() {
    _audioPlayer = AudioPlayer();
  }

  void _initializeAnimations() {
    _waveAnimationController = AnimationController(
      duration: const Duration(milliseconds: 1500),
      vsync: this,
    );
    _waveAnimation = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(parent: _waveAnimationController, curve: Curves.easeInOut),
    );
  }

  void _setupListeners() {
    _durationSubscription = _audioPlayer.durationStream.listen((duration) {
      setState(() => _duration = duration ?? Duration.zero);
    });

    _positionSubscription = _audioPlayer.positionStream.listen((position) {
      setState(() => _position = position);
      widget.onPositionChanged?.call(position);
    });

    _playerStateSubscription = _audioPlayer.playerStateStream.listen((state) {
      setState(() {
        _playerState = _mapPlayerState(state);
      });
      
      if (state.processingState == ProcessingState.completed) {
        _waveAnimationController.stop();
        widget.onPlayComplete?.call();
      }
    });
  }

  AudioPlayerState _mapPlayerState(PlayerState state) {
    if (state.processingState == ProcessingState.loading ||
        state.processingState == ProcessingState.buffering) {
      return AudioPlayerState.loading;
    } else if (state.processingState == ProcessingState.completed) {
      return AudioPlayerState.completed;
    } else if (state.playing) {
      return AudioPlayerState.playing;
    } else {
      return AudioPlayerState.paused;
    }
  }

  @override
  void dispose() {
    _audioPlayer.dispose();
    _waveAnimationController.dispose();
    _durationSubscription?.cancel();
    _positionSubscription?.cancel();
    _playerStateSubscription?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (!_hasAudioSource()) {
      return const SizedBox.shrink();
    }

    return Container(
      margin: const EdgeInsets.symmetric(vertical: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.grey.shade50,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.grey.shade200),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildPlayerControls(),
          if (widget.showWaveform) _buildWaveform(),
          if (widget.showTranscript && widget.transcript != null) _buildTranscript(),
        ],
      ),
    );
  }

  Widget _buildPlayerControls() {
    return Row(
      children: [
        _buildPlayButton(),
        const SizedBox(width: 12),
        Expanded(child: _buildProgressSlider()),
        const SizedBox(width: 12),
        _buildDurationText(),
        const SizedBox(width: 8),
        _buildSpeedButton(),
        if (widget.transcript != null) _buildTranscriptButton(),
      ],
    );
  }

  Widget _buildPlayButton() {
    IconData icon;
    VoidCallback? onPressed;
    
    switch (_playerState) {
      case AudioPlayerState.loading:
        return Container(
          width: 40,
          height: 40,
          padding: const EdgeInsets.all(8),
          child: const CircularProgressIndicator(strokeWidth: 2),
        );
      case AudioPlayerState.playing:
        icon = Icons.pause;
        onPressed = _pause;
        break;
      case AudioPlayerState.paused:
      case AudioPlayerState.completed:
      case AudioPlayerState.idle:
        icon = Icons.play_arrow;
        onPressed = _play;
        break;
      case AudioPlayerState.error:
        icon = Icons.error;
        onPressed = null;
        break;
    }

    return Container(
      width: 40,
      height: 40,
      decoration: BoxDecoration(
        color: Theme.of(context).primaryColor,
        borderRadius: BorderRadius.circular(20),
      ),
      child: IconButton(
        icon: Icon(icon, color: Colors.white),
        onPressed: onPressed,
        iconSize: 20,
      ),
    );
  }

  Widget _buildProgressSlider() {
    return SliderTheme(
      data: SliderTheme.of(context).copyWith(
        thumbShape: const RoundSliderThumbShape(enabledThumbRadius: 6),
        trackHeight: 3,
      ),
      child: Slider(
        value: _duration.inMilliseconds > 0
            ? _position.inMilliseconds / _duration.inMilliseconds
            : 0.0,
        onChanged: (value) {
          final position = Duration(
            milliseconds: (value * _duration.inMilliseconds).round(),
          );
          _audioPlayer.seek(position);
        },
        activeColor: Theme.of(context).primaryColor,
        inactiveColor: Colors.grey.shade300,
      ),
    );
  }

  Widget _buildDurationText() {
    return Text(
      '${_formatDuration(_position)} / ${_formatDuration(_duration)}',
      style: TextStyle(
        fontSize: 12,
        color: Colors.grey.shade600,
        fontFeatures: const [FontFeature.tabularFigures()],
      ),
    );
  }

  Widget _buildSpeedButton() {
    return PopupMenuButton<double>(
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
          color: Colors.grey.shade200,
          borderRadius: BorderRadius.circular(12),
        ),
        child: Text(
          '${_playbackSpeed}x',
          style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w500),
        ),
      ),
      itemBuilder: (context) => [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]
          .map((speed) => PopupMenuItem(
                value: speed,
                child: Text('${speed}x'),
              ))
          .toList(),
      onSelected: (speed) {
        setState(() => _playbackSpeed = speed);
        _audioPlayer.setSpeed(speed);
      },
    );
  }

  Widget _buildTranscriptButton() {
    return IconButton(
      icon: Icon(
        _showTranscript ? Icons.subtitles : Icons.subtitles_outlined,
        size: 20,
        color: _showTranscript ? Theme.of(context).primaryColor : Colors.grey.shade600,
      ),
      onPressed: () => setState(() => _showTranscript = !_showTranscript),
      tooltip: 'Toggle transcript',
    );
  }

  Widget _buildWaveform() {
    return Container(
      height: 60,
      margin: const EdgeInsets.symmetric(vertical: 8),
      child: AnimatedBuilder(
        animation: _waveAnimation,
        builder: (context, child) {
          return CustomPaint(
            painter: WaveformPainter(
              progress: _duration.inMilliseconds > 0
                  ? _position.inMilliseconds / _duration.inMilliseconds
                  : 0.0,
              animationValue: _waveAnimation.value,
              isPlaying: _playerState == AudioPlayerState.playing,
            ),
            size: Size.infinite,
          );
        },
      ),
    );
  }

  Widget _buildTranscript() {
    if (!_showTranscript || widget.transcript == null) {
      return const SizedBox.shrink();
    }

    return Container(
      margin: const EdgeInsets.only(top: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.grey.shade200),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                Icons.subtitles,
                size: 16,
                color: Colors.grey.shade600,
              ),
              const SizedBox(width: 4),
              Text(
                'Transcript',
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w500,
                  color: Colors.grey.shade700,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            widget.transcript!,
            style: const TextStyle(
              fontSize: 14,
              height: 1.4,
            ),
          ),
        ],
      ),
    );
  }

  bool _hasAudioSource() {
    return widget.audioUrl != null || widget.audioData != null;
  }

  Future<void> _loadAndPlay() async {
    if (!_hasAudioSource()) return;

    setState(() => _playerState = AudioPlayerState.loading);

    try {
      if (widget.audioUrl != null) {
        await _audioPlayer.setUrl(widget.audioUrl!);
      } else if (widget.audioData != null) {
        // Handle base64 encoded audio data
        // This would require converting base64 to a temporary file or streaming
        throw UnimplementedError('Base64 audio data not yet implemented');
      }
      
      await _play();
    } catch (e) {
      setState(() => _playerState = AudioPlayerState.error);
      debugPrint('Audio loading error: $e');
    }
  }

  Future<void> _play() async {
    try {
      if (_playerState == AudioPlayerState.completed) {
        await _audioPlayer.seek(Duration.zero);
      }
      
      await _audioPlayer.play();
      
      if (widget.showWaveform) {
        _waveAnimationController.repeat();
      }
    } catch (e) {
      setState(() => _playerState = AudioPlayerState.error);
      debugPrint('Play error: $e');
    }
  }

  Future<void> _pause() async {
    try {
      await _audioPlayer.pause();
      _waveAnimationController.stop();
    } catch (e) {
      debugPrint('Pause error: $e');
    }
  }

  String _formatDuration(Duration duration) {
    String twoDigits(int n) => n.toString().padLeft(2, '0');
    final hours = duration.inHours;
    final minutes = duration.inMinutes.remainder(60);
    final seconds = duration.inSeconds.remainder(60);

    if (hours > 0) {
      return '$hours:${twoDigits(minutes)}:${twoDigits(seconds)}';
    } else {
      return '${twoDigits(minutes)}:${twoDigits(seconds)}';
    }
  }
}

/// Waveform painter for audio visualization
class WaveformPainter extends CustomPainter {
  final double progress;
  final double animationValue;
  final bool isPlaying;

  WaveformPainter({
    required this.progress,
    required this.animationValue,
    required this.isPlaying,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..strokeWidth = 2
      ..strokeCap = StrokeCap.round;

    final progressPaint = Paint()
      ..strokeWidth = 2
      ..strokeCap = StrokeCap.round
      ..color = Colors.blue;

    final inactivePaint = Paint()
      ..strokeWidth = 2
      ..strokeCap = StrokeCap.round
      ..color = Colors.grey.shade300;

    // Draw waveform bars
    const barCount = 50;
    final barWidth = size.width / barCount;
    final progressX = size.width * progress;

    for (int i = 0; i < barCount; i++) {
      final x = i * barWidth + barWidth / 2;
      
      // Generate pseudo-random heights for waveform
      final heightFactor = _generateWaveHeight(i, animationValue);
      final barHeight = size.height * heightFactor;
      
      final startY = (size.height - barHeight) / 2;
      final endY = startY + barHeight;

      // Use progress paint for played portion, inactive for rest
      final currentPaint = x <= progressX ? progressPaint : inactivePaint;
      
      canvas.drawLine(
        Offset(x, startY),
        Offset(x, endY),
        currentPaint,
      );
    }
  }

  double _generateWaveHeight(int index, double animationValue) {
    // Create a pseudo-random waveform pattern
    final baseHeight = 0.3 + 0.4 * ((index * 0.1) % 1.0);
    final animatedHeight = isPlaying 
        ? baseHeight + 0.3 * (animationValue * (1 + index % 3))
        : baseHeight;
    
    return animatedHeight.clamp(0.1, 1.0);
  }

  @override
  bool shouldRepaint(WaveformPainter oldDelegate) {
    return progress != oldDelegate.progress ||
           animationValue != oldDelegate.animationValue ||
           isPlaying != oldDelegate.isPlaying;
  }
}

/// Compact audio player for inline use
class CompactAudioPlayer extends StatelessWidget {
  final String? audioUrl;
  final String? transcript;
  final VoidCallback? onTap;

  const CompactAudioPlayer({
    super.key,
    this.audioUrl,
    this.transcript,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(20),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        decoration: BoxDecoration(
          color: Colors.blue.shade50,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: Colors.blue.shade200),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.play_circle_outline,
              size: 16,
              color: Colors.blue.shade700,
            ),
            const SizedBox(width: 6),
            Text(
              'Play Audio',
              style: TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w500,
                color: Colors.blue.shade700,
              ),
            ),
            if (transcript != null) ...[ 
              const SizedBox(width: 6),
              Icon(
                Icons.subtitles,
                size: 14,
                color: Colors.blue.shade600,
              ),
            ],
          ],
        ),
      ),
    );
  }
}