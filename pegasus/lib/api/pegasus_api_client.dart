import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:dio/dio.dart';

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
      final formData = FormData.fromMap({
        'file': await MultipartFile.fromFile(
          audioFile.path,
          filename: fileName,
        ),
        'timestamp': DateTime.now().toIso8601String(),
        'duration': await _getAudioDuration(audioFile),
      });

      final response = await _dio.post(
        '/upload/audio',
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
  Future<List<Map<String, dynamic>>> getAudioFiles() async {
    try {
      final response = await _dio.get('/audio/list');
      if (response.statusCode == 200) {
        return List<Map<String, dynamic>>.from(response.data['files'] ?? []);
      }
      return [];
    } catch (e) {
      throw Exception('Failed to get audio files: $e');
    }
  }

  /// Delete an uploaded audio file
  Future<bool> deleteAudioFile(String fileId) async {
    try {
      final response = await _dio.delete('/audio/$fileId');
      return response.statusCode == 200;
    } catch (e) {
      throw Exception('Failed to delete audio file: $e');
    }
  }
}
