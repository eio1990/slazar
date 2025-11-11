import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TextInput,
  TouchableOpacity,
  RefreshControl,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { apiService, checkNetworkConnectivity, getOfflineQueue } from '../../services/api';
import { useStore } from '../../stores/useStore';
import NetInfo from '@react-native-community/netinfo';

export default function BalancesScreen() {
  const { balances, setBalances, setIsOnline, setPendingOperationsCount } = useStore();
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [isOnline, setOnlineState] = useState(true);

  // Categories from nomenclature
  const categories = Array.from(new Set(balances.map(b => b.category))).sort();

  // Filter balances
  const filteredBalances = balances.filter(balance => {
    const matchesSearch = balance.nomenclature_name.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory = !selectedCategory || balance.category === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  // Load balances
  const loadBalances = async (showLoader = true) => {
    try {
      if (showLoader) setLoading(true);
      const online = await checkNetworkConnectivity();
      setOnlineState(online);
      setIsOnline(online);

      if (online) {
        const data = await apiService.getBalances(selectedCategory || undefined);
        setBalances(data);
      }
    } catch (error) {
      console.error('Error loading balances:', error);
      Alert.alert('Помилка', 'Не вдалося завантажити залишки');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  // Check offline queue
  const checkOfflineQueue = async () => {
    const queue = await getOfflineQueue();
    setPendingOperationsCount(queue.length);
  };

  useEffect(() => {
    loadBalances();

    // Listen to network changes
    const unsubscribe = NetInfo.addEventListener(state => {
      const online = state.isConnected === true && state.isInternetReachable === true;
      setOnlineState(online);
      setIsOnline(online);
    });

    return () => unsubscribe();
  }, [selectedCategory]);

  useFocusEffect(
    useCallback(() => {
      loadBalances(false);
      checkOfflineQueue();
    }, [])
  );

  const onRefresh = () => {
    setRefreshing(true);
    loadBalances(false);
  };

  const renderBalanceItem = ({ item }: { item: typeof balances[0] }) => (
    <View style={styles.card}>
      <View style={styles.cardHeader}>
        <Text style={styles.itemName} numberOfLines={2}>
          {item.nomenclature_name}
        </Text>
        <View style={styles.quantityBadge}>
          <Text style={styles.quantityText}>
            {item.quantity} {item.unit}
          </Text>
        </View>
      </View>
      <View style={styles.cardFooter}>
        <Text style={styles.categoryText}>{item.category}</Text>
        <Text style={styles.lastUpdated}>
          {new Date(item.last_updated).toLocaleDateString('uk-UA', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
          })}
        </Text>
      </View>
    </View>
  );

  const renderCategoryFilter = () => (
    <View style={styles.filterContainer}>
      <FlatList
        horizontal
        showsHorizontalScrollIndicator={false}
        data={[null, ...categories]}
        keyExtractor={(item) => item || 'all'}
        renderItem={({ item }) => (
          <TouchableOpacity
            style={[
              styles.categoryChip,
              selectedCategory === item && styles.categoryChipActive,
            ]}
            onPress={() => setSelectedCategory(item)}
          >
            <Text
              style={[
                styles.categoryChipText,
                selectedCategory === item && styles.categoryChipTextActive,
              ]}
            >
              {item || 'Всі'}
            </Text>
          </TouchableOpacity>
        )}
      />
    </View>
  );

  if (loading) {
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator size="large" color="#4CAF50" />
        <Text style={styles.loadingText}>Завантаження залишків...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {/* Network status */}
      {!isOnline && (
        <View style={styles.offlineBanner}>
          <MaterialCommunityIcons name="wifi-off" size={20} color="#fff" />
          <Text style={styles.offlineText}>Офлайн режим</Text>
        </View>
      )}

      {/* Search bar */}
      <View style={styles.searchContainer}>
        <MaterialCommunityIcons name="magnify" size={24} color="#666" style={styles.searchIcon} />
        <TextInput
          style={styles.searchInput}
          placeholder="Пошук номенклатури..."
          value={searchQuery}
          onChangeText={setSearchQuery}
        />
        {searchQuery.length > 0 && (
          <TouchableOpacity onPress={() => setSearchQuery('')}>
            <MaterialCommunityIcons name="close-circle" size={20} color="#999" />
          </TouchableOpacity>
        )}
      </View>

      {/* Category filters */}
      {renderCategoryFilter()}

      {/* Balances list */}
      <FlatList
        data={filteredBalances}
        renderItem={renderBalanceItem}
        keyExtractor={(item) => item.nomenclature_id.toString()}
        contentContainerStyle={styles.listContent}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} colors={['#4CAF50']} />
        }
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            <MaterialCommunityIcons name="package-variant" size={64} color="#ccc" />
            <Text style={styles.emptyText}>Немає залишків</Text>
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
  offlineBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#FF9800',
    padding: 8,
    gap: 8,
  },
  offlineText: {
    color: '#fff',
    fontWeight: '600',
    fontSize: 14,
  },
  searchContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fff',
    margin: 16,
    marginBottom: 8,
    paddingHorizontal: 12,
    borderRadius: 12,
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  searchIcon: {
    marginRight: 8,
  },
  searchInput: {
    flex: 1,
    paddingVertical: 12,
    fontSize: 16,
  },
  filterContainer: {
    paddingHorizontal: 16,
    marginBottom: 8,
  },
  categoryChip: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    marginRight: 8,
    borderRadius: 20,
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: '#e0e0e0',
  },
  categoryChipActive: {
    backgroundColor: '#4CAF50',
    borderColor: '#4CAF50',
  },
  categoryChipText: {
    fontSize: 14,
    fontWeight: '500',
    color: '#666',
  },
  categoryChipTextActive: {
    color: '#fff',
  },
  listContent: {
    padding: 16,
    paddingTop: 8,
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
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 8,
  },
  itemName: {
    flex: 1,
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
    marginRight: 8,
  },
  quantityBadge: {
    backgroundColor: '#E8F5E9',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
  },
  quantityText: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#4CAF50',
  },
  cardFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  categoryText: {
    fontSize: 12,
    color: '#999',
  },
  lastUpdated: {
    fontSize: 12,
    color: '#999',
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
