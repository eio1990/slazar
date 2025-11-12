import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  Platform,
  Alert,
} from 'react-native';
import { useRouter } from 'expo-router';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useQuery } from '@tanstack/react-query';
import Constants from 'expo-constants';
const API_URL = Constants.expoConfig?.extra?.EXPO_PUBLIC_BACKEND_URL || 'http://localhost:8001';

export default function AnalyticsScreen() {
  const router = useRouter();
  const [dateFilter, setDateFilter] = useState<'all' | 'today' | 'week' | 'month'>('all');

  const getDateRange = () => {
    const now = new Date();
    let start = null;
    
    switch (dateFilter) {
      case 'today':
        start = new Date(now.getFullYear(), now.getMonth(), now.getDate());
        break;
      case 'week':
        start = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
        break;
      case 'month':
        start = new Date(now.getFullYear(), now.getMonth(), 1);
        break;
    }
    
    return start ? start.toISOString() : null;
  };

  const { data: analytics, isLoading, refetch } = useQuery({
    queryKey: ['analytics', dateFilter],
    queryFn: async () => {
      const startDate = getDateRange();
      const url = startDate 
        ? `${API_URL}/api/production/batches/analytics?start_date=${startDate}`
        : `${API_URL}/api/production/batches/analytics`;
      
      const response = await fetch(url);
      if (!response.ok) throw new Error('Failed to fetch analytics');
      return response.json();
    },
  });

  const handleExport = async () => {
    try {
      const startDate = getDateRange();
      const url = startDate 
        ? `${API_URL}/api/production/batches/export?start_date=${startDate}&format=json`
        : `${API_URL}/api/production/batches/export?format=json`;
      
      const response = await fetch(url);
      if (!response.ok) throw new Error('Failed to export');
      
      const data = await response.json();
      
      // Convert to CSV
      if (data.length === 0) {
        Alert.alert('Немає даних', 'Немає партій для експорту');
        return;
      }
      
      const headers = Object.keys(data[0]).join(',') + '\n';
      const rows = data.map((row: any) => 
        Object.values(row).map(val => `"${val}"`).join(',')
      ).join('\n');
      
      const csv = headers + rows;
      const filename = `batches_${new Date().toISOString().split('T')[0]}.csv`;
      const fileUri = FileSystem.documentDirectory + filename;
      
      await FileSystem.writeAsStringAsync(fileUri, csv, {
        encoding: FileSystem.EncodingType.UTF8,
      });
      
      if (await Sharing.isAvailableAsync()) {
        await Sharing.shareAsync(fileUri);
      } else {
        Alert.alert('Успіх', `Файл збережено: ${filename}`);
      }
    } catch (error) {
      Alert.alert('Помилка', 'Не вдалося експортувати дані');
    }
  };

  if (isLoading) {
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator size="large" color="#4CAF50" />
      </View>
    );
  }

  const summary = analytics?.summary || {};
  const byRecipe = analytics?.by_recipe || [];

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity style={styles.backButton} onPress={() => router.back()}>
          <MaterialCommunityIcons name="arrow-left" size={24} color="#fff" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Аналітика</Text>
        <TouchableOpacity style={styles.exportButton} onPress={handleExport}>
          <MaterialCommunityIcons name="download" size={24} color="#fff" />
        </TouchableOpacity>
      </View>

      <ScrollView style={styles.content}>
        {/* Date Filter */}
        <View style={styles.filterContainer}>
          <TouchableOpacity
            style={[styles.filterButton, dateFilter === 'all' && styles.filterButtonActive]}
            onPress={() => setDateFilter('all')}
          >
            <Text style={[styles.filterText, dateFilter === 'all' && styles.filterTextActive]}>
              Всі
            </Text>
          </TouchableOpacity>
          
          <TouchableOpacity
            style={[styles.filterButton, dateFilter === 'today' && styles.filterButtonActive]}
            onPress={() => setDateFilter('today')}
          >
            <Text style={[styles.filterText, dateFilter === 'today' && styles.filterTextActive]}>
              Сьогодні
            </Text>
          </TouchableOpacity>
          
          <TouchableOpacity
            style={[styles.filterButton, dateFilter === 'week' && styles.filterButtonActive]}
            onPress={() => setDateFilter('week')}
          >
            <Text style={[styles.filterText, dateFilter === 'week' && styles.filterTextActive]}>
              Тиждень
            </Text>
          </TouchableOpacity>
          
          <TouchableOpacity
            style={[styles.filterButton, dateFilter === 'month' && styles.filterButtonActive]}
            onPress={() => setDateFilter('month')}
          >
            <Text style={[styles.filterText, dateFilter === 'month' && styles.filterTextActive]}>
              Місяць
            </Text>
          </TouchableOpacity>
        </View>

        {/* Summary Cards */}
        <View style={styles.summaryGrid}>
          <View style={[styles.summaryCard, { backgroundColor: '#E3F2FD' }]}>
            <MaterialCommunityIcons name="package-variant" size={32} color="#2196F3" />
            <Text style={styles.summaryValue}>{summary.total_batches || 0}</Text>
            <Text style={styles.summaryLabel}>Всього партій</Text>
          </View>
          
          <View style={[styles.summaryCard, { backgroundColor: '#E8F5E9' }]}>
            <MaterialCommunityIcons name="check-circle" size={32} color="#4CAF50" />
            <Text style={styles.summaryValue}>{summary.completed_batches || 0}</Text>
            <Text style={styles.summaryLabel}>Завершено</Text>
          </View>
          
          <View style={[styles.summaryCard, { backgroundColor: '#FFF3E0' }]}>
            <MaterialCommunityIcons name="clock-outline" size={32} color="#FF9800" />
            <Text style={styles.summaryValue}>{summary.in_progress_batches || 0}</Text>
            <Text style={styles.summaryLabel}>В процесі</Text>
          </View>
          
          <View style={[styles.summaryCard, { backgroundColor: '#F3E5F5' }]}>
            <MaterialCommunityIcons name="chart-line" size={32} color="#9C27B0" />
            <Text style={styles.summaryValue}>
              {summary.avg_yield_percent ? `${summary.avg_yield_percent.toFixed(1)}%` : '-'}
            </Text>
            <Text style={styles.summaryLabel}>Середній вихід</Text>
          </View>
        </View>

        {/* Production Volume */}
        <View style={styles.volumeCard}>
          <Text style={styles.volumeTitle}>Обсяги виробництва</Text>
          <View style={styles.volumeRow}>
            <View style={styles.volumeItem}>
              <Text style={styles.volumeLabel}>Сировина:</Text>
              <Text style={styles.volumeValue}>
                {summary.total_input_weight?.toFixed(2) || 0} кг
              </Text>
            </View>
            <MaterialCommunityIcons name="arrow-right" size={24} color="#666" />
            <View style={styles.volumeItem}>
              <Text style={styles.volumeLabel}>Продукція:</Text>
              <Text style={[styles.volumeValue, { color: '#4CAF50' }]}>
                {summary.total_output_weight?.toFixed(2) || 0} кг
              </Text>
            </View>
          </View>
        </View>

        {/* By Recipe */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>По рецептах</Text>
          
          {byRecipe.map((recipe: any) => (
            <View key={recipe.recipe_id} style={styles.recipeCard}>
              <View style={styles.recipeHeader}>
                <MaterialCommunityIcons name="book-open-variant" size={24} color="#4CAF50" />
                <View style={styles.recipeInfo}>
                  <Text style={styles.recipeName}>{recipe.recipe_name}</Text>
                  <Text style={styles.recipeStats}>
                    {recipe.completed_count} з {recipe.batch_count} партій завершено
                  </Text>
                </View>
              </View>
              
              <View style={styles.recipeMetrics}>
                <View style={styles.metric}>
                  <Text style={styles.metricLabel}>Сировина</Text>
                  <Text style={styles.metricValue}>
                    {recipe.total_input_weight.toFixed(0)} кг
                  </Text>
                </View>
                
                <View style={styles.metric}>
                  <Text style={styles.metricLabel}>Продукція</Text>
                  <Text style={styles.metricValue}>
                    {recipe.total_output_weight.toFixed(0)} кг
                  </Text>
                </View>
                
                <View style={styles.metric}>
                  <Text style={styles.metricLabel}>Вихід</Text>
                  <Text style={[
                    styles.metricValue,
                    {
                      color: recipe.avg_yield >= recipe.expected_yield_min && 
                             recipe.avg_yield <= recipe.expected_yield_max 
                        ? '#4CAF50' 
                        : '#FF9800'
                    }
                  ]}>
                    {recipe.avg_yield.toFixed(1)}%
                  </Text>
                </View>
                
                <View style={styles.metric}>
                  <Text style={styles.metricLabel}>Очікується</Text>
                  <Text style={styles.metricValue}>
                    {recipe.expected_yield_min}-{recipe.expected_yield_max}%
                  </Text>
                </View>
              </View>
            </View>
          ))}
          
          {byRecipe.length === 0 && (
            <View style={styles.emptyContainer}>
              <MaterialCommunityIcons name="chart-box-outline" size={64} color="#ccc" />
              <Text style={styles.emptyText}>Немає даних за обраний період</Text>
            </View>
          )}
        </View>
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
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: '#4CAF50',
    paddingTop: Platform.OS === 'ios' ? 50 : 20,
    paddingBottom: 16,
    paddingHorizontal: 16,
  },
  backButton: {
    padding: 4,
  },
  headerTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#fff',
  },
  exportButton: {
    padding: 4,
  },
  centerContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  content: {
    flex: 1,
  },
  filterContainer: {
    flexDirection: 'row',
    padding: 16,
    gap: 8,
  },
  filterButton: {
    flex: 1,
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#e0e0e0',
    backgroundColor: '#fff',
    alignItems: 'center',
  },
  filterButtonActive: {
    backgroundColor: '#4CAF50',
    borderColor: '#4CAF50',
  },
  filterText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#666',
  },
  filterTextActive: {
    color: '#fff',
  },
  summaryGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    paddingHorizontal: 16,
    gap: 12,
  },
  summaryCard: {
    width: '48%',
    padding: 16,
    borderRadius: 12,
    alignItems: 'center',
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
  summaryValue: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#333',
    marginTop: 8,
  },
  summaryLabel: {
    fontSize: 12,
    color: '#666',
    marginTop: 4,
    textAlign: 'center',
  },
  volumeCard: {
    backgroundColor: '#fff',
    margin: 16,
    padding: 16,
    borderRadius: 12,
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
  volumeTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 12,
  },
  volumeRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  volumeItem: {
    flex: 1,
  },
  volumeLabel: {
    fontSize: 12,
    color: '#666',
    marginBottom: 4,
  },
  volumeValue: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#333',
  },
  section: {
    marginHorizontal: 16,
    marginBottom: 24,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 12,
  },
  recipeCard: {
    backgroundColor: '#fff',
    padding: 16,
    borderRadius: 12,
    marginBottom: 12,
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
  recipeHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  recipeInfo: {
    marginLeft: 12,
    flex: 1,
  },
  recipeName: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333',
  },
  recipeStats: {
    fontSize: 12,
    color: '#666',
    marginTop: 2,
  },
  recipeMetrics: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: '#f0f0f0',
  },
  metric: {
    alignItems: 'center',
  },
  metricLabel: {
    fontSize: 11,
    color: '#999',
    marginBottom: 4,
  },
  metricValue: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#333',
  },
  emptyContainer: {
    alignItems: 'center',
    paddingVertical: 48,
  },
  emptyText: {
    fontSize: 16,
    color: '#999',
    marginTop: 16,
  },
});
