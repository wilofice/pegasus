import 'dart:convert';
import 'package:http/http.dart' as http;

class PegasusApiClient {
  final String baseUrl;
  final String? token;

  PegasusApiClient({required this.baseUrl, this.token});

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
}
