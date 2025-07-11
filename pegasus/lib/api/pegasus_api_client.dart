import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:dio/dio.dart';
import 'package:http_parser/http_parser.dart';
import '../config/api_config.dart';
import '../models/game_model.dart';

class PegasusApiClient {
  final String baseUrl;
  final String? token;
  late final Dio _dio;

  PegasusApiClient({
    String? baseUrl, 
    String? token
  }) : baseUrl = baseUrl ?? ApiConfig.baseUrl,
       token = token ?? ApiConfig.defaultToken {
    _dio = Dio(BaseOptions(
      baseUrl: this.baseUrl,
      connectTimeout: Duration(seconds: ApiConfig.connectionTimeoutSeconds),
      receiveTimeout: Duration(seconds: ApiConfig.timeoutSeconds),
      headers: {
        if (this.token != null) 'Authorization': this.token!,
      },
    ));
  }

  /// Create a client with default configuration
  factory PegasusApiClient.defaultConfig() {
    return PegasusApiClient();
  }

  Future<String> sendMessage(String message) async {
    final uri = Uri.parse(ApiConfig.getFullUrl(ApiConfig.chatEndpoint));
    final response = await http.post(
      uri,
      headers: {
        'Content-Type': 'application/json',
        if (token != null) 'Authorization': token!,
      },
      body: jsonEncode({'message': message}),
    );

    if (response.statusCode != 200) {
      throw Exception('Failed to send message: ${response.statusCode}');
    }

    final Map<String, dynamic> data = jsonDecode(response.body);
    return data['response'] as String;
  }

  /// Upload an audio file to the backend
  Future<Map<String, dynamic>> uploadAudioFile(File audioFile, {String? language}) async {
    try {
      final fileName = audioFile.path.split('/').last;
      final mimeType = _getMimeTypeFromFileName(fileName);
      
      final formData = FormData.fromMap({
        'file': await MultipartFile.fromFile(
          audioFile.path,
          filename: fileName,
          contentType: MediaType.parse(mimeType),
        ),
        'user_id': 'flutter_user', // Add a default user ID
        if (language != null) 'language': language,
      });

      final response = await _dio.post(
        ApiConfig.audioUploadEndpoint,
        data: formData,
        options: Options(
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        ),
      );

      if (response.statusCode == 200) {
        return response.data as Map<String, dynamic>;
      } else {
        throw Exception('Upload failed with status: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Failed to upload audio file: $e');
    }
  }

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
      case 'aac':
        return 'audio/aac';
      case 'flac':
        return 'audio/flac';
      case 'webm':
        return 'audio/webm';
      default:
        return 'audio/mpeg'; // Default fallback
    }
  }

  /// Get audio file duration (simplified - you might want to use a proper audio library)
  Future<double> _getAudioDuration(File audioFile) async {
    try {
      final stats = await audioFile.stat();
      // This is a rough estimation - for actual duration, use an audio library
      return stats.size / 32000.0; // Rough estimate based on bitrate
    } catch (e) {
      return 0.0;
    }
  }

  /// Get uploaded audio files list
  Future<List<Map<String, dynamic>>> getAudioFiles({
    String? userId,
    String? status,
    String? tag,
    String? category,
    int limit = 20,
    int offset = 0,
  }) async {
    try {
      final queryParams = <String, dynamic>{
        'limit': limit,
        'offset': offset,
      };
      
      if (userId != null) queryParams['user_id'] = userId;
      if (status != null) queryParams['status'] = status;
      if (tag != null) queryParams['tag'] = tag;
      if (category != null) queryParams['category'] = category;
      
      final response = await _dio.get(ApiConfig.audioListEndpoint, queryParameters: queryParams);
      if (response.statusCode == 200) {
        return List<Map<String, dynamic>>.from(response.data['items'] ?? []);
      }
      return [];
    } catch (e) {
      throw Exception('Failed to get audio files: $e');
    }
  }

  /// Get audio file details by ID
  Future<Map<String, dynamic>?> getAudioFile(String audioId) async {
    try {
      final response = await _dio.get('${ApiConfig.audioDetailsEndpoint}$audioId');
      if (response.statusCode == 200) {
        return response.data as Map<String, dynamic>;
      }
      return null;
    } catch (e) {
      throw Exception('Failed to get audio file: $e');
    }
  }

  /// Get transcript for an audio file
  Future<Map<String, dynamic>?> getTranscript(String audioId, {bool improved = true}) async {
    try {
      final response = await _dio.get('${ApiConfig.transcriptEndpoint}$audioId/transcript', 
        queryParameters: {'improved': improved});
      if (response.statusCode == 200) {
        return response.data as Map<String, dynamic>;
      }
      return null;
    } catch (e) {
      throw Exception('Failed to get transcript: $e');
    }
  }

  /// Get both original and improved transcripts for an audio file
  Future<Map<String, String?>> getBothTranscripts(String audioId) async {
    try {
      // Get improved transcript
      final improvedResponse = await _dio.get('${ApiConfig.transcriptEndpoint}$audioId/transcript', 
        queryParameters: {'improved': true});
      
      // Get original transcript
      final originalResponse = await _dio.get('${ApiConfig.transcriptEndpoint}$audioId/transcript', 
        queryParameters: {'improved': false});
      
      String? improvedTranscript;
      String? originalTranscript;
      
      if (improvedResponse.statusCode == 200) {
        final data = improvedResponse.data as Map<String, dynamic>;
        improvedTranscript = data['transcript'] as String?;
      }
      
      if (originalResponse.statusCode == 200) {
        final data = originalResponse.data as Map<String, dynamic>;
        originalTranscript = data['transcript'] as String?;
      }
      
      return {
        'original': originalTranscript,
        'improved': improvedTranscript,
      };
    } catch (e) {
      throw Exception('Failed to get transcripts: $e');
    }
  }

  /// Update audio file tags (supports multiple tags)
  Future<bool> updateAudioTags(String audioId, {List<String>? tags, String? category}) async {
    try {
      final data = <String, dynamic>{};
      if (tags != null) data['tags'] = tags;
      if (category != null) data['category'] = category;
      
      final response = await _dio.put('${ApiConfig.updateTagsEndpoint}$audioId/tags', data: data);
      return response.statusCode == 200;
    } catch (e) {
      throw Exception('Failed to update audio tags: $e');
    }
  }

  /// Update transcript and tags before processing
  Future<Map<String, dynamic>?> updateTranscriptAndTags(
    String audioId, 
    String improvedTranscript, 
    List<String> tags, 
    {String? category}
  ) async {
    try {
      final data = <String, dynamic>{
        'improved_transcript': improvedTranscript,
        'tags': tags,
      };
      if (category != null) data['category'] = category;
      
      final response = await _dio.put('${ApiConfig.updateTagsEndpoint}$audioId/transcript-and-tags', data: data);
      if (response.statusCode == 200) {
        return response.data as Map<String, dynamic>;
      }
      return null;
    } catch (e) {
      throw Exception('Failed to update transcript and tags: $e');
    }
  }

  /// Start processing after user review and approval
  Future<bool> startProcessing(String audioId) async {
    try {
      final response = await _dio.post('${ApiConfig.updateTagsEndpoint}$audioId/start-processing');
      return response.statusCode == 200;
    } catch (e) {
      throw Exception('Failed to start processing: $e');
    }
  }

  /// Get available tags and categories
  Future<Map<String, List<String>>> getAvailableTags({String? userId}) async {
    try {
      final queryParams = <String, dynamic>{};
      if (userId != null) queryParams['user_id'] = userId;
      
      final response = await _dio.get(ApiConfig.tagsEndpoint, queryParameters: queryParams);
      if (response.statusCode == 200) {
        final data = response.data as Map<String, dynamic>;
        return {
          'tags': List<String>.from(data['tags'] ?? []),
          'categories': List<String>.from(data['categories'] ?? []),
        };
      }
      return {'tags': [], 'categories': []};
    } catch (e) {
      print('Failed to get available tags: $e');
      throw Exception('Tag retrieval failed. See logs');
    }
  }

  /// Delete an uploaded audio file
  Future<bool> deleteAudioFile(String fileId) async {
    try {
      final response = await _dio.delete('${ApiConfig.deleteAudioEndpoint}$fileId');
      return response.statusCode == 200;
    } catch (e) {
      throw Exception('Failed to delete audio file: $e');
    }
  }

  // GAME API METHODS

  /// Start a new game session
  Future<GameStartResponse> startGame(GameStartRequest request) async {
    try {
      final response = await _dio.post('/game/start', data: request.toJson());
      if (response.statusCode == 200) {
        return GameStartResponse.fromJson(response.data as Map<String, dynamic>);
      } else {
        throw Exception('Failed to start game: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Failed to start game: $e');
    }
  }

  /// Submit an answer for the current question
  Future<GameAnswerResponse> submitAnswer(String sessionId, GameAnswerRequest request) async {
    try {
      final response = await _dio.post('/game/answer/$sessionId', data: request.toJson());
      if (response.statusCode == 200) {
        return GameAnswerResponse.fromJson(response.data as Map<String, dynamic>);
      } else {
        throw Exception('Failed to submit answer: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Failed to submit answer: $e');
    }
  }

  /// Get game summary and final results
  Future<GameSummary> getGameSummary(String sessionId) async {
    try {
      final response = await _dio.get('/game/summary/$sessionId');
      if (response.statusCode == 200) {
        return GameSummary.fromJson(response.data as Map<String, dynamic>);
      } else {
        throw Exception('Failed to get game summary: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Failed to get game summary: $e');
    }
  }

  /// Get current game session details (for debugging)
  Future<Map<String, dynamic>?> getGameSession(String sessionId) async {
    try {
      final response = await _dio.get('/game/session/$sessionId');
      if (response.statusCode == 200) {
        return response.data as Map<String, dynamic>;
      } else {
        return null;
      }
    } catch (e) {
      throw Exception('Failed to get game session: $e');
    }
  }

  /// Delete a game session
  Future<bool> deleteGameSession(String sessionId) async {
    try {
      final response = await _dio.delete('/game/session/$sessionId');
      return response.statusCode == 200;
    } catch (e) {
      throw Exception('Failed to delete game session: $e');
    }
  }

  /// Check game service health
  Future<Map<String, dynamic>?> checkGameHealth() async {
    try {
      final response = await _dio.get('/game/health');
      if (response.statusCode == 200) {
        return response.data as Map<String, dynamic>;
      } else {
        return null;
      }
    } catch (e) {
      throw Exception('Failed to check game health: $e');
    }
  }

  // PLUGIN API METHODS

  /// Execute plugins for a transcript
  Future<Map<String, dynamic>> executePlugins(String audioId, {List<String>? pluginTypes}) async {
    try {
      final data = {
        'audio_id': audioId,
        if (pluginTypes != null) 'plugin_types': pluginTypes,
      };
      
      final response = await _dio.post(ApiConfig.pluginExecuteEndpoint, data: data);
      if (response.statusCode == 200) {
        return response.data as Map<String, dynamic>;
      } else {
        throw Exception('Plugin execution failed with status: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Failed to execute plugins: $e');
    }
  }

  /// Execute a single plugin
  Future<Map<String, dynamic>> executeSinglePlugin(
    String audioId, 
    String pluginName, 
    {Map<String, dynamic>? pluginConfig}
  ) async {
    try {
      final data = {
        'audio_id': audioId,
        'plugin_name': pluginName,
        if (pluginConfig != null) 'plugin_config': pluginConfig,
      };
      
      final response = await _dio.post(ApiConfig.pluginExecuteSingleEndpoint, data: data);
      if (response.statusCode == 200) {
        return response.data as Map<String, dynamic>;
      } else {
        throw Exception('Single plugin execution failed with status: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Failed to execute single plugin: $e');
    }
  }

  /// Get plugin execution results for an audio file
  Future<Map<String, dynamic>> getPluginResults(String audioId, {String? pluginName}) async {
    try {
      final queryParams = <String, dynamic>{};
      if (pluginName != null) queryParams['plugin_name'] = pluginName;
      
      final response = await _dio.get(
        '${ApiConfig.pluginResultsEndpoint}$audioId',
        queryParameters: queryParams
      );
      
      if (response.statusCode == 200) {
        return response.data as Map<String, dynamic>;
      } else {
        throw Exception('Failed to get plugin results with status: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Failed to get plugin results: $e');
    }
  }

  /// Get available plugins list
  Future<List<Map<String, dynamic>>> getPluginsList({String? pluginType, String? status}) async {
    try {
      final queryParams = <String, dynamic>{};
      if (pluginType != null) queryParams['plugin_type'] = pluginType;
      if (status != null) queryParams['status'] = status;
      
      final response = await _dio.get(ApiConfig.pluginsEndpoint, queryParameters: queryParams);
      if (response.statusCode == 200) {
        return List<Map<String, dynamic>>.from(response.data ?? []);
      }
      return [];
    } catch (e) {
      throw Exception('Failed to get plugins list: $e');
    }
  }

  /// Get plugin status overview
  Future<Map<String, dynamic>> getPluginStatus() async {
    try {
      final response = await _dio.get(ApiConfig.pluginStatusEndpoint);
      if (response.statusCode == 200) {
        return response.data as Map<String, dynamic>;
      } else {
        throw Exception('Failed to get plugin status with status: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Failed to get plugin status: $e');
    }
  }

  /// Search context using the context aggregator
  Future<Map<String, dynamic>> searchContext(
    String query, {
    int maxResults = 20,
    String strategy = 'hybrid',
    double? vectorWeight,
    double? graphWeight,
    bool includeRelated = true,
    Map<String, dynamic>? filters,
  }) async {
    try {
      final data = {
        'query': query,
        'max_results': maxResults,
        'strategy': strategy,
        'include_related': includeRelated,
        if (vectorWeight != null) 'vector_weight': vectorWeight,
        if (graphWeight != null) 'graph_weight': graphWeight,
        if (filters != null) 'filters': filters,
      };
      
      final response = await _dio.post(ApiConfig.contextSearchEndpoint, data: data);
      if (response.statusCode == 200) {
        return response.data as Map<String, dynamic>;
      } else {
        throw Exception('Context search failed with status: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Failed to search context: $e');
    }
  }
}
