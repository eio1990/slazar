import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  ActivityIndicator,
  Platform,
} from 'react-native';
import { useRouter } from 'expo-router';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useQuery } from '@tanstack/react-query';

const API_URL = process.env.EXPO_PUBLIC_BACKEND_URL || 'http://localhost:8001';

interface Recipe {
  id: number;
  name: string;
  target_product_id: number;
  target_product_name: string;
  expected_yield_min: number;
  expected_yield_max: number;
  description?: string;
}

export default function RecipesScreen() {
  const router = useRouter();

  const { data: recipes, isLoading, error } = useQuery({
    queryKey: ['recipes'],
    queryFn: async () => {
      const response = await fetch(`${API_URL}/api/production/recipes`);
      if (!response.ok) throw new Error('Failed to fetch recipes');
      return response.json();
    },
  });

  const renderRecipe = ({ item }: { item: Recipe }) => (
    <TouchableOpacity
      style={styles.recipeCard}
      onPress={() => router.push(`/recipes/${item.id}` as any)}
    >
      <View style={styles.recipeHeader}>
        <MaterialCommunityIcons name="book-open-variant" size={24} color="#4CAF50" />
        <View style={styles.recipeInfo}>
          <Text style={styles.recipeName}>{item.name}</Text>
          <Text style={styles.productName}>{item.target_product_name}</Text>
        </View>
        <MaterialCommunityIcons name="chevron-right" size={24} color="#999" />
      </View>
      
      <View style={styles.yieldContainer}>
        <MaterialCommunityIcons name="chart-line" size={18} color="#666" />
        <Text style={styles.yieldText}>
          Очікуваний вихід: {item.expected_yield_min}% - {item.expected_yield_max}%
        </Text>
      </View>
      
      {item.description && (
        <Text style={styles.description} numberOfLines={2}>
          {item.description}
        </Text>
      )}
    </TouchableOpacity>
  );

  if (isLoading) {
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator size="large" color="#4CAF50" />
        <Text style={styles.loadingText}>Завантаження рецептів...</Text>
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.centerContainer}>
        <MaterialCommunityIcons name="alert-circle" size={48} color="#f44336" />
        <Text style={styles.errorText}>Помилка завантаження рецептів</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity
          style={styles.backButton}
          onPress={() => router.back()}
        >
          <MaterialCommunityIcons name="arrow-left" size={24} color="#fff" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Рецепти</Text>
        <View style={styles.placeholder} />
      </View>

      <FlatList
        data={recipes}
        renderItem={renderRecipe}
        keyExtractor={(item) => item.id.toString()}
        contentContainerStyle={styles.listContent}
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            <MaterialCommunityIcons name="book-open-variant" size={64} color="#ccc" />
            <Text style={styles.emptyText}>Немає рецептів</Text>
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
  listContent: {
    padding: 16,
  },
  recipeCard: {
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
  recipeHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  recipeInfo: {
    flex: 1,
    marginLeft: 12,
  },
  recipeName: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 4,
  },
  productName: {
    fontSize: 14,
    color: '#666',
  },
  yieldContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 8,
    paddingHorizontal: 12,
    backgroundColor: '#f5f5f5',
    borderRadius: 8,
    marginBottom: 8,
  },
  yieldText: {
    fontSize: 14,
    color: '#666',
    marginLeft: 8,
    fontWeight: '600',
  },
  description: {
    fontSize: 14,
    color: '#999',
    lineHeight: 20,
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
