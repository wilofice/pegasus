import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:dio/dio.dart';
import 'package:http_parser/http_parser.dart';

class PegasusApiClient {
  final String baseUrl;
  final String? token;
  late final Dio _dio;

  PegasusApiClient({this.baseUrl = 'http://127.0.0.1:8000', this.token}) {
    _dio = Dio(BaseOptions(
      baseUrl: baseUrl,
      headers: {
        if (token != null) 'Authorization': token!,
      },
    ));
  }

  Future<String> sendMessage(String message) async {
    final uri = Uri.parse('$baseUrl/chat');
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
  Future<Map<String, dynamic>> uploadAudioFile(File audioFile) async {
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
      
      final response = await _dio.get('/api/audio/', queryParameters: queryParams);
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
      final response = await _dio.get('/api/audio/$audioId');
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
      final response = await _dio.get('/api/audio/$audioId/transcript', 
        queryParameters: {'improved': improved});
      if (response.statusCode == 200) {
        return response.data as Map<String, dynamic>;
      }
      return null;
    } catch (e) {
      throw Exception('Failed to get transcript: $e');
    }
  }

  /// Update audio file tags
  Future<bool> updateAudioTags(String audioId, {String? tag, String? category}) async {
    try {
      final data = <String, dynamic>{};
      if (tag != null) data['tag'] = tag;
      if (category != null) data['category'] = category;
      
      final response = await _dio.put('/api/audio/$audioId/tags', data: data);
      return response.statusCode == 200;
    } catch (e) {
      throw Exception('Failed to update audio tags: $e');
    }
  }

  /// Get available tags and categories
  Future<Map<String, List<String>>> getAvailableTags({String? userId}) async {
    try {
      final queryParams = <String, dynamic>{};
      if (userId != null) queryParams['user_id'] = userId;
      
      final response = await _dio.get('/api/audio/tags', queryParameters: queryParams);
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
      final response = await _dio.delete('/api/audio/$fileId');
      return response.statusCode == 200;
    } catch (e) {
      throw Exception('Failed to delete audio file: $e');
    }
  }
}
