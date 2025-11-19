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
      {/* Header */}
      <View style={styles.header}>
        <View>
          <Text style={styles.headerTitle}>Розділка</Text>
          <Text style={styles.headerSubtitle}>Первинна обробка сировини</Text>
        </View>
        <TouchableOpacity
          style={styles.newButton}
          onPress={() => router.push('/butchery/select-recipe' as any)}
        >
          <MaterialCommunityIcons name="plus" size={20} color="#fff" />
          <Text style={styles.newButtonText}>Нова</Text>
        </TouchableOpacity>
      </View>

      {/* Filters */}
      <View style={styles.filters}>
        {filters.map((f) => (
          <TouchableOpacity
            key={f.key}
            style={[styles.filterButton, filter === f.key && styles.filterButtonActive]}
            onPress={() => setFilter(f.key)}
          >
            <Text style={[styles.filterText, filter === f.key && styles.filterTextActive]}>
              {f.label}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* Content */}
      <ScrollView
        style={styles.content}
        refreshControl={<RefreshControl refreshing={isLoading} onRefresh={refetch} />}
      >
        {isLoading ? (
          <View style={styles.loadingContainer}>
            <ActivityIndicator size="large" color="#007AFF" />
          </View>
        ) : !operations || operations.length === 0 ? (
          <View style={styles.emptyContainer}>
            <MaterialCommunityIcons name="knife" size={60} color="#ccc" />
            <Text style={styles.emptyText}>Операцій розділки немає</Text>
            <Text style={styles.emptyHint}>Почніть нову розділку</Text>
          </View>
        ) : (
          operations.map((operation: any) => (
            <TouchableOpacity
              key={operation.id}
              style={styles.operationCard}
              onPress={() => router.push(`/butchery/${operation.id}` as any)}
            >
              <View style={styles.operationHeader}>
                <View style={styles.operationTitleRow}>
                  <MaterialCommunityIcons name="knife" size={20} color="#007AFF" />
                  <Text style={styles.operationNumber}>{operation.operation_number}</Text>
                </View>
                <View style={[styles.statusBadge, { backgroundColor: getStatusColor(operation.status) }]}>
                  <Text style={styles.statusText}>{getStatusText(operation.status)}</Text>
                </View>
              </View>

              <View style={styles.operationInfo}>
                <Text style={styles.recipeName}>{operation.recipe_name}</Text>
                <View style={styles.sourceRow}>
                  <MaterialCommunityIcons name="arrow-right" size={16} color="#666" />
                  <Text style={styles.sourceName}>{operation.source_name}</Text>
                </View>
              </View>

              <View style={styles.weightRow}>
                <View style={styles.weightItem}>
                  <Text style={styles.weightLabel}>Вхід:</Text>
                  <Text style={styles.weightValue}>{operation.input_weight} кг</Text>
                </View>
                {operation.status === 'in_progress' && (
                  <View style={styles.pendingBadge}>
                    <Text style={styles.pendingText}>Очікує завершення</Text>
                  </View>
                )}
              </View>

              <View style={styles.operationFooter}>
                <Text style={styles.footerText}>
                  {new Date(operation.started_at).toLocaleDateString('uk-UA', {
                    day: '2-digit',
                    month: '2-digit',
                    year: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </Text>
                <MaterialCommunityIcons name="chevron-right" size={20} color="#999" />
              </View>
            </TouchableOpacity>
          ))
        )}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  headerTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#333',
  },
  headerSubtitle: {
    fontSize: 12,
    color: '#999',
    marginTop: 2,
  },
  newButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#007AFF',
    paddingVertical: 8,
    paddingHorizontal: 16,
    borderRadius: 8,
    gap: 6,
  },
  newButtonText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: '600',
  },
  filters: {
    flexDirection: 'row',
    padding: 16,
    gap: 8,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  filterButton: {
    paddingVertical: 8,
    paddingHorizontal: 16,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: '#ddd',
    backgroundColor: '#fff',
  },
  filterButtonActive: {
    backgroundColor: '#007AFF',
    borderColor: '#007AFF',
  },
  filterText: {
    fontSize: 14,
    color: '#666',
  },
  filterTextActive: {
    color: '#fff',
    fontWeight: '600',
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
