import 'package:shared_preferences/shared_preferences.dart';

class PrefsService {
  static const String _kMaxRecordingSec = 'max_recording_sec';
  static const String _kAutoUploadAudio = 'auto_upload_audio';
  static const String _kAudioQuality = 'audio_quality';
  static const String _kSaveToGallery = 'save_to_gallery';
  static const String _kRecordingLanguage = 'recording_language';
  
  // Default values
  static const int defaultMaxRecordingSec = 60; // 1 minute
  static const bool defaultAutoUpload = true;
  static const String defaultAudioQuality = 'medium'; // low, medium, high
  static const bool defaultSaveToGallery = false;
  static const String defaultRecordingLanguage = 'en'; // en, fr
  
  /// Get maximum recording duration in seconds
  Future<int> getMaxRecordingSec() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getInt(_kMaxRecordingSec) ?? defaultMaxRecordingSec;
  }
  
  /// Set maximum recording duration in seconds
  Future<void> setMaxRecordingSec(int seconds) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setInt(_kMaxRecordingSec, seconds);
  }
  
  /// Get auto-upload preference
  Future<bool> getAutoUploadAudio() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getBool(_kAutoUploadAudio) ?? defaultAutoUpload;
  }
  
  /// Set auto-upload preference
  Future<void> setAutoUploadAudio(bool autoUpload) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_kAutoUploadAudio, autoUpload);
  }
  
  /// Get audio quality setting
  Future<String> getAudioQuality() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_kAudioQuality) ?? defaultAudioQuality;
  }
  
  /// Set audio quality setting
  Future<void> setAudioQuality(String quality) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_kAudioQuality, quality);
  }
  
  /// Get save to gallery preference
  Future<bool> getSaveToGallery() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getBool(_kSaveToGallery) ?? defaultSaveToGallery;
  }
  
  /// Set save to gallery preference
  Future<void> setSaveToGallery(bool saveToGallery) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_kSaveToGallery, saveToGallery);
  }
  
  /// Get recording language setting
  Future<String> getRecordingLanguage() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_kRecordingLanguage) ?? defaultRecordingLanguage;
  }
  
  /// Set recording language setting
  Future<void> setRecordingLanguage(String language) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_kRecordingLanguage, language);
  }
  
  /// Get all audio recording preferences as a map
  Future<Map<String, dynamic>> getAllAudioPrefs() async {
    return {
      'maxRecordingSec': await getMaxRecordingSec(),
      'autoUpload': await getAutoUploadAudio(),
      'audioQuality': await getAudioQuality(),
      'saveToGallery': await getSaveToGallery(),
      'recordingLanguage': await getRecordingLanguage(),
    };
  }
  
  /// Reset all audio preferences to defaults
  Future<void> resetAudioPrefs() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_kMaxRecordingSec);
    await prefs.remove(_kAutoUploadAudio);
    await prefs.remove(_kAudioQuality);
    await prefs.remove(_kSaveToGallery);
    await prefs.remove(_kRecordingLanguage);
  }
  
  /// Get recording configuration based on quality setting
  Map<String, dynamic> getRecordingConfig(String quality) {
    switch (quality.toLowerCase()) {
      case 'low':
        return {
          'bitRate': 64000,
          'samplingRate': 22050,
        };
      case 'high':
        return {
          'bitRate': 256000,
          'samplingRate': 48000,
        };
      case 'medium':
      default:
        return {
          'bitRate': 128000,
          'samplingRate': 44100,
        };
    }
  }
}