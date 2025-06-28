import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:path_provider/path_provider.dart';
import 'package:http/http.dart' as http;

class ModelDownloader {
  static const String baseUrl = 'https://huggingface.co/microsoft/Phi-3-mini-4K-instruct-onnx/resolve/main/cpu_and_mobile/cpu-int4-rtn-block-32-acc-level-4/';
  static const String modelName = 'phi3-mini-4k-instruct-cpu-int4-rtn-block-32-acc-level-4';
  
  Future<String> getModelPath() async {
    final directory = await getApplicationDocumentsDirectory();
    final modelDir = Directory('${directory.path}/models');
    await modelDir.create(recursive: true);
    return '${modelDir.path}/$modelName.onnx';
  }
  
  Future<String> getModelDataPath() async {
    final modelPath = await getModelPath();
    return modelPath.replaceAll('.onnx', '.onnx.data');
  }
  
  Future<bool> isModelDownloaded() async {
    try {
      final modelPath = await getModelPath();
      final dataPath = await getModelDataPath();
      final modelFile = File(modelPath);
      final dataFile = File(dataPath);
      
      final modelExists = await modelFile.exists();
      final dataExists = await dataFile.exists();
      
      if (!modelExists || !dataExists) {
        return false;
      }
      
      // Check if files have reasonable sizes (not empty or corrupted)
      final modelSize = await modelFile.length();
      final dataSize = await dataFile.length();
      
      // Model file should be at least 1MB, data file should be much larger
      return modelSize > 1024 * 1024 && dataSize > 10 * 1024 * 1024;
    } catch (e) {
      debugPrint('Error checking model download status: $e');
      return false;
    }
  }
  
  Future<void> downloadModelWithProgress(Function(double, String) onProgress) async {
    try {
      final modelPath = await getModelPath();
      final dataPath = await getModelDataPath();
      
      onProgress(0.0, 'Starting download...');
      
      // Download model file first (smaller)
      onProgress(0.1, 'Downloading model file...');
      await _downloadFileWithProgress(
        '$baseUrl$modelName.onnx', 
        modelPath, 
        (progress) {
          onProgress(0.1 + progress * 0.2, 'Downloading model file... ${(progress * 100).toInt()}%');
        }
      );
      
      // Download data file (larger)
      onProgress(0.3, 'Downloading model data...');
      await _downloadFileWithProgress(
        '$baseUrl$modelName.onnx.data', 
        dataPath, 
        (progress) {
          onProgress(0.3 + progress * 0.7, 'Downloading model data... ${(progress * 100).toInt()}%');
        }
      );
      
      onProgress(1.0, 'Download complete!');
    } catch (e) {
      throw Exception('Failed to download model: $e');
    }
  }
  
  Future<void> _downloadFileWithProgress(String url, String savePath, Function(double) onProgress) async {
    try {
      final request = http.Request('GET', Uri.parse(url));
      final response = await request.send();
      
      if (response.statusCode != 200) {
        throw Exception('Failed to download file: HTTP ${response.statusCode}');
      }
      
      final file = File(savePath);
      final sink = file.openWrite();
      
      int downloaded = 0;
      final total = response.contentLength ?? 0;
      
      await response.stream.listen(
        (chunk) {
          downloaded += chunk.length;
          sink.add(chunk);
          if (total > 0) {
            onProgress(downloaded / total);
          }
        },
        onDone: () {
          sink.close();
        },
        onError: (error) {
          sink.close();
          throw error;
        },
      ).asFuture();
      
    } catch (e) {
      throw Exception('Download failed: $e');
    }
  }
  
  Future<void> deleteModel() async {
    try {
      final modelPath = await getModelPath();
      final dataPath = await getModelDataPath();
      
      final modelFile = File(modelPath);
      final dataFile = File(dataPath);
      
      if (await modelFile.exists()) {
        await modelFile.delete();
      }
      
      if (await dataFile.exists()) {
        await dataFile.delete();
      }
    } catch (e) {
      debugPrint('Error deleting model files: $e');
    }
  }
  
  Future<double> getModelSize() async {
    try {
      final modelPath = await getModelPath();
      final dataPath = await getModelDataPath();
      
      final modelFile = File(modelPath);
      final dataFile = File(dataPath);
      
      double totalSize = 0;
      
      if (await modelFile.exists()) {
        totalSize += await modelFile.length();
      }
      
      if (await dataFile.exists()) {
        totalSize += await dataFile.length();
      }
      
      // Return size in MB
      return totalSize / (1024 * 1024);
    } catch (e) {
      debugPrint('Error getting model size: $e');
      return 0;
    }
  }
  
  Future<String> getModelDirectory() async {
    final directory = await getApplicationDocumentsDirectory();
    return '${directory.path}/models';
  }
}