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

export default function PackagingScreen() {
  const router = useRouter();
  const [filter, setFilter] = useState<string>('all');

  // Get packaging batches
  const { data: batches, isLoading, refetch } = useQuery({
    queryKey: ['packaging-batches', filter],
    queryFn: async () => {
      let url = `${API_URL}/api/packaging/batches`;
      if (filter !== 'all') {
        url += `?status=${filter}`;
      }
      const response = await fetch(url);
      if (!response.ok) throw new Error('Failed to fetch batches');
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
        <Text style={styles.headerTitle}>Фасування</Text>
        <TouchableOpacity
          style={styles.newButton}
          onPress={() => router.push('/packaging/new-batch' as any)}
        >
          <MaterialCommunityIcons name="plus" size={20} color="#fff" />
          <Text style={styles.newButtonText}>Нова партія</Text>
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
        ) : !batches || batches.length === 0 ? (
          <View style={styles.emptyContainer}>
            <MaterialCommunityIcons name="package-variant" size={60} color="#ccc" />
            <Text style={styles.emptyText}>Партій фасування немає</Text>
            <Text style={styles.emptyHint}>Створіть нову партію, щоб почати</Text>
          </View>
        ) : (
          batches.map((batch: any) => (
            <TouchableOpacity
              key={batch.id}
              style={styles.batchCard}
              onPress={() => router.push(`/packaging/${batch.id}` as any)}
            >
              <View style={styles.batchHeader}>
                <View style={styles.batchTitleRow}>
                  <MaterialCommunityIcons name="package-variant-closed" size={20} color="#007AFF" />
                  <Text style={styles.batchNumber}>{batch.batch_number}</Text>
                </View>
                <View style={[styles.statusBadge, { backgroundColor: getStatusColor(batch.status) }]}>
                  <Text style={styles.statusText}>{getStatusText(batch.status)}</Text>
                </View>
              </View>

              <View style={styles.batchInfo}>
                <Text style={styles.productName}>{batch.target_product_name || 'Продукт'}</Text>
                <Text style={styles.packagingType}>
                  {batch.packaging_type === 'vacuum' ? '🔷 Вакуум' : 
                   batch.packaging_type === 'skin' ? '📦 Скін' : '⚖️ Ваговий'}
                </Text>
              </View>

              <View style={styles.statsRow}>
                <View style={styles.stat}>
                  <Text style={styles.statLabel}>Заплановано</Text>
                  <Text style={styles.statValue}>{batch.planned_quantity || 0} шт</Text>
                </View>
                <View style={styles.stat}>
                  <Text style={styles.statLabel}>Фактично</Text>
                  <Text style={styles.statValue}>{batch.actual_packed_quantity || 0} шт</Text>
                </View>
                <View style={styles.stat}>
                  <Text style={styles.statLabel}>Відходи</Text>
                  <Text style={styles.statValue}>{(batch.waste_quantity || 0).toFixed(2)} кг</Text>
                </View>
              </View>

              {batch.status === 'in_progress' && (
                <View style={styles.progressBar}>
                  <View 
                    style={[
                      styles.progressFill, 
                      { 
                        width: `${Math.min(
                          100, 
                          (batch.actual_packed_quantity / (batch.planned_quantity || 1)) * 100
                        )}%` 
                      }
                    ]} 
                  />
                </View>
              )}

              <View style={styles.batchFooter}>
                <Text style={styles.footerText}>
                  {new Date(batch.started_at).toLocaleDateString('uk-UA', { 
                    day: '2-digit', 
                    month: '2-digit', 
                    year: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit'
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
  batchCard: {
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
  batchHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  batchTitleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  batchNumber: {
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
  batchInfo: {
    marginBottom: 12,
  },
  productName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
    marginBottom: 4,
  },
  packagingType: {
    fontSize: 14,
    color: '#666',
  },
  statsRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 12,
  },
  stat: {
    flex: 1,
  },
  statLabel: {
    fontSize: 12,
    color: '#999',
    marginBottom: 4,
  },
  statValue: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
  },
  progressBar: {
    height: 6,
    backgroundColor: '#e0e0e0',
    borderRadius: 3,
    marginBottom: 12,
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    backgroundColor: '#4CAF50',
    borderRadius: 3,
  },
  batchFooter: {
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
