import React, { useState, useEffect } from 'react';
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
  Platform,
  ScrollView,
} from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { apiService, checkNetworkConnectivity } from '../../services/api';
import NetInfo from '@react-native-community/netinfo';

const API_URL = process.env.EXPO_PUBLIC_BACKEND_URL || 'http://localhost:8001';

export default function StockScreen() {
  const router = useRouter();
  const [balances, setBalances] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategories, setSelectedCategories] = useState<string[]>([]);
  const [selectedMeatType, setSelectedMeatType] = useState<string | null>(null);
  const [isOnline, setOnlineState] = useState(true);
  const [usageStats, setUsageStats] = useState<Record<number, number>>({});

  // Define filter categories with priority order
  const filterCategories = ['Сировина - М\'ясо', 'Спеції'];
  
  // Get all unique categories
  const allCategories = Array.from(new Set(balances.map(b => b.category))).sort();
  
  // Toggle category filter
  const toggleCategoryFilter = (category: string) => {
    setSelectedCategories(prev => {
      if (prev.includes(category)) {
        return prev.filter(c => c !== category);
      } else {
        return [...prev, category];
      }
    });
    setSelectedRecipe(null); // Clear recipe filter when category changes
  };

  // Define meat types for filtering
  const meatTypes = [
    { key: 'яловичина', label: 'Яловичина' },
    { key: 'конина', label: 'Конина' },
    { key: 'індичка', label: 'Індичка' },
    { key: 'свинина', label: 'Свинина' },
  ];

  // Load data
  const loadData = async () => {
    try {
      const online = await checkNetworkConnectivity();
      setOnlineState(online);

      if (online) {
        // Load balances and usage stats
        const [balancesData, statsData] = await Promise.all([
          apiService.getBalances(),
          fetch(`${API_URL}/api/nomenclature/usage-stats`)
            .then(res => res.json())
            .catch(() => ({}))
        ]);
        setBalances(balancesData);
        setUsageStats(statsData);
      }
    } catch (error) {
      console.error('Error loading data:', error);
      Alert.alert('Помилка', 'Не вдалося завантажити дані');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  // Load recipe nomenclatures when recipe is selected
  const loadRecipeNomenclatures = async (recipeId: number) => {
    try {
      const response = await fetch(`${API_URL}/api/production/recipes/${recipeId}/materials`);
      const data = await response.json();
      
      const nomenclatureIds: number[] = [];
      
      // Add ingredients
      data.ingredients?.forEach((ing: any) => {
        nomenclatureIds.push(ing.nomenclature_id);
      });
      
      // Add spices
      data.spices?.forEach((spice: any) => {
        nomenclatureIds.push(spice.nomenclature_id);
      });
      
      setRecipeNomenclatureIds(nomenclatureIds);
    } catch (error) {
      console.error('Error loading recipe materials:', error);
    }
  };

  useEffect(() => {
    loadData();

    const unsubscribe = NetInfo.addEventListener(state => {
      const online = state.isConnected === true && state.isInternetReachable === true;
      setOnlineState(online);
    });

    return () => unsubscribe();
  }, []);

  useEffect(() => {
    if (selectedRecipe) {
      loadRecipeNomenclatures(selectedRecipe);
    } else {
      setRecipeNomenclatureIds([]);
    }
  }, [selectedRecipe]);

  const onRefresh = () => {
    setRefreshing(true);
    loadData();
  };

  // Filter and sort balances
  const filteredBalances = balances
    .filter(balance => {
      const matchesSearch = balance.nomenclature_name.toLowerCase().includes(searchQuery.toLowerCase());
      
      // Category filter: if no categories selected, show all
      const matchesCategory = selectedCategories.length === 0 || selectedCategories.includes(balance.category);
      
      // Recipe filter
      const matchesRecipe = !selectedRecipe || recipeNomenclatureIds.includes(balance.nomenclature_id);
      
      return matchesSearch && matchesCategory && matchesRecipe;
    })
    .sort((a, b) => {
      // Sort by usage frequency
      const aUsage = usageStats[a.nomenclature_id] || 0;
      const bUsage = usageStats[b.nomenclature_id] || 0;
      
      if (aUsage !== bUsage) {
        return bUsage - aUsage; // Higher usage first
      }
      
      // Then by category priority
      const aPriority = filterCategories.includes(a.category);
      const bPriority = filterCategories.includes(b.category);
      
      if (aPriority && !bPriority) return -1;
      if (!aPriority && bPriority) return 1;
      
      // Alphabetical
      return a.nomenclature_name.localeCompare(b.nomenclature_name, 'uk');
    });

  const renderBalanceItem = ({ item }: { item: any }) => {
    const isLowStock = item.quantity === 0;
    
    return (
      <View style={[styles.card, isLowStock && styles.cardLowStock]}>
        <View style={styles.cardHeader}>
          <Text style={styles.itemName} numberOfLines={2}>
            {item.nomenclature_name}
          </Text>
          <View style={[styles.quantityBadge, isLowStock && styles.quantityBadgeLow]}>
            <Text style={[styles.quantityText, isLowStock && styles.quantityTextLow]}>
              {item.quantity} {item.unit}
            </Text>
          </View>
        </View>
        <View style={styles.cardFooter}>
          <View style={styles.categoryBadge}>
            <MaterialCommunityIcons name="tag" size={14} color="#666" />
            <Text style={styles.categoryText}>{item.category}</Text>
          </View>
          <Text style={styles.lastUpdated}>
            {new Date(item.last_updated).toLocaleDateString('uk-UA', {
              day: '2-digit',
              month: '2-digit',
            })}
          </Text>
        </View>
      </View>
    );
  };

  if (loading) {
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator size="large" color="#4CAF50" />
        <Text style={styles.loadingText}>Завантаження...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity style={styles.backButton} onPress={() => router.back()}>
          <MaterialCommunityIcons name="arrow-left" size={24} color="#fff" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Залишки</Text>
        <View style={styles.placeholder} />
      </View>

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
      <View style={styles.categoryFilterRow}>
        {/* Priority filters - fixed */}
        {filterCategories.map((category) => (
          <TouchableOpacity
            key={category}
            style={[
              styles.categoryButton,
              selectedCategories.includes(category) && styles.categoryButtonActive
            ]}
            onPress={() => toggleCategoryFilter(category)}
          >
            <Text style={[
              styles.categoryButtonText,
              selectedCategories.includes(category) && styles.categoryButtonTextActive
            ]}>
              {category === 'Сировина - М\'ясо' ? 'М\'ясо' : category}
            </Text>
          </TouchableOpacity>
        ))}
        
        {/* Other filters - scrollable */}
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          style={styles.scrollableFilters}
          contentContainerStyle={styles.scrollableFiltersContent}
        >
          {allCategories
            .filter(c => !filterCategories.includes(c))
            .map((category) => (
              <TouchableOpacity
                key={category}
                style={[
                  styles.categoryChip,
                  selectedCategories.includes(category) && styles.categoryChipActive
                ]}
                onPress={() => toggleCategoryFilter(category)}
              >
                <Text style={[
                  styles.categoryChipText,
                  selectedCategories.includes(category) && styles.categoryChipTextActive
                ]}>
                  {category}
                </Text>
              </TouchableOpacity>
            ))}
        </ScrollView>
      </View>

      {/* Recipe filters */}
      <View style={styles.filterSection}>
        <Text style={styles.filterLabel}>Рецепти:</Text>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.filterScroll}>
          <TouchableOpacity
            style={[styles.filterChip, !selectedRecipe && styles.filterChipActive]}
            onPress={() => setSelectedRecipe(null)}
          >
            <Text style={[styles.filterChipText, !selectedRecipe && styles.filterChipTextActive]}>
              Всі
            </Text>
          </TouchableOpacity>
          {recipes.map((recipe) => (
            <TouchableOpacity
              key={recipe.id}
              style={[styles.filterChip, selectedRecipe === recipe.id && styles.filterChipActive]}
              onPress={() => {
                setSelectedRecipe(recipe.id);
                setSelectedCategories([]);
              }}
            >
              <Text style={[styles.filterChipText, selectedRecipe === recipe.id && styles.filterChipTextActive]}>
                {recipe.name}
              </Text>
            </TouchableOpacity>
          ))}
        </ScrollView>
      </View>

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
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 12,
    backgroundColor: '#4CAF50',
    ...Platform.select({
      android: {
        paddingTop: 40,
      },
    }),
  },
  backButton: {
    padding: 8,
  },
  headerTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#fff',
  },
  placeholder: {
    width: 40,
  },
  offlineBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    backgroundColor: '#FF9800',
    paddingVertical: 8,
  },
  offlineText: {
    color: '#fff',
    fontWeight: '600',
    fontSize: 14,
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
  searchContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fff',
    marginHorizontal: 16,
    marginVertical: 12,
    paddingHorizontal: 12,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#e0e0e0',
  },
  searchIcon: {
    marginRight: 8,
  },
  searchInput: {
    flex: 1,
    paddingVertical: 12,
    fontSize: 16,
  },
  categoryFilterRow: {
    flexDirection: 'row',
    padding: 12,
    backgroundColor: '#fff',
    gap: 8,
    alignItems: 'center',
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  categoryButton: {
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#e0e0e0',
    alignItems: 'center',
    minWidth: 80,
  },
  categoryButtonActive: {
    backgroundColor: '#4CAF50',
    borderColor: '#4CAF50',
  },
  categoryButtonText: {
    fontSize: 13,
    fontWeight: '600',
    color: '#666',
  },
  categoryButtonTextActive: {
    color: '#fff',
  },
  scrollableFilters: {
    flex: 1,
    maxHeight: 44,
  },
  scrollableFiltersContent: {
    paddingLeft: 8,
    alignItems: 'center',
    gap: 8,
  },
  categoryChip: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    marginRight: 8,
    borderRadius: 20,
    backgroundColor: '#f0f0f0',
    borderWidth: 1,
    borderColor: '#e0e0e0',
  },
  categoryChipActive: {
    backgroundColor: '#4CAF50',
    borderColor: '#4CAF50',
  },
  categoryChipText: {
    fontSize: 13,
    fontWeight: '600',
    color: '#666',
  },
  categoryChipTextActive: {
    color: '#fff',
  },
  filterSection: {
    paddingVertical: 12,
    paddingHorizontal: 16,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  filterLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
    marginBottom: 8,
  },
  filterScroll: {
    flexGrow: 0,
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
  cardLowStock: {
    borderLeftWidth: 4,
    borderLeftColor: '#FF5722',
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  itemName: {
    flex: 1,
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
    marginRight: 12,
  },
  quantityBadge: {
    backgroundColor: '#4CAF50',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 12,
  },
  quantityBadgeLow: {
    backgroundColor: '#FF5722',
  },
  quantityText: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#fff',
  },
  quantityTextLow: {
    color: '#fff',
  },
  cardFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  categoryBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  categoryText: {
    fontSize: 12,
    color: '#666',
  },
  lastUpdated: {
    fontSize: 12,
    color: '#999',
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
});
