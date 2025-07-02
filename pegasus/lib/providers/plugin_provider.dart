import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../api/pegasus_api_client.dart';
import '../models/plugin_model.dart';

/// State for plugin execution results
class PluginState {
  final bool isLoading;
  final PluginExecutionResponse? results;
  final String? error;
  final bool isExecuting;

  const PluginState({
    this.isLoading = false,
    this.results,
    this.error,
    this.isExecuting = false,
  });

  PluginState copyWith({
    bool? isLoading,
    PluginExecutionResponse? results,
    String? error,
    bool? isExecuting,
  }) {
    return PluginState(
      isLoading: isLoading ?? this.isLoading,
      results: results ?? this.results,
      error: error ?? this.error,
      isExecuting: isExecuting ?? this.isExecuting,
    );
  }
}

/// Provider for managing plugin execution and results
class PluginNotifier extends StateNotifier<PluginState> {
  final PegasusApiClient _apiClient;

  PluginNotifier(this._apiClient) : super(const PluginState());

  /// Load plugin results for a specific audio file
  Future<void> loadPluginResults(String audioId, {String? pluginName}) async {
    state = state.copyWith(isLoading: true, error: null);
    
    try {
      final response = await _apiClient.getPluginResults(audioId, pluginName: pluginName);
      final results = PluginExecutionResponse.fromJson(response);
      state = state.copyWith(isLoading: false, results: results);
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: 'Failed to load plugin results: ${e.toString()}',
      );
    }
  }

  /// Execute plugins for an audio file
  Future<void> executePlugins(String audioId, {List<String>? pluginTypes}) async {
    state = state.copyWith(isExecuting: true, error: null);
    
    try {
      await _apiClient.executePlugins(audioId, pluginTypes: pluginTypes);
      state = state.copyWith(isExecuting: false);
      
      // Wait a moment for processing to start, then load results
      await Future.delayed(const Duration(seconds: 2));
      await loadPluginResults(audioId);
    } catch (e) {
      state = state.copyWith(
        isExecuting: false,
        error: 'Failed to execute plugins: ${e.toString()}',
      );
    }
  }

  /// Execute the review reflection plugin specifically
  Future<void> executeReviewReflectionPlugin(String audioId, {Map<String, dynamic>? config}) async {
    state = state.copyWith(isExecuting: true, error: null);
    
    try {
      await _apiClient.executeSinglePlugin(
        audioId, 
        'ReviewReflectionPlugin',
        pluginConfig: config,
      );
      state = state.copyWith(isExecuting: false);
      
      // Wait for processing to complete, then load results
      await Future.delayed(const Duration(seconds: 3));
      await loadPluginResults(audioId, pluginName: 'review_reflection');
    } catch (e) {
      state = state.copyWith(
        isExecuting: false,
        error: 'Failed to execute review reflection plugin: ${e.toString()}',
      );
    }
  }

  /// Clear current results and error state
  void clearResults() {
    state = const PluginState();
  }

  /// Clear only the error state
  void clearError() {
    state = state.copyWith(error: null);
  }
}

/// Provider for the plugin notifier
final pluginProvider = StateNotifierProvider<PluginNotifier, PluginState>((ref) {
  final apiClient = PegasusApiClient.defaultConfig();
  return PluginNotifier(apiClient);
});

/// Provider for plugin status overview
final pluginStatusProvider = FutureProvider<Map<String, dynamic>>((ref) async {
  final apiClient = PegasusApiClient.defaultConfig();
  return await apiClient.getPluginStatus();
});

/// Provider for available plugins list
final pluginsListProvider = FutureProvider.family<List<Map<String, dynamic>>, Map<String, String?>>((ref, filters) async {
  final apiClient = PegasusApiClient.defaultConfig();
  return await apiClient.getPluginsList(
    pluginType: filters['pluginType'],
    status: filters['status'],
  );
});

/// Provider for review reflection data from current plugin state
final reviewReflectionDataProvider = Provider<ReviewReflectionData?>((ref) {
  final pluginState = ref.watch(pluginProvider);
  return pluginState.results?.getReviewReflectionData();
});