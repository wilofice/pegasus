import 'dart:io';
import 'package:flutter/services.dart';
import 'package:onnxruntime/onnxruntime.dart';
import 'package:path_provider/path_provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'phi3_tokenizer.dart';

class Phi3ModelManager {
  OrtSession? _session;
  bool _isLoaded = false;
  String? _modelPath;
  late Phi3Tokenizer _tokenizer;
  
  static const String _modelAssetPath = 'assets/models/phi3-mini-4k-instruct-cpu-int4-rtn-block-32-acc-level-4.onnx';
  static const String _modelFileName = 'phi3-mini-4k-instruct-cpu-int4-rtn-block-32-acc-level-4.onnx';
  static const String _prefKeyModelLoaded = 'phi3_model_loaded';
  
  bool get isLoaded => _isLoaded;
  
  Future<void> loadModel() async {
    if (_isLoaded) return;
    
    try {
      final prefs = await SharedPreferences.getInstance();
      final modelLoaded = prefs.getBool(_prefKeyModelLoaded) ?? false;
      
      // Get app documents directory
      final directory = await getApplicationDocumentsDirectory();
      _modelPath = '${directory.path}/$_modelFileName';
      
      // Check if model exists in documents directory
      final modelFile = File(_modelPath!);
      
      if (!modelFile.existsSync() || !modelLoaded) {
        // Copy model from assets to documents directory
        await _copyModelFromAssets(_modelPath!);
        await prefs.setBool(_prefKeyModelLoaded, true);
      }
      
      // Initialize ONNX Runtime
      OrtEnv.instance.init();
      
      // Create session options
      final sessionOptions = OrtSessionOptions()
        ..setInterOpNumThreads(2)
        ..setIntraOpNumThreads(2);
      
      // Create session
      _session = OrtSession.fromFile(modelFile, sessionOptions);
      
      // Initialize tokenizer
      _tokenizer = Phi3Tokenizer();
      
      _isLoaded = true;
      
      print('Phi-3 model loaded successfully');
    } catch (e) {
      print('Error loading Phi-3 model: $e');
      throw Exception('Failed to load Phi-3 model: $e');
    }
  }
  
  Future<void> _copyModelFromAssets(String targetPath) async {
    try {
      final byteData = await rootBundle.load(_modelAssetPath);
      final buffer = byteData.buffer;
      await File(targetPath).writeAsBytes(
        buffer.asUint8List(byteData.offsetInBytes, byteData.lengthInBytes),
      );
    } catch (e) {
      print('Error copying model from assets: $e');
      throw Exception('Failed to copy model from assets: $e');
    }
  }
  
  Future<String> generateText(String prompt, {int maxTokens = 100}) async {
    if (!_isLoaded || _session == null) {
      throw Exception('Model not loaded. Call loadModel() first.');
    }
    
    try {
      // Tokenize the prompt
      final inputIds = _tokenizer.encode(prompt, maxLength: 4096);
      final paddedInputIds = _tokenizer.padTokens(inputIds, maxTokens);
      
      // Convert to input tensor
      final inputTensor = OrtValueTensor.createTensorWithDataList(
        paddedInputIds,
        [1, paddedInputIds.length],
      );
      
      // Create attention mask
      final attentionMask = _tokenizer.createAttentionMask(paddedInputIds);
      final attentionTensor = OrtValueTensor.createTensorWithDataList(
        attentionMask,
        [1, attentionMask.length],
      );
      
      // Run inference
      final inputs = {
        'input_ids': inputTensor,
        'attention_mask': attentionTensor,
      };
      
      final outputs = await _session!.runAsync(
        OrtRunOptions(), 
        inputs,
      );
      
      // Process outputs
      final outputTensor = outputs?[0]?.value as List<List<double>>?;
      if (outputTensor == null) {
        throw Exception('No output from model');
      }
      
      // Process the logits to get token IDs
      final generatedTokens = _processLogits(outputTensor, maxTokens);
      
      // Decode output tokens
      final generatedText = _tokenizer.decode(generatedTokens);
      
      return generatedText;
    } catch (e) {
      print('Error generating text: $e');
      throw Exception('Failed to generate text: $e');
    }
  }
  
  // Process logits to get token IDs using greedy decoding
  List<int> _processLogits(List<List<double>> logits, int maxTokens) {
    final tokens = <int>[];
    
    for (final timestepLogits in logits) {
      // Find the token with highest probability (greedy decoding)
      double maxLogit = timestepLogits[0];
      int maxIndex = 0;
      
      for (int i = 1; i < timestepLogits.length; i++) {
        if (timestepLogits[i] > maxLogit) {
          maxLogit = timestepLogits[i];
          maxIndex = i;
        }
      }
      
      tokens.add(maxIndex);
      
      // Stop if we reach max tokens or end token
      if (tokens.length >= maxTokens || maxIndex == Phi3Tokenizer.endToken) {
        break;
      }
    }
    
    return tokens;
  }
  
  void dispose() {
    _session?.release();
    _session = null;
    _isLoaded = false;
  }
}