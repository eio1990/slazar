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
  const [recipes, setRecipes] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [selectedRecipe, setSelectedRecipe] = useState<number | null>(null);
  const [recipeNomenclatureIds, setRecipeNomenclatureIds] = useState<number[]>([]);
  const [isOnline, setOnlineState] = useState(true);

  const categories = Array.from(new Set(balances.map(b => b.category))).sort();

  // Load data
  const loadData = async () => {
    try {
      const online = await checkNetworkConnectivity();
      setOnlineState(online);

      if (online) {
        // Load balances
        const balancesData = await apiService.getBalances();
        setBalances(balancesData);

        // Load recipes
        const recipesResponse = await fetch(`${API_URL}/api/production/recipes`);
        const recipesData = await recipesResponse.json();
        setRecipes(recipesData);
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

  // Filter balances
  const filteredBalances = balances.filter(balance => {
    const matchesSearch = balance.nomenclature_name.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory = !selectedCategory || balance.category === selectedCategory;
    const matchesRecipe = !selectedRecipe || recipeNomenclatureIds.includes(balance.nomenclature_id);
    return matchesSearch && matchesCategory && matchesRecipe;
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
      <View style={styles.filterSection}>
        <Text style={styles.filterLabel}>Категорії:</Text>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.filterScroll}>
          <TouchableOpacity
            style={[styles.filterChip, !selectedCategory && styles.filterChipActive]}
            onPress={() => {
              setSelectedCategory(null);
              setSelectedRecipe(null);
            }}
          >
            <Text style={[styles.filterChipText, !selectedCategory && styles.filterChipTextActive]}>
              Всі
            </Text>
          </TouchableOpacity>
          {categories.map((cat) => (
            <TouchableOpacity
              key={cat}
              style={[styles.filterChip, selectedCategory === cat && styles.filterChipActive]}
              onPress={() => {
                setSelectedCategory(cat);
                setSelectedRecipe(null);
              }}
            >
              <Text style={[styles.filterChipText, selectedCategory === cat && styles.filterChipTextActive]}>
                {cat}
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
                setSelectedCategory(null);
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
  placeholder: {
    width: 32,
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
    marginBottom: 12,
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
  filterSection: {
    paddingHorizontal: 16,
    marginBottom: 12,
  },
  filterLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#666',
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
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: '#e0e0e0',
  },
  filterChipActive: {
    backgroundColor: '#4CAF50',
    borderColor: '#4CAF50',
  },
  filterChipText: {
    fontSize: 14,
    fontWeight: '500',
    color: '#666',
  },
  filterChipTextActive: {
    color: '#fff',
  },
  listContent: {
    padding: 16,
    paddingTop: 0,
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
  cardLowStock: {
    borderLeftWidth: 4,
    borderLeftColor: '#FF5722',
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
  quantityBadgeLow: {
    backgroundColor: '#FFEBEE',
  },
  quantityText: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#4CAF50',
  },
  quantityTextLow: {
    color: '#FF5722',
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
    justifyContent: 'center',
    paddingVertical: 64,
  },
  emptyText: {
    marginTop: 16,
    fontSize: 16,
    color: '#999',
  },
});
