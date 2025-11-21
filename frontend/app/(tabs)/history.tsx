import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  ActivityIndicator,
  RefreshControl,
  TouchableOpacity,
  Alert,
  Platform,
} from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { apiService, StockMovement, checkNetworkConnectivity, getOfflineQueue, clearOfflineQueue } from '../../services/api';
import { format } from 'date-fns';
import { uk } from 'date-fns/locale';
import { useStore } from '../../stores/useStore';

interface MovementWithName extends StockMovement {
  nomenclature_name?: string;
}

export default function HistoryScreen() {
  const { isOnline, isSyncing, setIsSyncing, setPendingOperationsCount } = useStore();
  const [movements, setMovements] = useState<MovementWithName[]>([]);
  const [filteredMovements, setFilteredMovements] = useState<MovementWithName[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [pendingOpsCount, setPendingOps] = useState(0);
  const [operationTypeFilter, setOperationTypeFilter] = useState<string>('all');

  useEffect(() => {
    loadMovements();
    checkPendingOperations();
  }, []);

  useEffect(() => {
    // Filter movements based on selected operation type
    if (operationTypeFilter === 'all') {
      setFilteredMovements(movements);
    } else {
      setFilteredMovements(
        movements.filter(m => m.operation_type === operationTypeFilter)
      );
    }
  }, [operationTypeFilter, movements]);

  const loadMovements = async (showLoader = true) => {
    try {
      if (showLoader) setLoading(true);
      const online = await checkNetworkConnectivity();
      
      if (online) {
        const [movementsData, nomenclature] = await Promise.all([
          // Увеличиваем лимит для загрузки старых записей
          apiService.getMovements({ limit: 500 }),
          apiService.getNomenclature(),
        ]);
        
        // Create a map of nomenclature names
        const nomenclatureMap = new Map(
          nomenclature.map(n => [n.id, n.name])
        );
        
        // Add nomenclature names to movements
        const movementsWithNames = movementsData.map(m => {
          const name = nomenclatureMap.get(m.nomenclature_id);
          return {
            ...m,
            nomenclature_name: name || `Номенклатура #${m.nomenclature_id}`,
          };
        });
        
        setMovements(movementsWithNames);
      }
    } catch (error) {
      console.error('Error loading movements:', error);
      Alert.alert('Помилка', 'Не вдалося завантажити історію');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const checkPendingOperations = async () => {
    const queue = await getOfflineQueue();
    setPendingOps(queue.length);
    setPendingOperationsCount(queue.length);
  };

  const syncPendingOperations = async () => {
    const queue = await getOfflineQueue();
    if (queue.length === 0) {
      Alert.alert('Інформація', 'Немає операцій для синхронізації');
      return;
    }

    const online = await checkNetworkConnectivity();
    if (!online) {
      Alert.alert('Помилка', 'Відсутнє підключення до інтернету');
      return;
    }

    Alert.alert(
      'Синхронізація',
      `Синхронізувати ${queue.length} операцій?`,
      [
        { text: 'Скасувати', style: 'cancel' },
        {
          text: 'Синхронізувати',
          onPress: async () => {
            try {
              setIsSyncing(true);
              const result = await apiService.syncOperations(queue);
              
              const successCount = result.results.filter((r: any) => r.status === 'success').length;
              const errorCount = result.results.filter((r: any) => r.status === 'error').length;

              if (errorCount === 0) {
                clearOfflineQueue();
                checkPendingOperations();
                Alert.alert('Успіх', `Всі ${successCount} операцій синхронізовано`);
                loadMovements(false);
              } else {
                Alert.alert(
                  'Часткова синхронізація',
                  `Успішно: ${successCount}, Помилок: ${errorCount}`
                );
              }
            } catch (error: any) {
              console.error('Sync error:', error);
              Alert.alert('Помилка', 'Не вдалося синхронізувати операції');
            } finally {
              setIsSyncing(false);
            }
          },
        },
      ]
    );
  };

  const onRefresh = () => {
    setRefreshing(true);
    loadMovements(false);
    checkPendingOperations();
  };

  const getOperationIcon = (type: string) => {
    if (type === 'receipt') return 'arrow-down-bold';
    if (type === 'withdrawal') return 'arrow-up-bold';
    if (type.includes('production')) return 'factory';
    if (type.includes('inventory')) return 'clipboard-check';
    return 'swap-horizontal';
  };

  const getOperationColor = (type: string) => {
    if (type === 'receipt') return '#4CAF50';
    if (type === 'withdrawal') return '#FF5722';
    if (type.includes('production')) return '#2196F3';
    if (type.includes('inventory')) return '#FF9800';
    return '#666';
  };

  const getOperationLabel = (type: string) => {
    if (type === 'receipt') return 'Прихід';
    if (type === 'withdrawal') return 'Розхід';
    if (type === 'production_withdrawal') return 'Виробництво';
    if (type === 'butchery_withdrawal') return 'Розділка';
    if (type === 'inventory_adjustment_receipt') return 'Інвентаризація +';
    if (type === 'inventory_adjustment_withdrawal') return 'Інвентаризація -';
    return type;
  };

  const filters = [
    { key: 'all', label: 'Всі', icon: 'format-list-bulleted' },
    { key: 'receipt', label: 'Прихід', icon: 'arrow-down-bold' },
    { key: 'withdrawal', label: 'Розхід', icon: 'arrow-up-bold' },
    { key: 'production_withdrawal', label: 'Виробництво', icon: 'factory' },
  ];

  const renderMovement = ({ item }: { item: MovementWithName }) => {
    const operationColor = getOperationColor(item.operation_type);
    const operationLabel = getOperationLabel(item.operation_type);
    const sign = item.operation_type === 'withdrawal' || item.operation_type.includes('withdrawal') ? '-' : '+';
    
    return (
      <View style={styles.card}>
        <View style={styles.cardHeader}>
          <View style={[styles.iconContainer, { backgroundColor: operationColor + '20' }]}>
            <MaterialCommunityIcons
              name={getOperationIcon(item.operation_type)}
              size={24}
              color={operationColor}
            />
          </View>
          <View style={styles.cardContent}>
            <Text style={styles.operationType}>{operationLabel}</Text>
            <Text style={styles.nomenclatureName}>{item.nomenclature_name}</Text>
            <Text style={styles.dateText}>
              {format(new Date(item.operation_date), 'dd MMM yyyy, HH:mm', { locale: uk })}
            </Text>
          </View>
          <View style={styles.quantityContainer}>
            <Text style={[styles.quantityValue, { color: operationColor }]}>
              {sign}{item.quantity}
            </Text>
            <Text style={styles.balanceAfter}>Залишок: {item.balance_after}</Text>
          </View>
        </View>

        {item.metadata && (
          <View style={styles.metadataContainer}>
            <MaterialCommunityIcons name="information-outline" size={16} color="#666" />
            <Text style={styles.metadataText} numberOfLines={2}>
              {typeof item.metadata === 'string' ? JSON.parse(item.metadata).notes || 'Додаткова інформація' : item.metadata.notes || 'Додаткова інформація'}
            </Text>
          </View>
        )}
      </View>
    );
  };

  if (loading) {
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator size="large" color="#4CAF50" />
        <Text style={styles.loadingText}>Завантаження історії...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {pendingOpsCount > 0 && (
        <View style={styles.syncBanner}>
          <View style={styles.syncBannerContent}>
            <MaterialCommunityIcons name="cloud-upload" size={24} color="#fff" />
            <Text style={styles.syncBannerText}>
              {pendingOpsCount} операцій очікують синхронізації
            </Text>
          </View>
          <TouchableOpacity
            style={styles.syncButton}
            onPress={syncPendingOperations}
            disabled={isSyncing}
          >
            {isSyncing ? (
              <ActivityIndicator size="small" color="#fff" />
            ) : (
              <Text style={styles.syncButtonText}>Синхронізувати</Text>
            )}
          </TouchableOpacity>
        </View>
      )}

      {/* Filters */}
      <View style={styles.filterContainer}>
        {filters.map((f) => (
          <TouchableOpacity
            key={f.key}
            style={[
              styles.filterButton,
              operationTypeFilter === f.key && styles.filterButtonActive,
            ]}
            onPress={() => setOperationTypeFilter(f.key)}
          >
            <MaterialCommunityIcons
              name={f.icon as any}
              size={18}
              color={operationTypeFilter === f.key ? '#fff' : '#666'}
            />
            <Text
              style={[
                styles.filterButtonText,
                operationTypeFilter === f.key && styles.filterButtonTextActive,
              ]}
            >
              {f.label}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      <FlatList
        data={filteredMovements}
        renderItem={renderMovement}
        keyExtractor={(item) => item.id.toString()}
        contentContainerStyle={styles.listContent}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} colors={['#4CAF50']} />
        }
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            <MaterialCommunityIcons name="history" size={64} color="#ccc" />
            <Text style={styles.emptyText}>Немає операцій</Text>
            <Text style={styles.emptySubtext}>
              {operationTypeFilter !== 'all' 
                ? 'Змініть фільтр для перегляду інших операцій'
                : 'Історія операцій з\'явиться тут'}
            </Text>
          </View>
        }
      />
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
    backgroundColor: '#f5f5f5',
  },
  loadingText: {
    marginTop: 16,
    fontSize: 16,
    color: '#666',
  },
  syncBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: '#FF9800',
    padding: 16,
  },
  syncBannerContent: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    flex: 1,
  },
  syncBannerText: {
    color: '#fff',
    fontWeight: '600',
    fontSize: 14,
    flex: 1,
  },
  syncButton: {
    backgroundColor: 'rgba(255,255,255,0.3)',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 8,
  },
  syncButtonText: {
    color: '#fff',
    fontWeight: '600',
    fontSize: 14,
  },
  filterContainer: {
    flexDirection: 'row',
    padding: 12,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
    gap: 8,
  },
  filterButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 4,
    paddingVertical: 8,
    paddingHorizontal: 8,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#e0e0e0',
  },
  filterButtonActive: {
    backgroundColor: '#4CAF50',
    borderColor: '#4CAF50',
  },
  filterButtonText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#666',
  },
  filterButtonTextActive: {
    color: '#fff',
  },
  listContent: {
    padding: 16,
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
  card: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
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
  cardHeader: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 12,
  },
  iconContainer: {
    width: 48,
    height: 48,
    borderRadius: 24,
    justifyContent: 'center',
    alignItems: 'center',
  },
  cardContent: {
    flex: 1,
  },
  operationType: {
    fontSize: 12,
    fontWeight: '600',
    color: '#666',
    marginBottom: 4,
  },
  nomenclatureName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
    marginBottom: 4,
  },
  dateText: {
    fontSize: 12,
    color: '#999',
  },
  quantityContainer: {
    alignItems: 'flex-end',
  },
  quantityValue: {
    fontSize: 20,
    fontWeight: 'bold',
    marginBottom: 4,
  },
  balanceAfter: {
    fontSize: 12,
    color: '#666',
  },
  metadataContainer: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 8,
    marginTop: 12,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: '#f0f0f0',
  },
  metadataText: {
    flex: 1,
    fontSize: 13,
    color: '#666',
    lineHeight: 18,
  },
});
