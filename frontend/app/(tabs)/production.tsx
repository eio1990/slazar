import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  RefreshControl,
  ActivityIndicator,
  Platform,
  ScrollView,
} from 'react-native';
import { useRouter } from 'expo-router';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useQuery } from '@tanstack/react-query';
import Toast from 'react-native-toast-message';

const API_URL = process.env.EXPO_PUBLIC_BACKEND_URL || 'http://85.238.112.232:8001';

console.log('[Production Screen] Using API URL:', API_URL);

interface Batch {
  id: number;
  batch_number: string;
  recipe_id: number;
  recipe_name: string;
  status: string;
  current_step: number;
  started_at: string;
  completed_at?: string;
  initial_weight: number;
  final_weight?: number;
}

export default function ProductionScreen() {
  const router = useRouter();
  const [selectedFilters, setSelectedFilters] = useState<string[]>([]);
  
  // Toggle filter selection
  const toggleFilter = (filterKey: string) => {
    setSelectedFilters(prev => {
      if (prev.includes(filterKey)) {
        return prev.filter(f => f !== filterKey);
      } else {
        return [...prev, filterKey];
      }
    });
  };

  const { data: allBatches, isLoading, error, refetch } = useQuery({
    queryKey: ['batches'],
    queryFn: async () => {
      try {
        const url = `${API_URL}/api/production/batches`;
        console.log('[Production] Fetching from:', url);
        const response = await fetch(url);
        console.log('[Production] Response status:', response.status);
        if (!response.ok) {
          const errorText = await response.text();
          console.error('[Production] Error response:', errorText);
          Toast.show({
            type: 'error',
            text1: 'Помилка завантаження',
            text2: `Не вдалося завантажити партії: ${response.status}`,
            position: 'bottom',
          });
          throw new Error(`Failed to fetch batches: ${response.status}`);
        }
        const data = await response.json();
        console.log('[Production] Fetched batches:', data.length);
        return data;
      } catch (error) {
        console.error('[Production] Query error:', error);
        throw error;
      }
    },
    retry: 1,
    retryDelay: 1000,
  });

  // Filter batches based on selected filters
  const batches = allBatches?.filter((batch: Batch) => {
    // If no filters selected, show all
    if (selectedFilters.length === 0) return true;
    // If filters selected, show only matching ones
    return selectedFilters.includes(batch.status);
  }) || [];

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'created': return '#2196F3';
      case 'in_progress': return '#FF9800';
      case 'completed': return '#4CAF50';
      default: return '#666';
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'created': return 'Створена';
      case 'in_progress': return 'В процесі';
      case 'completed': return 'Завершена';
      default: return status;
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('uk-UA', { 
      day: '2-digit', 
      month: '2-digit', 
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const filters = [
    { key: 'created', label: 'Нові' },
    { key: 'in_progress', label: 'В процесі' },
    { key: 'completed', label: 'Завершені' },
  ];

  const renderBatch = ({ item }: { item: Batch }) => (
    <TouchableOpacity
      style={styles.batchCard}
      onPress={() => router.push(`/batches/${item.id}` as any)}
    >
      <View style={styles.batchHeader}>
        <View style={styles.batchNumberContainer}>
          <MaterialCommunityIcons name="barcode" size={20} color="#666" />
          <Text style={styles.batchNumber}>{item.batch_number}</Text>
        </View>
        <View style={[styles.statusBadge, { backgroundColor: getStatusColor(item.status) }]}>
          <Text style={styles.statusText}>{getStatusText(item.status)}</Text>
        </View>
      </View>
      
      <Text style={styles.recipeName}>{item.recipe_name}</Text>
      
      <View style={styles.batchDetails}>
        <View style={styles.detailRow}>
          <MaterialCommunityIcons name="weight-kilogram" size={16} color="#666" />
          <Text style={styles.detailText}>
            Початкова вага: {item.initial_weight.toFixed(2)} кг
          </Text>
        </View>
        
        {item.final_weight && (
          <View style={styles.detailRow}>
            <MaterialCommunityIcons name="check-circle" size={16} color="#4CAF50" />
            <Text style={styles.detailText}>
              Фінальна вага: {item.final_weight.toFixed(2)} кг
            </Text>
          </View>
        )}
        
        <View style={styles.detailRow}>
          <MaterialCommunityIcons name="clock-outline" size={16} color="#666" />
          <Text style={styles.detailText}>
            Початок: {formatDate(item.started_at)}
          </Text>
        </View>
        
        {item.completed_at && (
          <View style={styles.detailRow}>
            <MaterialCommunityIcons name="flag-checkered" size={16} color="#4CAF50" />
            <Text style={styles.detailText}>
              Завершено: {formatDate(item.completed_at)}
            </Text>
          </View>
        )}
      </View>
    </TouchableOpacity>
  );

  if (isLoading) {
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator size="large" color="#4CAF50" />
        <Text style={styles.loadingText}>Завантаження партій...</Text>
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.centerContainer}>
        <MaterialCommunityIcons name="alert-circle" size={48} color="#f44336" />
        <Text style={styles.errorText}>Помилка завантаження партій</Text>
        <TouchableOpacity style={styles.retryButton} onPress={() => refetch()}>
          <Text style={styles.retryButtonText}>Спробувати ще раз</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {/* Filter chips */}
      <ScrollView 
        horizontal 
        showsHorizontalScrollIndicator={false}
        style={styles.filterScroll}
        contentContainerStyle={styles.filterContainer}
      >
        {filters.map((f) => (
          <TouchableOpacity
            key={f.key}
            style={[styles.filterChip, selectedFilters.includes(f.key) && styles.filterChipActive]}
            onPress={() => toggleFilter(f.key)}
          >
            <Text style={[styles.filterChipText, selectedFilters.includes(f.key) && styles.filterChipTextActive]}>
              {f.label}
            </Text>
          </TouchableOpacity>
        ))}
      </ScrollView>

      <FlatList
        data={batches}
        renderItem={renderBatch}
        keyExtractor={(item) => item.id.toString()}
        contentContainerStyle={styles.listContent}
        refreshControl={
          <RefreshControl refreshing={isLoading} onRefresh={refetch} colors={['#4CAF50']} />
        }
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            <MaterialCommunityIcons name="factory" size={64} color="#ccc" />
            <Text style={styles.emptyText}>Немає партій</Text>
            <Text style={styles.emptySubtext}>
              Натисніть "Рецепти" щоб створити нову партію
            </Text>
          </View>
        }
      />

      {/* Floating Action Button */}
      <TouchableOpacity
        style={styles.fab}
        onPress={() => router.push('/recipes' as any)}
      >
        <MaterialCommunityIcons name="plus" size={28} color="#fff" />
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  centerContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 24,
  },
  loadingText: {
    marginTop: 16,
    fontSize: 16,
    color: '#666',
  },
  errorText: {
    marginTop: 16,
    fontSize: 16,
    color: '#f44336',
    textAlign: 'center',
  },
  retryButton: {
    marginTop: 16,
    paddingVertical: 12,
    paddingHorizontal: 24,
    backgroundColor: '#4CAF50',
    borderRadius: 8,
  },
  retryButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  filterScroll: {
    backgroundColor: '#fff',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  filterContainer: {
    flexDirection: 'row',
    paddingHorizontal: 12,
    gap: 8,
    alignItems: 'center',
  },
  filterChip: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    marginRight: 8,
    borderRadius: 20,
    backgroundColor: '#f0f0f0',
    borderWidth: 1,
    borderColor: '#e0e0e0',
  },
  filterChipActive: {
    backgroundColor: '#4CAF50',
    borderColor: '#4CAF50',
  },
  filterChipText: {
    fontSize: 13,
    fontWeight: '600',
    color: '#666',
  },
  filterChipTextActive: {
    color: '#fff',
  },
  listContent: {
    padding: 16,
  },
  batchCard: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
    ...Platform.select({
      ios: {
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.1,
        shadowRadius: 4,
      },
      android: {
        elevation: 3,
      },
      web: {
        boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
      },
    }),
  },
  batchHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  batchNumberContainer: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  batchNumber: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333',
    marginLeft: 8,
  },
  statusBadge: {
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 12,
  },
  statusText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#fff',
  },
  recipeName: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333',
    marginBottom: 12,
  },
  batchDetails: {
    gap: 8,
  },
  detailRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  detailText: {
    fontSize: 14,
    color: '#666',
    marginLeft: 8,
  },
  emptyContainer: {
    alignItems: 'center',
    paddingVertical: 48,
  },
  emptyText: {
    fontSize: 18,
    fontWeight: '600',
    color: '#999',
    marginTop: 16,
  },
  emptySubtext: {
    fontSize: 14,
    color: '#999',
    marginTop: 8,
    textAlign: 'center',
  },
  fab: {
    position: 'absolute',
    right: 24,
    bottom: 24,
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: '#4CAF50',
    justifyContent: 'center',
    alignItems: 'center',
    ...Platform.select({
      ios: {
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 4 },
        shadowOpacity: 0.3,
        shadowRadius: 8,
      },
      android: {
        elevation: 8,
      },
      web: {
        boxShadow: '0 4px 8px rgba(0,0,0,0.3)',
      },
    }),
  },
});