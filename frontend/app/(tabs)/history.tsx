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
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [pendingOpsCount, setPendingOps] = useState(0);

  useEffect(() => {
    loadMovements();
    checkPendingOperations();
  }, []);

  const loadMovements = async (showLoader = true) => {
    try {
      if (showLoader) setLoading(true);
      const online = await checkNetworkConnectivity();
      
      if (online) {
        const [movementsData, nomenclature] = await Promise.all([
          apiService.getMovements({ limit: 100 }),
          apiService.getNomenclature(),
        ]);
        
        // Create a map of nomenclature names
        const nomenclatureMap = new Map(
          nomenclature.map(n => [n.id, n.name])
        );
        
        // Add nomenclature names to movements
        const movementsWithNames = movementsData.map(m => ({
          ...m,
          nomenclature_name: nomenclatureMap.get(m.nomenclature_id) || `ID: ${m.nomenclature_id}`,
        }));
        
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
    if (type.includes('inventory')) return 'clipboard-check';
    return 'swap-horizontal';
  };

  const getOperationColor = (type: string) => {
    if (type === 'receipt') return '#4CAF50';
    if (type === 'withdrawal') return '#FF5722';
    if (type.includes('inventory')) return '#2196F3';
    return '#666';
  };

  const getOperationLabel = (type: string) => {
    if (type === 'receipt') return 'Прихід';
    if (type === 'withdrawal') return 'Розхід';
    if (type === 'inventory_adjustment_receipt') return 'Інвентаризація +';
    if (type === 'inventory_adjustment_withdrawal') return 'Інвентаризація -';
    return type;
  };

  const renderMovement = ({ item }: { item: StockMovement }) => {
    const operationColor = getOperationColor(item.operation_type);
    
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
            <Text style={styles.operationType}>
              {getOperationLabel(item.operation_type)}
            </Text>
            <Text style={styles.dateText}>
              {format(new Date(item.operation_date), 'dd MMMM yyyy, HH:mm', { locale: uk })}
            </Text>
          </View>
        </View>

        <View style={styles.quantityRow}>
          <View style={styles.quantityItem}>
            <Text style={styles.quantityLabel}>Кількість</Text>
            <Text style={[styles.quantityValue, { color: operationColor }]}>
              {item.operation_type === 'withdrawal' ? '-' : '+'}
              {item.quantity}
            </Text>
          </View>
          <View style={styles.quantityItem}>
            <Text style={styles.quantityLabel}>Залишок після</Text>
            <Text style={styles.quantityValue}>{item.balance_after}</Text>
          </View>
        </View>

        {item.metadata && (
          <View style={styles.metadataContainer}>
            <Text style={styles.metadataText} numberOfLines={2}>
              {JSON.parse(item.metadata).notes || 'Додаткова інформація'}
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

      <FlatList
        data={movements}
        renderItem={renderMovement}
        keyExtractor={(item) => item.id.toString()}
        contentContainerStyle={styles.listContent}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} colors={['#4CAF50']} />
        }
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            <MaterialCommunityIcons name="history" size={64} color="#ccc" />
            <Text style={styles.emptyText}>Немає історії операцій</Text>
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
  },
  listContent: {
    padding: 16,
  },
  card: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  cardHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  iconContainer: {
    width: 48,
    height: 48,
    borderRadius: 24,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
  },
  cardContent: {
    flex: 1,
  },
  operationType: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
    marginBottom: 2,
  },
  dateText: {
    fontSize: 12,
    color: '#999',
  },
  quantityRow: {
    flexDirection: 'row',
    gap: 16,
    marginBottom: 8,
  },
  quantityItem: {
    flex: 1,
  },
  quantityLabel: {
    fontSize: 12,
    color: '#666',
    marginBottom: 4,
  },
  quantityValue: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
  },
  metadataContainer: {
    marginTop: 8,
    padding: 8,
    backgroundColor: '#f5f5f5',
    borderRadius: 8,
  },
  metadataText: {
    fontSize: 12,
    color: '#666',
  },
  emptyContainer: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 64,
  },
  emptyText: {
    marginTop: 16,
    fontSize: 16,
    color: '#999',
  },
});
