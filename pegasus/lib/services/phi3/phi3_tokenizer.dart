
class Phi3Tokenizer {
  // Phi-3 uses a BPE tokenizer similar to GPT models
  // This is a simplified implementation - in production, you'd load the actual vocab
  
  static const int padToken = 0;
  static const int startToken = 1;
  static const int endToken = 2;
  static const int unkToken = 3;
  
  // Simplified vocab - in production, load from tokenizer.json
  final Map<String, int> _vocab = {
    '<pad>': padToken,
    '<s>': startToken,
    '</s>': endToken,
    '<unk>': unkToken,
    // Add more tokens as needed
  };
  
  final Map<int, String> _reverseVocab = {};
  
  Phi3Tokenizer() {
    // Build reverse vocab
    _vocab.forEach((key, value) {
      _reverseVocab[value] = key;
    });
    
    // Initialize basic word tokens
    _initializeBasicVocab();
  }
  
  void _initializeBasicVocab() {
    // Add common words and subwords
    final commonWords = [
      'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'I',
      'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at',
      'this', 'but', 'his', 'by', 'from', 'they', 'we', 'say', 'her', 'she',
      'or', 'an', 'will', 'my', 'one', 'all', 'would', 'there', 'their',
      'what', 'so', 'up', 'out', 'if', 'about', 'who', 'get', 'which', 'go',
      'me', 'when', 'make', 'can', 'like', 'time', 'no', 'just', 'him', 'know',
      'take', 'people', 'into', 'year', 'your', 'good', 'some', 'could', 'them',
      'see', 'other', 'than', 'then', 'now', 'look', 'only', 'come', 'its', 'over',
      'think', 'also', 'back', 'after', 'use', 'two', 'how', 'our', 'work',
      'first', 'well', 'way', 'even', 'new', 'want', 'because', 'any', 'these',
      'give', 'day', 'most', 'us', 'is', 'was', 'are', 'been', 'has', 'had',
      'were', 'said', 'did', 'getting', 'made', 'find', 'where', 'much', 'too',
      'very', 'still', 'being', 'going', 'why', 'before', 'never', 'here', 'more',
      ' ', '.', ',', '!', '?', "'", '"', '-', ':', ';', '(', ')', '[', ']',
    ];
    
    int tokenId = 4; // Start after special tokens
    for (final word in commonWords) {
      if (!_vocab.containsKey(word)) {
        _vocab[word] = tokenId;
        _reverseVocab[tokenId] = word;
        tokenId++;
      }
    }
    
    // Add subword tokens for common prefixes/suffixes
    final subwords = ['##ing', '##ed', '##s', '##er', '##est', '##ly', '##tion', '##ment'];
    for (final subword in subwords) {
      _vocab[subword] = tokenId;
      _reverseVocab[tokenId] = subword;
      tokenId++;
    }
    
    // Add character tokens for OOV handling
    for (int i = 0; i < 256; i++) {
      final char = String.fromCharCode(i);
      if (!_vocab.containsKey(char)) {
        _vocab[char] = tokenId;
        _reverseVocab[tokenId] = char;
        tokenId++;
      }
    }
  }
  
  List<int> encode(String text, {int? maxLength}) {
    final tokens = <int>[];
    
    // Add start token
    tokens.add(startToken);
    
    // Simple word-level tokenization with subword fallback
    final words = text.toLowerCase().split(RegExp(r'(\s+|[.!?,;:()\[\]"])'));
    
    for (final word in words) {
      if (word.isEmpty) continue;
      
      if (_vocab.containsKey(word)) {
        tokens.add(_vocab[word]!);
      } else {
        // Try to break into subwords
        final subwordTokens = _tokenizeSubwords(word);
        tokens.addAll(subwordTokens);
      }
    }
    
    // Add end token
    tokens.add(endToken);
    
    // Truncate if needed
    if (maxLength != null && tokens.length > maxLength) {
      tokens.removeRange(maxLength - 1, tokens.length);
      tokens.add(endToken);
    }
    
    return tokens;
  }
  
  List<int> _tokenizeSubwords(String word) {
    final tokens = <int>[];
    
    // Try common subword patterns
    if (word.endsWith('ing') && word.length > 3) {
      final stem = word.substring(0, word.length - 3);
      if (_vocab.containsKey(stem)) {
        tokens.add(_vocab[stem]!);
        tokens.add(_vocab['##ing']!);
        return tokens;
      }
    }
    
    if (word.endsWith('ed') && word.length > 2) {
      final stem = word.substring(0, word.length - 2);
      if (_vocab.containsKey(stem)) {
        tokens.add(_vocab[stem]!);
        tokens.add(_vocab['##ed']!);
        return tokens;
      }
    }
    
    // Fall back to character-level tokenization
    for (final char in word.split('')) {
      if (_vocab.containsKey(char)) {
        tokens.add(_vocab[char]!);
      } else {
        tokens.add(unkToken);
      }
    }
    
    return tokens;
  }
  
  String decode(List<int> tokens) {
    final words = <String>[];
    
    for (final token in tokens) {
      if (token == padToken || token == startToken || token == endToken) {
        continue;
      }
      
      if (_reverseVocab.containsKey(token)) {
        String word = _reverseVocab[token]!;
        
        // Handle subword tokens
        if (word.startsWith('##')) {
          if (words.isNotEmpty) {
            words[words.length - 1] += word.substring(2);
          } else {
            words.add(word.substring(2));
          }
        } else {
          words.add(word);
        }
      } else {
        words.add('<unk>');
      }
    }
    
    return words.join('');
  }
  
  List<int> createAttentionMask(List<int> tokens) {
    return tokens.map((token) => token != padToken ? 1 : 0).toList();
  }
  
  List<int> padTokens(List<int> tokens, int maxLength) {
    if (tokens.length >= maxLength) {
      return tokens.sublist(0, maxLength);
    }
    
    final padded = List<int>.from(tokens);
    while (padded.length < maxLength) {
      padded.add(padToken);
    }
    
    return padded;
  }
}