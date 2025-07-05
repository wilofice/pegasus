/// Enhanced Audio API models for comprehensive audio processing
/// 
/// These models support the enhanced audio API with advanced processing,
/// metadata management, and real-time status tracking.

import 'api_enums.dart';

/// Audio file response model
class AudioFileResponse {
  final String id;
  final String filename;
  final String? originalFilename;
  final int? fileSizeBytes;
  final double? durationSeconds;
  final String? mimeType;
  final String? originalTranscript;
  final String? improvedTranscript;
  final String? transcriptionEngine;
  final DateTime? transcriptionStartedAt;
  final DateTime? transcriptionCompletedAt;
  final DateTime? improvementCompletedAt;
  final String? userId;
  final DateTime? uploadTimestamp;
  final ProcessingStatus processingStatus;
  final String? errorMessage;
  final String? tag;
  final String? category;
  final DateTime? createdAt;
  final DateTime? updatedAt;

  const AudioFileResponse({
    required this.id,
    required this.filename,
    this.originalFilename,
    this.fileSizeBytes,
    this.durationSeconds,
    this.mimeType,
    this.originalTranscript,
    this.improvedTranscript,
    this.transcriptionEngine,
    this.transcriptionStartedAt,
    this.transcriptionCompletedAt,
    this.improvementCompletedAt,
    this.userId,
    this.uploadTimestamp,
    required this.processingStatus,
    this.errorMessage,
    this.tag,
    this.category,
    this.createdAt,
    this.updatedAt,
  });

  /// Create from JSON
  factory AudioFileResponse.fromJson(Map<String, dynamic> json) {
    return AudioFileResponse(
      id: json['id'] as String,
      filename: json['filename'] as String,
      originalFilename: json['original_filename'] as String?,
      fileSizeBytes: json['file_size_bytes'] as int?,
      durationSeconds: json['duration_seconds'] != null
          ? (json['duration_seconds'] as num).toDouble()
          : null,
      mimeType: json['mime_type'] as String?,
      originalTranscript: json['original_transcript'] as String?,
      improvedTranscript: json['improved_transcript'] as String?,
      transcriptionEngine: json['transcription_engine'] as String?,
      transcriptionStartedAt: json['transcription_started_at'] != null
          ? DateTime.parse(json['transcription_started_at'] as String)
          : null,
      transcriptionCompletedAt: json['transcription_completed_at'] != null
          ? DateTime.parse(json['transcription_completed_at'] as String)
          : null,
      improvementCompletedAt: json['improvement_completed_at'] != null
          ? DateTime.parse(json['improvement_completed_at'] as String)
          : null,
      userId: json['user_id'] as String?,
      uploadTimestamp: json['upload_timestamp'] != null
          ? DateTime.parse(json['upload_timestamp'] as String)
          : null,
      processingStatus: ProcessingStatus.fromString(json['processing_status'] as String),
      errorMessage: json['error_message'] as String?,
      tag: json['tag'] as String?,
      category: json['category'] as String?,
      createdAt: json['created_at'] != null
          ? DateTime.parse(json['created_at'] as String)
          : null,
      updatedAt: json['updated_at'] != null
          ? DateTime.parse(json['updated_at'] as String)
          : null,
    );
  }

  /// Get display filename
  String get displayFilename => originalFilename ?? filename;

  /// Get file size in human-readable format
  String get formattedFileSize {
    if (fileSizeBytes == null) return 'Unknown size';
    
    final bytes = fileSizeBytes!;
    if (bytes < 1024) return '$bytes B';
    if (bytes < 1024 * 1024) return '${(bytes / 1024).toStringAsFixed(1)} KB';
    if (bytes < 1024 * 1024 * 1024) return '${(bytes / (1024 * 1024)).toStringAsFixed(1)} MB';
    return '${(bytes / (1024 * 1024 * 1024)).toStringAsFixed(1)} GB';
  }

  /// Get formatted duration
  String get formattedDuration {
    if (durationSeconds == null) return 'Unknown duration';
    
    final duration = Duration(seconds: durationSeconds!.round());
    final hours = duration.inHours;
    final minutes = duration.inMinutes.remainder(60);
    final seconds = duration.inSeconds.remainder(60);
    
    if (hours > 0) {
      return '${hours}:${minutes.toString().padLeft(2, '0')}:${seconds.toString().padLeft(2, '0')}';
    } else {
      return '${minutes}:${seconds.toString().padLeft(2, '0')}';
    }
  }

  /// Get formatted upload timestamp
  String? get formattedUploadTime {
    if (uploadTimestamp == null) return null;
    final now = DateTime.now();
    final difference = now.difference(uploadTimestamp!);
    
    if (difference.inDays > 0) {
      return '${difference.inDays} day${difference.inDays == 1 ? '' : 's'} ago';
    } else if (difference.inHours > 0) {
      return '${difference.inHours} hour${difference.inHours == 1 ? '' : 's'} ago';
    } else if (difference.inMinutes > 0) {
      return '${difference.inMinutes} minute${difference.inMinutes == 1 ? '' : 's'} ago';
    } else {
      return 'Just now';
    }
  }

  /// Get transcription duration if available
  Duration? get transcriptionDuration {
    if (transcriptionStartedAt == null || transcriptionCompletedAt == null) return null;
    return transcriptionCompletedAt!.difference(transcriptionStartedAt!);
  }

  /// Get improvement duration if available
  Duration? get improvementDuration {
    if (transcriptionCompletedAt == null || improvementCompletedAt == null) return null;
    return improvementCompletedAt!.difference(transcriptionCompletedAt!);
  }

  /// Check if transcript is available
  bool get hasTranscript => 
      originalTranscript != null && originalTranscript!.isNotEmpty;

  /// Check if improved transcript is available
  bool get hasImprovedTranscript => 
      improvedTranscript != null && improvedTranscript!.isNotEmpty;

  /// Get best available transcript
  String? get bestTranscript => improvedTranscript ?? originalTranscript;

  /// Check if processing is complete
  bool get isProcessingComplete => processingStatus.isCompleted;

  /// Check if processing failed
  bool get isProcessingFailed => processingStatus.isFailed;

  /// Check if currently processing
  bool get isProcessing => processingStatus.isInProgress;

  /// Get file extension
  String? get fileExtension {
    final parts = filename.split('.');
    return parts.length > 1 ? parts.last.toLowerCase() : null;
  }

  /// Check if file is audio format
  bool get isAudioFile {
    final ext = fileExtension;
    return ext != null && ['mp3', 'wav', 'm4a', 'ogg', 'flac', 'aac'].contains(ext);
  }
}

/// Audio upload response model
class AudioUploadResponse {
  final String id;
  final String filename;
  final String? originalFilename;
  final int? fileSizeBytes;
  final DateTime? uploadTimestamp;
  final ProcessingStatus processingStatus;
  final String message;

  const AudioUploadResponse({
    required this.id,
    required this.filename,
    this.originalFilename,
    this.fileSizeBytes,
    this.uploadTimestamp,
    required this.processingStatus,
    this.message = 'File uploaded successfully',
  });

  /// Create from JSON
  factory AudioUploadResponse.fromJson(Map<String, dynamic> json) {
    return AudioUploadResponse(
      id: json['id'] as String,
      filename: json['filename'] as String,
      originalFilename: json['original_filename'] as String?,
      fileSizeBytes: json['file_size_bytes'] as int?,
      uploadTimestamp: json['upload_timestamp'] != null
          ? DateTime.parse(json['upload_timestamp'] as String)
          : null,
      processingStatus: ProcessingStatus.fromString(json['processing_status'] as String),
      message: json['message'] as String? ?? 'File uploaded successfully',
    );
  }

  /// Check if upload was successful
  bool get isSuccessful => processingStatus != ProcessingStatus.failed;
}

/// Audio file list response model
class AudioFileListResponse {
  final List<AudioFileResponse> items;
  final int total;
  final int limit;
  final int offset;

  const AudioFileListResponse({
    required this.items,
    required this.total,
    required this.limit,
    required this.offset,
  });

  /// Create from JSON
  factory AudioFileListResponse.fromJson(Map<String, dynamic> json) {
    return AudioFileListResponse(
      items: (json['items'] as List<dynamic>)
          .map((item) => AudioFileResponse.fromJson(item as Map<String, dynamic>))
          .toList(),
      total: json['total'] as int,
      limit: json['limit'] as int,
      offset: json['offset'] as int,
    );
  }

  /// Check if there are more items available
  bool get hasMore => offset + limit < total;

  /// Get current page number (1-based)
  int get currentPage => (offset ~/ limit) + 1;

  /// Get total number of pages
  int get totalPages => (total / limit).ceil();

  /// Check if this is the first page
  bool get isFirstPage => offset == 0;

  /// Check if this is the last page
  bool get isLastPage => !hasMore;
}

/// Audio tags response model
class AudioTagsResponse {
  final List<String> tags;
  final List<String> categories;

  const AudioTagsResponse({
    required this.tags,
    required this.categories,
  });

  /// Create from JSON
  factory AudioTagsResponse.fromJson(Map<String, dynamic> json) {
    return AudioTagsResponse(
      tags: List<String>.from(json['tags'] as List<dynamic>),
      categories: List<String>.from(json['categories'] as List<dynamic>),
    );
  }

  /// Get all available options (tags + categories)
  List<String> get allOptions => [...tags, ...categories];

  /// Check if has tags
  bool get hasTags => tags.isNotEmpty;

  /// Check if has categories
  bool get hasCategories => categories.isNotEmpty;
}

/// Audio tag update request model
class AudioTagUpdateRequest {
  final String? tag;
  final String? category;

  const AudioTagUpdateRequest({
    this.tag,
    this.category,
  });

  /// Convert to JSON for API request
  Map<String, dynamic> toJson() {
    final json = <String, dynamic>{};
    if (tag != null) json['tag'] = tag;
    if (category != null) json['category'] = category;
    return json;
  }
}

/// Audio list request model for filtering
class AudioListRequest {
  final String? userId;
  final ProcessingStatus? status;
  final String? tag;
  final String? category;
  final int limit;
  final int offset;

  const AudioListRequest({
    this.userId,
    this.status,
    this.tag,
    this.category,
    this.limit = 20,
    this.offset = 0,
  });

  /// Convert to query parameters
  Map<String, String> toQueryParams() {
    final params = <String, String>{
      'limit': limit.toString(),
      'offset': offset.toString(),
    };

    if (userId != null) params['user_id'] = userId!;
    if (status != null) params['status'] = status!.value;
    if (tag != null) params['tag'] = tag!;
    if (category != null) params['category'] = category!;

    return params;
  }

  /// Create a copy with updated fields
  AudioListRequest copyWith({
    String? userId,
    ProcessingStatus? status,
    String? tag,
    String? category,
    int? limit,
    int? offset,
  }) {
    return AudioListRequest(
      userId: userId ?? this.userId,
      status: status ?? this.status,
      tag: tag ?? this.tag,
      category: category ?? this.category,
      limit: limit ?? this.limit,
      offset: offset ?? this.offset,
    );
  }

  /// Create request for next page
  AudioListRequest nextPage() {
    return copyWith(offset: offset + limit);
  }

  /// Create request for previous page
  AudioListRequest previousPage() {
    return copyWith(offset: (offset - limit).clamp(0, double.infinity).toInt());
  }

  /// Create request for specific page (1-based)
  AudioListRequest page(int pageNumber) {
    return copyWith(offset: (pageNumber - 1) * limit);
  }
}

/// Audio processing update model (for real-time updates)
class AudioProcessingUpdate {
  final String audioId;
  final ProcessingStatus status;
  final int? progress;
  final String? message;
  final String? currentStage;
  final Map<String, dynamic>? metadata;
  final DateTime timestamp;

  const AudioProcessingUpdate({
    required this.audioId,
    required this.status,
    this.progress,
    this.message,
    this.currentStage,
    this.metadata,
    required this.timestamp,
  });

  /// Create from JSON
  factory AudioProcessingUpdate.fromJson(Map<String, dynamic> json) {
    return AudioProcessingUpdate(
      audioId: json['audio_id'] as String,
      status: ProcessingStatus.fromString(json['status'] as String),
      progress: json['progress'] as int?,
      message: json['message'] as String?,
      currentStage: json['current_stage'] as String?,
      metadata: json['metadata'] as Map<String, dynamic>?,
      timestamp: DateTime.parse(json['timestamp'] as String),
    );
  }

  /// Get progress percentage (0-100)
  int get progressPercentage => progress ?? 0;

  /// Get current stage display name
  String get stageDisplayName {
    switch (currentStage?.toLowerCase()) {
      case 'upload':
        return 'Uploading';
      case 'transcription':
        return 'Transcribing';
      case 'improvement':
        return 'Improving';
      case 'processing':
        return 'Processing';
      default:
        return currentStage ?? 'Processing';
    }
  }

  /// Check if processing is in progress
  bool get isInProgress => status.isInProgress;

  /// Check if processing is completed
  bool get isCompleted => status.isCompleted;

  /// Check if processing has failed
  bool get isFailed => status.isFailed;
}