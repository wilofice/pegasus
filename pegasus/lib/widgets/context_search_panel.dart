// Context Search Panel for In-Chat Discovery
// 
// This widget provides inline context search capabilities within the chat interface,
// allowing users to search through their documents and audio without leaving the conversation.
// Features include:
// - Multiple search strategies (vector, graph, hybrid, ensemble)
// - Real-time search suggestions
// - Source preview with relevance scoring
// - Integration with chat context

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/context_search_models.dart';
import '../models/api_enums.dart';
import '../providers/chat_v2_provider.dart';
import 'confidence_indicator.dart';

class ContextSearchPanel extends ConsumerStatefulWidget {
  final Function(ContextSearchResult)? onResultSelected;
  final Function(String)? onQuerySubmitted;
  final bool showInline;
  final String? initialQuery;

  const ContextSearchPanel({
    super.key,
    this.onResultSelected,
    this.onQuerySubmitted,
    this.showInline = false,
    this.initialQuery,
  });

  @override
  ConsumerState<ContextSearchPanel> createState() => _ContextSearchPanelState();
}

class _ContextSearchPanelState extends ConsumerState<ContextSearchPanel>
    with SingleTickerProviderStateMixin {
  final TextEditingController _searchController = TextEditingController();
  final FocusNode _searchFocusNode = FocusNode();
  
  late TabController _tabController;
  bool _isSearching = false;
  List<ContextSearchResult> _searchResults = [];
  String? _errorMessage;
  SearchStrategy _selectedStrategy = SearchStrategy.ensemble;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 4, vsync: this);
    
    if (widget.initialQuery != null) {
      _searchController.text = widget.initialQuery!;
      WidgetsBinding.instance.addPostFrameCallback((_) {
        _performSearch();
      });
    }
  }

  @override
  void dispose() {
    _searchController.dispose();
    _searchFocusNode.dispose();
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (widget.showInline) {
      return _buildInlineSearch();
    } else {
      return _buildExpandedSearch();
    }
  }

  Widget _buildInlineSearch() {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.blue.shade50,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.blue.shade200),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.search, size: 18, color: Colors.blue.shade600),
              const SizedBox(width: 8),
              Text(
                'Search your documents',
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w500,
                  color: Colors.blue.shade700,
                ),
              ),
              const Spacer(),
              TextButton(
                onPressed: _showExpandedSearch,
                child: const Text('Expand', style: TextStyle(fontSize: 12)),
              ),
            ],
          ),
          const SizedBox(height: 8),
          _buildSearchBar(),
          if (_searchResults.isNotEmpty) ...[ 
            const SizedBox(height: 8),
            _buildCompactResults(),
          ],
        ],
      ),
    );
  }

  Widget _buildExpandedSearch() {
    return Container(
      height: MediaQuery.of(context).size.height * 0.7,
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      child: Column(
        children: [
          _buildSearchHeader(),
          _buildSearchBar(),
          _buildStrategyTabs(),
          Expanded(child: _buildSearchContent()),
        ],
      ),
    );
  }

  Widget _buildSearchHeader() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        border: Border(bottom: BorderSide(color: Colors.grey.shade200)),
      ),
      child: Row(
        children: [
          Icon(Icons.search, color: Theme.of(context).primaryColor),
          const SizedBox(width: 12),
          const Text(
            'Context Search',
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.w600),
          ),
          const Spacer(),
          IconButton(
            icon: const Icon(Icons.close),
            onPressed: () => Navigator.of(context).pop(),
          ),
        ],
      ),
    );
  }

  Widget _buildSearchBar() {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: TextField(
        controller: _searchController,
        focusNode: _searchFocusNode,
        decoration: InputDecoration(
          hintText: 'Search your documents and audio...',
          prefixIcon: const Icon(Icons.search),
          suffixIcon: _isSearching 
              ? const SizedBox(
                  width: 20,
                  height: 20,
                  child: Padding(
                    padding: EdgeInsets.all(12),
                    child: CircularProgressIndicator(strokeWidth: 2),
                  ),
                )
              : IconButton(
                  icon: const Icon(Icons.send),
                  onPressed: _performSearch,
                ),
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide: BorderSide(color: Colors.grey.shade300),
          ),
          enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide: BorderSide(color: Colors.grey.shade300),
          ),
          focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide: BorderSide(color: Theme.of(context).primaryColor),
          ),
        ),
        onSubmitted: (_) => _performSearch(),
        textInputAction: TextInputAction.search,
      ),
    );
  }

  Widget _buildStrategyTabs() {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 16),
      child: TabBar(
        controller: _tabController,
        isScrollable: true,
        labelColor: Theme.of(context).primaryColor,
        unselectedLabelColor: Colors.grey.shade600,
        indicatorSize: TabBarIndicatorSize.tab,
        tabs: const [
          Tab(text: 'Smart Search'),
          Tab(text: 'Vector'),
          Tab(text: 'Graph'),
          Tab(text: 'Hybrid'),
        ],
        onTap: (index) {
          setState(() {
            _selectedStrategy = [
              SearchStrategy.ensemble,
              SearchStrategy.vector,
              SearchStrategy.graph,
              SearchStrategy.hybrid,
            ][index];
          });
          if (_searchController.text.isNotEmpty) {
            _performSearch();
          }
        },
      ),
    );
  }

  Widget _buildSearchContent() {
    if (_errorMessage != null) {
      return _buildErrorState();
    } else if (_searchResults.isEmpty && !_isSearching) {
      return _buildEmptyState();
    } else if (_isSearching) {
      return _buildLoadingState();
    } else {
      return _buildResultsList();
    }
  }

  Widget _buildCompactResults() {
    return Container(
      height: 120,
      child: ListView.builder(
        scrollDirection: Axis.horizontal,
        itemCount: _searchResults.take(3).length,
        itemBuilder: (context, index) {
          final result = _searchResults[index];
          return Container(
            width: 250,
            margin: const EdgeInsets.only(right: 8),
            child: Card(
              child: ListTile(
                title: Text(result.summary, maxLines: 2, overflow: TextOverflow.ellipsis),
                subtitle: Text('${result.sources.length} sources'),
                onTap: () => _selectResult(result),
              ),
            ),
          );
        },
      ),
    );
  }

  Widget _buildResultsList() {
    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: _searchResults.length,
      itemBuilder: (context, index) {
        final result = _searchResults[index];
        return _buildResultCard(result);
      },
    );
  }

  Widget _buildResultCard(ContextSearchResult result) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: InkWell(
        onTap: () => _selectResult(result),
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: _getStrategyColor(result.searchStrategy).withOpacity(0.1),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Text(
                      result.searchStrategy.value.toUpperCase(),
                      style: TextStyle(
                        fontSize: 10,
                        fontWeight: FontWeight.w600,
                        color: _getStrategyColor(result.searchStrategy),
                      ),
                    ),
                  ),
                  const Spacer(),
                  ConfidenceBadge(confidence: result.overallConfidence),
                ],
              ),
              const SizedBox(height: 12),
              Text(
                result.summary,
                style: const TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w500,
                  height: 1.3,
                ),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  Icon(
                    Icons.source,
                    size: 14,
                    color: Colors.grey.shade600,
                  ),
                  const SizedBox(width: 4),
                  Text(
                    '${result.sources.length} source${result.sources.length != 1 ? 's' : ''}',
                    style: TextStyle(
                      fontSize: 12,
                      color: Colors.grey.shade600,
                    ),
                  ),
                  const SizedBox(width: 16),
                  Icon(
                    Icons.timer,
                    size: 14,
                    color: Colors.grey.shade600,
                  ),
                  const SizedBox(width: 4),
                  Text(
                    '${result.processingTimeMs.round()}ms',
                    style: TextStyle(
                      fontSize: 12,
                      color: Colors.grey.shade600,
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.search,
            size: 64,
            color: Colors.grey.shade400,
          ),
          const SizedBox(height: 16),
          Text(
            'Search your documents',
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.w500,
              color: Colors.grey.shade600,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'Find relevant information from your\nuploaded documents and audio',
            textAlign: TextAlign.center,
            style: TextStyle(
              fontSize: 14,
              color: Colors.grey.shade500,
            ),
          ),
          const SizedBox(height: 24),
          Wrap(
            spacing: 8,
            children: [
              'meeting notes',
              'project updates',
              'research findings',
            ].map((suggestion) =>
              ActionChip(
                label: Text(suggestion),
                onPressed: () {
                  _searchController.text = suggestion;
                  _performSearch();
                },
              ),
            ).toList(),
          ),
        ],
      ),
    );
  }

  Widget _buildLoadingState() {
    return const Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          CircularProgressIndicator(),
          SizedBox(height: 16),
          Text('Searching your documents...'),
        ],
      ),
    );
  }

  Widget _buildErrorState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            Icons.error_outline,
            size: 64,
            color: Colors.red.shade400,
          ),
          const SizedBox(height: 16),
          Text(
            'Search failed',
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.w500,
              color: Colors.red.shade600,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            _errorMessage!,
            textAlign: TextAlign.center,
            style: TextStyle(
              fontSize: 14,
              color: Colors.grey.shade600,
            ),
          ),
          const SizedBox(height: 24),
          ElevatedButton(
            onPressed: _performSearch,
            child: const Text('Try Again'),
          ),
        ],
      ),
    );
  }

  Future<void> _performSearch() async {
    final query = _searchController.text.trim();
    if (query.isEmpty) return;

    setState(() {
      _isSearching = true;
      _errorMessage = null;
    });

    try {
      final apiClient = ref.read(apiClientV2Provider);
      final request = ContextSearchRequest(
        query: query,
        strategy: _selectedStrategy,
        maxResults: 10,
        includeAudio: true,
        includeDocuments: true,
      );

      final results = await apiClient.searchContext(request);
      
      setState(() {
        _searchResults = results;
        _isSearching = false;
      });

      widget.onQuerySubmitted?.call(query);
    } catch (e) {
      setState(() {
        _errorMessage = 'Failed to search: ${e.toString()}';
        _isSearching = false;
      });
    }
  }

  void _selectResult(ContextSearchResult result) {
    widget.onResultSelected?.call(result);
    
    if (!widget.showInline) {
      Navigator.of(context).pop(result);
    }
  }

  void _showExpandedSearch() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => ContextSearchPanel(
        onResultSelected: widget.onResultSelected,
        onQuerySubmitted: widget.onQuerySubmitted,
        initialQuery: _searchController.text,
      ),
    );
  }

  Color _getStrategyColor(SearchStrategy strategy) {
    switch (strategy) {
      case SearchStrategy.vector:
        return Colors.blue;
      case SearchStrategy.graph:
        return Colors.green;
      case SearchStrategy.hybrid:
        return Colors.purple;
      case SearchStrategy.ensemble:
        return Colors.orange;
    }
  }
}

/// Quick search widget for chat input area
class QuickContextSearch extends ConsumerWidget {
  final Function(String)? onQuerySelected;

  const QuickContextSearch({
    super.key,
    this.onQuerySelected,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Container(
      height: 40,
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
      child: Row(
        children: [
          Expanded(
            child: GestureDetector(
              onTap: () => _showContextSearch(context),
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 12),
                decoration: BoxDecoration(
                  color: Colors.grey.shade100,
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(color: Colors.grey.shade300),
                ),
                child: Row(
                  children: [
                    Icon(
                      Icons.search,
                      size: 18,
                      color: Colors.grey.shade600,
                    ),
                    const SizedBox(width: 8),
                    Text(
                      'Search documents...',
                      style: TextStyle(
                        color: Colors.grey.shade600,
                        fontSize: 14,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
          const SizedBox(width: 8),
          IconButton(
            icon: const Icon(Icons.auto_awesome, size: 20),
            onPressed: () => _showSmartSuggestions(context),
            tooltip: 'Smart suggestions',
          ),
        ],
      ),
    );
  }

  void _showContextSearch(BuildContext context) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => ContextSearchPanel(
        onResultSelected: (result) => onQuerySelected?.call(result.summary),
      ),
    );
  }

  void _showSmartSuggestions(BuildContext context) {
    // Show AI-generated search suggestions based on recent conversation
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Smart suggestions coming soon!'),
        duration: Duration(seconds: 2),
      ),
    );
  }
}