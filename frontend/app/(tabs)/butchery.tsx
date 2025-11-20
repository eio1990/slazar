import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  RefreshControl,
  ActivityIndicator,
} from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { useQuery } from '@tanstack/react-query';

const API_URL = process.env.EXPO_PUBLIC_BACKEND_URL || 'http://localhost:8001';

export default function ButcheryScreen() {
  const router = useRouter();
  const [filter, setFilter] = useState<string>('all');

  // Get butchery operations
  const { data: operations, isLoading, refetch } = useQuery({
    queryKey: ['butchery-operations', filter],
    queryFn: async () => {
      let url = `${API_URL}/api/butchery/operations`;
      if (filter !== 'all') {
        url += `?status=${filter}`;
      }
      const response = await fetch(url);
      if (!response.ok) throw new Error('Failed to fetch operations');
      return response.json();
    },
  });

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'in_progress': return '#FF9800';
      case 'completed': return '#4CAF50';
      default: return '#999';
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'in_progress': return 'В процесі';
      case 'completed': return 'Завершена';
      default: return status;
    }
  };

  const filters = [
    { key: 'all', label: 'Всі' },
    { key: 'in_progress', label: 'В процесі' },
    { key: 'completed', label: 'Завершені' },
  ];

  return (
    <View style={styles.container}>
      {/* Filters */}
      <View style={styles.filterContainer}>
        {filters.map((f) => (
          <TouchableOpacity
            key={f.key}
            style={[styles.filterButton, filter === f.key && styles.filterButtonActive]}
            onPress={() => setFilter(f.key)}
          >
            <Text style={[styles.filterButtonText, filter === f.key && styles.filterButtonTextActive]}>
              {f.label}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* Content */}
      <FlatList
        data={operations}
        renderItem={({ item }) => (
          <TouchableOpacity
            style={styles.operationCard}
            onPress={() => router.push(`/butchery/${item.id}` as any)}
          >
            <View style={styles.operationHeader}>
              <View style={styles.operationTitleRow}>
                <MaterialCommunityIcons name="knife" size={20} color="#4CAF50" />
                <Text style={styles.operationNumber}>{item.operation_number}</Text>
              </View>
              <View style={[styles.statusBadge, { backgroundColor: getStatusColor(item.status) }]}>
                <Text style={styles.statusText}>{getStatusText(item.status)}</Text>
              </View>
            </View>

            <Text style={styles.recipeName}>{item.recipe_name}</Text>
            
            <View style={styles.detailsContainer}>
              <View style={styles.detailRow}>
                <MaterialCommunityIcons name="arrow-right" size={16} color="#666" />
                <Text style={styles.detailText}>{item.source_name}</Text>
              </View>
              
              <View style={styles.detailRow}>
                <MaterialCommunityIcons name="weight-kilogram" size={16} color="#666" />
                <Text style={styles.detailText}>
                  Вага: {item.input_weight} кг
                </Text>
              </View>
              
              <View style={styles.detailRow}>
                <MaterialCommunityIcons name="clock-outline" size={16} color="#666" />
                <Text style={styles.detailText}>
                  {new Date(item.started_at).toLocaleDateString('uk-UA', {
                    day: '2-digit',
                    month: '2-digit',
                    year: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </Text>
              </View>
            </View>
          </TouchableOpacity>
        )}
        keyExtractor={(item) => item.id.toString()}
        contentContainerStyle={styles.listContent}
        refreshControl={
          <RefreshControl refreshing={isLoading} onRefresh={refetch} colors={['#4CAF50']} />
        }
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            <MaterialCommunityIcons name="knife" size={64} color="#ccc" />
            <Text style={styles.emptyText}>Немає операцій</Text>
            <Text style={styles.emptySubtext}>
              Натисніть "+" щоб створити нову операцію розділки
            </Text>
          </View>
        }
      />

      {/* Floating Action Button */}
      <TouchableOpacity
        style={styles.fab}
        onPress={() => router.push('/butchery/select-meat-type' as any)}
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
  filterContainer: {
    flexDirection: 'row',
    padding: 12,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  filterButton: {
    flex: 1,
    paddingVertical: 8,
    paddingHorizontal: 12,
    marginHorizontal: 4,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#e0e0e0',
    alignItems: 'center',
  },
  filterButtonActive: {
    backgroundColor: '#4CAF50',
    borderColor: '#4CAF50',
  },
  filterButtonText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#666',
  },
  filterButtonTextActive: {
    color: '#fff',
  },
  content: {
    flex: 1,
  },
  loadingContainer: {
    padding: 40,
    alignItems: 'center',
  },
  emptyContainer: {
    padding: 40,
    alignItems: 'center',
  },
  emptyText: {
    fontSize: 18,
    fontWeight: '600',
    color: '#666',
    marginTop: 16,
  },
  emptyHint: {
    fontSize: 14,
    color: '#999',
    marginTop: 8,
  },
  operationCard: {
    backgroundColor: '#fff',
    marginHorizontal: 16,
    marginTop: 16,
    padding: 16,
    borderRadius: 12,
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
  },
  operationHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  operationTitleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  operationNumber: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
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
  operationInfo: {
    marginBottom: 12,
  },
  recipeName: {
    fontSize: 15,
    fontWeight: '600',
    color: '#333',
    marginBottom: 6,
  },
  sourceRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  sourceName: {
    fontSize: 14,
    color: '#666',
  },
  weightRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  weightItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  weightLabel: {
    fontSize: 14,
    color: '#999',
  },
  weightValue: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
  },
  pendingBadge: {
    backgroundColor: '#FFF3CD',
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 12,
  },
  pendingText: {
    fontSize: 12,
    color: '#856404',
    fontWeight: '600',
  },
  operationFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: '#f0f0f0',
  },
  footerText: {
    fontSize: 12,
    color: '#999',
  },
});
