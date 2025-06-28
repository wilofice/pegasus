import 'dart:io';
import 'package:onnxruntime/onnxruntime.dart';
import 'phi3_tokenizer.dart';
import 'model_downloader.dart';

class Phi3ModelManager {
  OrtSession? _session;
  bool _isLoaded = false;
  String? _modelPath;
  late Phi3Tokenizer _tokenizer;
  final ModelDownloader _modelDownloader = ModelDownloader();
  
  bool get isLoaded => _isLoaded;
  
  Future<void> loadModel() async {
    if (_isLoaded) return;
    
    try {
      // Get model path from downloader
      _modelPath = await _modelDownloader.getModelPath();
      
      // Check if model exists
      final modelFile = File(_modelPath!);
      if (!await modelFile.exists()) {
        throw Exception('Model file not found. Please download the model first.');
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