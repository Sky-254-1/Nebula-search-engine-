import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Clock, Trash2, Search, Calendar } from 'lucide-react';
import { useSearchStore } from '@/state';
import { SearchHistoryItem } from '@/types';

export const HistoryPage: React.FC = () => {
  const { searchHistory, fetchSearchHistory } = useSearchStore();
  const [filteredHistory, setFilteredHistory] = useState<SearchHistoryItem[]>([]);
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    fetchSearchHistory();
  }, [fetchSearchHistory]);

  useEffect(() => {
    if (searchQuery) {
      setFilteredHistory(
        searchHistory.filter(item =>
          item.query.toLowerCase().includes(searchQuery.toLowerCase())
        )
      );
    } else {
      setFilteredHistory(searchHistory);
    }
  }, [searchQuery, searchHistory]);

  const handleReuseQuery = (query: string) => {
    // Navigate to search page with query
    window.location.href = `/search?q=${encodeURIComponent(query)}`;
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
          Search History
        </h1>
        <p className="text-gray-600 dark:text-gray-300">
          View and manage your recent searches
        </p>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" size={20} />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search history..."
          className="w-full pl-12 pr-4 py-3 border border-gray-300 dark:border-gray-600 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent dark:bg-gray-800 dark:text-white"
        />
      </div>

      {/* History List */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
        {filteredHistory.length > 0 ? (
          <div className="divide-y divide-gray-200 dark:divide-gray-700">
            {filteredHistory.map((item, index) => (
              <motion.div
                key={item.id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.05 }}
                className="flex items-center justify-between p-4 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
              >
                <div className="flex items-center gap-4 flex-1">
                  <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
                    <Clock className="text-blue-600 dark:text-blue-400" size={20} />
                  </div>
                  <div className="flex-1">
                    <h3 className="font-medium text-gray-900 dark:text-white">
                      {item.query}
                    </h3>
                    <div className="flex items-center gap-3 text-sm text-gray-500 dark:text-gray-400 mt-1">
                      <span className="flex items-center gap-1">
                        <Search size={14} />
                        {item.backend}
                      </span>
                      <span>{item.result_count} results</span>
                      <span className="flex items-center gap-1">
                        <Calendar size={14} />
                        {new Date(item.created_at).toLocaleDateString()}
                      </span>
                    </div>
                  </div>
                </div>
                <button
                  onClick={() => handleReuseQuery(item.query)}
                  className="px-4 py-2 text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-lg transition-colors text-sm font-medium"
                >
                  Reuse
                </button>
              </motion.div>
            ))}
          </div>
        ) : (
          <div className="text-center py-12">
            <Clock className="mx-auto text-gray-400 mb-4" size={48} />
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
              No search history
            </h3>
            <p className="text-gray-600 dark:text-gray-300">
              Your recent searches will appear here
            </p>
          </div>
        )}
      </div>
    </div>
  );
};