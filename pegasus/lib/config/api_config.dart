/// API configuration for the Pegasus app
class ApiConfig {
  /// Base URL for the Pegasus backend API
  /// 
  /// Update this URL to point to your backend server:
  /// - Development: 'http://192.168.1.15:9000' or 'http://localhost:9000'
  /// - Production: 'https://your-api.domain.com'
  static const String baseUrl = 'http://192.168.1.15:9000';
  
  /// Default authentication token (if needed)
  /// Set to null if no authentication is required
  static const String? defaultToken = 'empty';
  
  /// API timeout duration in seconds
  static const int timeoutSeconds = 30;
  
  /// Connection timeout duration in seconds
  static const int connectionTimeoutSeconds = 10;
  
  /// Endpoints
  static const String chatEndpoint = '/chat';
  static const String audioUploadEndpoint = '/api/audio/upload';
  static const String audioListEndpoint = '/api/audio/';
  static const String audioDetailsEndpoint = '/api/audio/';  // append /{id}
  static const String transcriptEndpoint = '/api/audio/';    // append /{id}/transcript
  static const String tagsEndpoint = '/api/audio/tags';
  static const String updateTagsEndpoint = '/api/audio/';    // append /{id}/tags
  static const String deleteAudioEndpoint = '/api/audio/';   // append /{id}
  
  /// Plugin endpoints
  static const String pluginsEndpoint = '/plugins';
  static const String pluginExecuteEndpoint = '/plugins/execute';
  static const String pluginExecuteSingleEndpoint = '/plugins/execute-single';
  static const String pluginStatusEndpoint = '/plugins/status/overview';
  static const String pluginResultsEndpoint = '/plugins/results/';  // append /{audio_id}
  static const String contextSearchEndpoint = '/context/search';
  
  /// Get the full URL for an endpoint
  static String getFullUrl(String endpoint) {
    if (endpoint.startsWith('http')) {
      return endpoint;
    }
    return '$baseUrl$endpoint';
  }
  
  /// Get audio details URL for a specific audio ID
  static String getAudioDetailsUrl(String audioId) {
    return '$baseUrl$audioDetailsEndpoint$audioId';
  }
  
  /// Get transcript URL for a specific audio ID
  static String getTranscriptUrl(String audioId) {
    return '$baseUrl$transcriptEndpoint$audioId/transcript';
  }
  
  /// Get update tags URL for a specific audio ID
  static String getUpdateTagsUrl(String audioId) {
    return '$baseUrl$updateTagsEndpoint$audioId/tags';
  }
  
  /// Get delete audio URL for a specific audio ID
  static String getDeleteAudioUrl(String audioId) {
    return '$baseUrl$deleteAudioEndpoint$audioId';
  }
}