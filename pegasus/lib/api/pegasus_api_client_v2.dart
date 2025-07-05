// Enhanced Pegasus API Client V2 for advanced backend integration
// 
// This client supports all the enhanced backend capabilities including:
// - Chat V2 with context awareness and citations
// - Context search with multiple strategies
// - Plugin system management and execution
// - Enhanced audio processing with real-time updates
// - Comprehensive error handling and retry logic
import 'dart:io';
import 'package:dio/dio.dart';
import 'package:http_parser/http_parser.dart';

import '../config/api_config.dart';
import '../models/api_enums.dart';
import '../models/chat_v2_models.dart';
import '../models/context_search_models.dart';
import '../models/plugin_models.dart';
import '../models/audio_models.dart';
import '../models/game_models_v2.dart';

/// Enhanced API client with comprehensive backend integration
class PegasusApiClientV2 {
  final String baseUrl;
  final String? token;
  late final Dio _dio;

  PegasusApiClientV2({
    String? baseUrl,
    String? token,
  }) : baseUrl = baseUrl ?? ApiConfig.baseUrl,
       token = token ?? ApiConfig.defaultToken {
    _dio = Dio(BaseOptions(
      baseUrl: this.baseUrl,
      connectTimeout: Duration(seconds: ApiConfig.connectionTimeoutSeconds),
      receiveTimeout: Duration(seconds: ApiConfig.timeoutSeconds),
      headers: {
        'Content-Type': 'application/json',
        if (this.token != null) 'Authorization': this.token!,
      },
    ));

    // Add interceptors for logging and error handling
    _dio.interceptors.add(LogInterceptor(
      requestBody: true,
      responseBody: true,
      error: true,
      logPrint: (obj) => print('[API] $obj'),
    ));

    _dio.interceptors.add(InterceptorsWrapper(
      onError: (error, handler) {
        print('[API Error] ${error.message}');
        if (error.response != null) {
          print('[API Error Response] ${error.response?.data}');
        }
        handler.next(error);
      },
    ));
  }

  /// Create a client with default configuration
  factory PegasusApiClientV2.defaultConfig() {
    return PegasusApiClientV2();
  }

  // =============================================================================
  // CHAT V2 API ENDPOINTS
  // =============================================================================

  /// Send message using Chat V2 API with advanced features
  Future<ChatResponseV2> sendMessageV2(ChatRequestV2 request) async {
    try {
      final response = await _dio.post(
        '/chat/v2/',
        data: request.toJson(),
      );

      return ChatResponseV2.fromJson(response.data);
    } catch (e) {
      throw _handleApiError(e, 'Failed to send message');
    }
  }

  /// Alias for sendMessageV2 for backward compatibility
  Future<ChatResponseV2> chatV2(ChatRequestV2 request) async {
    return sendMessageV2(request);
  }

  /// Get session information
  Future<SessionInfo> getSessionInfo(String sessionId) async {
    try {
      final response = await _dio.get('/chat/v2/session/$sessionId');
      return SessionInfo.fromJson(response.data);
    } catch (e) {
      throw _handleApiError(e, 'Failed to get session info');
    }
  }

  /// Delete chat session
  Future<void> deleteSession(String sessionId) async {
    try {
      await _dio.delete('/chat/v2/session/$sessionId');
    } catch (e) {
      throw _handleApiError(e, 'Failed to delete session');
    }
  }

  /// Check Chat V2 health
  Future<ChatHealthResponse> getChatHealth() async {
    try {
      final response = await _dio.get('/chat/v2/health');
      return ChatHealthResponse.fromJson(response.data);
    } catch (e) {
      throw _handleApiError(e, 'Failed to check chat health');
    }
  }

  // =============================================================================
  // CONTEXT SEARCH API ENDPOINTS
  // =============================================================================

  /// Search context using advanced strategies
  Future<List<ContextSearchResult>> searchContext(ContextSearchRequest request) async {
    try {
      final response = await _dio.post(
        '/context/search',
        data: request.toJson(),
      );

      final searchResponse = ContextSearchResponse.fromJson(response.data);
      return searchResponse.results.map((result) => 
        ContextSearchResult(
          id: result.id,
          summary: result.previewContent,
          sources: [result],
          searchStrategy: request.strategy,
          overallConfidence: result.relevanceScore,
          processingTimeMs: searchResponse.totalResults.toDouble(),
        )
      ).toList();
    } catch (e) {
      throw _handleApiError(e, 'Failed to search context');
    }
  }

  /// Search context using GET method (simplified)
  Future<ContextSearchResponse> searchContextGet({
    required String query,
    int maxResults = 20,
    SearchStrategy strategy = SearchStrategy.hybrid,
    double? vectorWeight,
    double? graphWeight,
    bool includeRelated = true,
  }) async {
    try {
      final params = {
        'query': query,
        'max_results': maxResults.toString(),
        'strategy': strategy.value,
        'include_related': includeRelated.toString(),
      };

      if (vectorWeight != null) params['vector_weight'] = vectorWeight.toString();
      if (graphWeight != null) params['graph_weight'] = graphWeight.toString();

      final response = await _dio.get(
        '/context/search',
        queryParameters: params,
      );

      return ContextSearchResponse.fromJson(response.data);
    } catch (e) {
      throw _handleApiError(e, 'Failed to search context');
    }
  }

  /// Get available search strategies
  Future<SearchStrategiesInfo> getSearchStrategies() async {
    try {
      final response = await _dio.get('/context/strategies');
      return SearchStrategiesInfo.fromJson(response.data);
    } catch (e) {
      throw _handleApiError(e, 'Failed to get search strategies');
    }
  }

  /// Check context search health
  Future<ContextHealthResponse> getContextHealth() async {
    try {
      final response = await _dio.get('/context/health');
      return ContextHealthResponse.fromJson(response.data);
    } catch (e) {
      throw _handleApiError(e, 'Failed to check context health');
    }
  }

  // =============================================================================
  // PLUGIN SYSTEM API ENDPOINTS
  // =============================================================================

  /// Get list of all plugins
  Future<List<PluginInfo>> getPlugins({
    String? pluginType,
    String? status,
  }) async {
    try {
      final params = <String, String>{};
      if (pluginType != null) params['plugin_type'] = pluginType;
      if (status != null) params['status'] = status;

      final response = await _dio.get(
        '/plugins/',
        queryParameters: params.isNotEmpty ? params : null,
      );

      return (response.data as List<dynamic>)
          .map((plugin) => PluginInfo.fromJson(plugin as Map<String, dynamic>))
          .toList();
    } catch (e) {
      throw _handleApiError(e, 'Failed to get plugins');
    }
  }

  /// Get specific plugin information
  Future<PluginInfo> getPluginInfo(String pluginName) async {
    try {
      final response = await _dio.get('/plugins/$pluginName');
      return PluginInfo.fromJson(response.data);
    } catch (e) {
      throw _handleApiError(e, 'Failed to get plugin info');
    }
  }

  /// Execute plugins for an audio file
  Future<PluginExecutionResponse> executePlugins(PluginExecutionRequest request) async {
    try {
      final response = await _dio.post(
        '/plugins/execute',
        data: request.toJson(),
      );

      return PluginExecutionResponse.fromJson(response.data);
    } catch (e) {
      throw _handleApiError(e, 'Failed to execute plugins');
    }
  }

  /// Execute a single plugin
  Future<PluginExecutionResponse> executeSinglePlugin(
      SinglePluginExecutionRequest request) async {
    try {
      final response = await _dio.post(
        '/plugins/execute-single',
        data: request.toJson(),
      );

      return PluginExecutionResponse.fromJson(response.data);
    } catch (e) {
      throw _handleApiError(e, 'Failed to execute single plugin');
    }
  }

  /// Reload a plugin
  Future<void> reloadPlugin(String pluginName) async {
    try {
      await _dio.post('/plugins/$pluginName/reload');
    } catch (e) {
      throw _handleApiError(e, 'Failed to reload plugin');
    }
  }

  /// Get plugin system status overview
  Future<PluginSystemStatus> getPluginSystemStatus() async {
    try {
      final response = await _dio.get('/plugins/status/overview');
      return PluginSystemStatus.fromJson(response.data);
    } catch (e) {
      throw _handleApiError(e, 'Failed to get plugin system status');
    }
  }

  /// Get available plugin types
  Future<AvailablePluginTypes> getAvailablePluginTypes() async {
    try {
      final response = await _dio.get('/plugins/types/available');
      return AvailablePluginTypes.fromJson(response.data);
    } catch (e) {
      throw _handleApiError(e, 'Failed to get available plugin types');
    }
  }

  /// Get plugin results for an audio file
  Future<Map<String, dynamic>> getPluginResults(
    String audioId, {
    String? pluginName,
  }) async {
    try {
      final params = <String, String>{};
      if (pluginName != null) params['plugin_name'] = pluginName;

      final response = await _dio.get(
        '/plugins/results/$audioId',
        queryParameters: params.isNotEmpty ? params : null,
      );

      return response.data as Map<String, dynamic>;
    } catch (e) {
      throw _handleApiError(e, 'Failed to get plugin results');
    }
  }

  /// Check plugin system health
  Future<PluginHealthResponse> getPluginHealth() async {
    try {
      final response = await _dio.get('/plugins/health');
      return PluginHealthResponse.fromJson(response.data);
    } catch (e) {
      throw _handleApiError(e, 'Failed to check plugin health');
    }
  }

  // =============================================================================
  // ENHANCED AUDIO API ENDPOINTS
  // =============================================================================

  /// Upload an audio file with enhanced features
  Future<AudioUploadResponse> uploadAudioFile(
    File audioFile, {
    String? userId,
    String? language = 'en',
  }) async {
    try {
      final fileName = audioFile.path.split('/').last;
      final mimeType = _getMimeTypeFromFileName(fileName);

      final formData = FormData.fromMap({
        'file': await MultipartFile.fromFile(
          audioFile.path,
          filename: fileName,
          contentType: MediaType.parse(mimeType),
        ),
        if (userId != null) 'user_id': userId,
        if (language != null) 'language': language,
      });

      final response = await _dio.post(
        '/api/audio/upload',
        data: formData,
        options: Options(
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        ),
      );

      return AudioUploadResponse.fromJson(response.data);
    } catch (e) {
      throw _handleApiError(e, 'Failed to upload audio file');
    }
  }

  /// Get audio file details
  Future<AudioFileResponse> getAudioFile(String audioId) async {
    try {
      final response = await _dio.get('/api/audio/$audioId');
      return AudioFileResponse.fromJson(response.data);
    } catch (e) {
      throw _handleApiError(e, 'Failed to get audio file');
    }
  }

  /// List audio files with filters
  Future<AudioFileListResponse> listAudioFiles(AudioListRequest request) async {
    try {
      final response = await _dio.get(
        '/api/audio/',
        queryParameters: request.toQueryParams(),
      );

      return AudioFileListResponse.fromJson(response.data);
    } catch (e) {
      throw _handleApiError(e, 'Failed to list audio files');
    }
  }

  /// Delete an audio file
  Future<void> deleteAudioFile(String audioId) async {
    try {
      await _dio.delete('/api/audio/$audioId');
    } catch (e) {
      throw _handleApiError(e, 'Failed to delete audio file');
    }
  }

  /// Get transcript for an audio file
  Future<String> getTranscript(String audioId, {bool improved = true}) async {
    try {
      final response = await _dio.get(
        '/api/audio/$audioId/transcript',
        queryParameters: {'improved': improved.toString()},
      );

      // Handle both string and object responses
      if (response.data is String) {
        return response.data;
      } else if (response.data is Map<String, dynamic>) {
        return response.data['transcript'] as String? ?? '';
      } else {
        return response.data.toString();
      }
    } catch (e) {
      throw _handleApiError(e, 'Failed to get transcript');
    }
  }

  /// Download audio file
  Future<Response> downloadAudioFile(String audioId) async {
    try {
      return await _dio.get(
        '/api/audio/$audioId/download',
        options: Options(responseType: ResponseType.bytes),
      );
    } catch (e) {
      throw _handleApiError(e, 'Failed to download audio file');
    }
  }

  /// Update audio file tags
  Future<AudioFileResponse> updateAudioTags(
    String audioId,
    AudioTagUpdateRequest request,
  ) async {
    try {
      final response = await _dio.put(
        '/api/audio/$audioId/tags',
        data: request.toJson(),
      );

      return AudioFileResponse.fromJson(response.data);
    } catch (e) {
      throw _handleApiError(e, 'Failed to update audio tags');
    }
  }

  /// Get available tags and categories
  Future<AudioTagsResponse> getAvailableTags({String? userId}) async {
    try {
      final params = <String, String>{};
      if (userId != null) params['user_id'] = userId;

      final response = await _dio.get(
        '/api/audio/tags',
        queryParameters: params.isNotEmpty ? params : null,
      );

      return AudioTagsResponse.fromJson(response.data);
    } catch (e) {
      throw _handleApiError(e, 'Failed to get available tags');
    }
  }

  // =============================================================================
  // GAME API ENDPOINTS
  // =============================================================================

  /// Start a new game session
  Future<GameStartResponse> startGame(GameStartRequest request) async {
    try {
      final response = await _dio.post(
        '/game/start',
        data: request.toJson(),
      );

      return GameStartResponse.fromJson(response.data);
    } catch (e) {
      throw _handleApiError(e, 'Failed to start game');
    }
  }

  /// Submit an answer for the current question
  Future<GameAnswerResponse> submitAnswer(
    String sessionId,
    GameAnswerRequest request,
  ) async {
    try {
      final response = await _dio.post(
        '/game/answer/$sessionId',
        data: request.toJson(),
      );

      return GameAnswerResponse.fromJson(response.data);
    } catch (e) {
      throw _handleApiError(e, 'Failed to submit answer');
    }
  }

  /// Get game summary and final results
  Future<GameSummaryResponse> getGameSummary(String sessionId) async {
    try {
      final response = await _dio.get('/game/summary/$sessionId');
      return GameSummaryResponse.fromJson(response.data);
    } catch (e) {
      throw _handleApiError(e, 'Failed to get game summary');
    }
  }

  /// Get current game session details
  Future<Map<String, dynamic>> getGameSession(String sessionId) async {
    try {
      final response = await _dio.get('/game/session/$sessionId');
      return response.data as Map<String, dynamic>;
    } catch (e) {
      throw _handleApiError(e, 'Failed to get game session');
    }
  }

  /// Delete a game session
  Future<void> deleteGameSession(String sessionId) async {
    try {
      await _dio.delete('/game/session/$sessionId');
    } catch (e) {
      throw _handleApiError(e, 'Failed to delete game session');
    }
  }

  /// Check game service health
  Future<GameHealthResponse> getGameHealth() async {
    try {
      final response = await _dio.get('/game/health');
      return GameHealthResponse.fromJson(response.data);
    } catch (e) {
      throw _handleApiError(e, 'Failed to check game health');
    }
  }

  // =============================================================================
  // LEGACY SUPPORT
  // =============================================================================

  /// Send message using legacy chat endpoint
  Future<String> sendMessage(String message) async {
    try {
      final response = await _dio.post(
        '/chat/',
        data: {'message': message},
      );

      if (response.data is Map<String, dynamic>) {
        return response.data['response'] as String? ?? '';
      } else {
        return response.data.toString();
      }
    } catch (e) {
      throw _handleApiError(e, 'Failed to send message (legacy)');
    }
  }

  /// Process webhook notifications
  Future<Map<String, dynamic>> processWebhook(String filePath, {String? token}) async {
    try {
      final response = await _dio.post(
        '/webhook/',
        data: {'file_path': filePath},
        options: Options(
          headers: {
            if (token != null) 'X-Token': token,
          },
        ),
      );

      return response.data as Map<String, dynamic>;
    } catch (e) {
      throw _handleApiError(e, 'Failed to process webhook');
    }
  }

  /// General health check
  Future<Map<String, dynamic>> getHealth() async {
    try {
      final response = await _dio.get('/health');
      return response.data as Map<String, dynamic>;
    } catch (e) {
      throw _handleApiError(e, 'Failed to check health');
    }
  }

  // =============================================================================
  // UTILITY METHODS
  // =============================================================================

  /// Get MIME type from file extension
  String _getMimeTypeFromFileName(String fileName) {
    final extension = fileName.split('.').last.toLowerCase();
    switch (extension) {
      case 'm4a':
        return 'audio/mp4';
      case 'mp3':
        return 'audio/mpeg';
      case 'wav':
        return 'audio/wav';
      case 'ogg':
        return 'audio/ogg';
      case 'flac':
        return 'audio/flac';
      case 'aac':
        return 'audio/aac';
      default:
        return 'audio/mpeg'; // Default fallback
    }
  }

  /// Handle API errors with consistent error messages
  Exception _handleApiError(dynamic error, String operation) {
    if (error is DioException) {
      final statusCode = error.response?.statusCode;
      final message = error.response?.data?['detail'] ?? 
                     error.response?.data?['message'] ?? 
                     error.message ?? 
                     'Unknown error';

      switch (statusCode) {
        case 400:
          return Exception('Bad Request: $message');
        case 401:
          return Exception('Unauthorized: Please check your authentication');
        case 403:
          return Exception('Forbidden: Access denied');
        case 404:
          return Exception('Not Found: Resource does not exist');
        case 422:
          return Exception('Validation Error: $message');
        case 500:
          return Exception('Server Error: Please try again later');
        case 503:
          return Exception('Service Unavailable: Please try again later');
        default:
          return Exception('$operation failed: $message');
      }
    } else {
      return Exception('$operation failed: ${error.toString()}');
    }
  }

  /// Close the client and clean up resources
  void close() {
    _dio.close();
  }
}