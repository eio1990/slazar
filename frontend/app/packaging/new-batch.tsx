import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  TextInput,
  Alert,
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { useRouter } from 'expo-router';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

const API_URL = process.env.EXPO_PUBLIC_BACKEND_URL || 'http://localhost:8001';

export default function NewPackagingBatchScreen() {
  const router = useRouter();
  const queryClient = useQueryClient();

  const [selectedRecipe, setSelectedRecipe] = useState<any>(null);
  const [sourceWeight, setSourceWeight] = useState('');
  const [plannedQty, setPlannedQty] = useState('');
  const [notes, setNotes] = useState('');

  // Get packaging recipes
  const { data: recipes, isLoading: recipesLoading } = useQuery({
    queryKey: ['packaging-recipes'],
    queryFn: async () => {
      const response = await fetch(`${API_URL}/api/packaging/recipes?active_only=true`);
      if (!response.ok) throw new Error('Failed to fetch recipes');
      return response.json();
    },
  });

  // Create batch mutation
  const createBatchMutation = useMutation({
    mutationFn: async (batchData: any) => {
      const response = await fetch(`${API_URL}/api/packaging/batches`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(batchData),
      });
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to create batch');
      }
      return response.json();
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['packaging-batches'] });
      Alert.alert('Успіх', 'Партію фасування створено', [
        { text: 'OK', onPress: () => router.replace(`/packaging/${data.id}` as any) }
      ]);
    },
    onError: (error: any) => {
      Alert.alert('Помилка', error.message || 'Не вдалося створити партію');
    },
  });

  const handleSubmit = () => {
    if (!selectedRecipe) {
      Alert.alert('Помилка', 'Оберіть рецепт фасування');
      return;
    }

    const weight = parseFloat(sourceWeight);
    if (!sourceWeight || isNaN(weight) || weight <= 0) {
      Alert.alert('Помилка', 'Введіть коректну вагу вихідного продукту');
      return;
    }

    const planned = parseInt(plannedQty);
    if (plannedQty && (isNaN(planned) || planned <= 0)) {
      Alert.alert('Помилка', 'Введіть коректну планову кількість');
      return;
    }

    const batchData = {
      recipe_id: selectedRecipe.id,
      source_weight_taken: weight,
      planned_quantity: planned || null,
      operator_notes: notes || null,
    };

    createBatchMutation.mutate(batchData);
  };

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      style={styles.container}
    >
      <ScrollView style={styles.container} contentContainerStyle={styles.content}>
        {/* Header */}
        <View style={styles.header}>
          <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
            <MaterialCommunityIcons name="arrow-left" size={24} color="#007AFF" />
          </TouchableOpacity>
          <Text style={styles.title}>Нова партія фасування</Text>
        </View>

        {/* Recipe Selection */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Рецепт фасування *</Text>
          
          {recipesLoading ? (
            <ActivityIndicator color="#007AFF" />
          ) : !recipes || recipes.length === 0 ? (
            <Text style={styles.emptyText}>Рецепти фасування не знайдено</Text>
          ) : (
            <View style={styles.recipeList}>
              {recipes.map((recipe: any) => (
                <TouchableOpacity
                  key={recipe.id}
                  style={[
                    styles.recipeCard,
                    selectedRecipe?.id === recipe.id && styles.recipeCardSelected,
                  ]}
                  onPress={() => setSelectedRecipe(recipe)}
                >
                  <View style={styles.recipeHeader}>
                    <Text style={styles.recipeName}>{recipe.target_product_name}</Text>
                    <View style={[
                      styles.typeBadge,
                      recipe.packaging_type === 'vacuum' && styles.vacuumBadge,
                      recipe.packaging_type === 'skin' && styles.skinBadge,
                      recipe.packaging_type === 'weight' && styles.weightBadge,
                    ]}>
                      <Text style={styles.typeBadgeText}>
                        {recipe.packaging_type === 'vacuum' ? 'VAC' : 
                         recipe.packaging_type === 'skin' ? 'SKIN' : 'WEIGHT'}
                      </Text>
                    </View>
                  </View>
                  <Text style={styles.recipeSource}>
                    З: {recipe.source_product_name}
                  </Text>
                  <Text style={styles.recipeWeight}>
                    Вага: {recipe.target_weight_grams}г
                  </Text>
                  {selectedRecipe?.id === recipe.id && (
                    <View style={styles.selectedCheck}>
                      <MaterialCommunityIcons name="check-circle" size={24} color="#4CAF50" />
                    </View>
                  )}
                </TouchableOpacity>
              ))}
            </View>
          )}
        </View>

        {/* Source Weight */}
        <View style={styles.section}>
          <Text style={styles.label}>Вага взятого вихідного продукту (кг) *</Text>
          <TextInput
            style={styles.input}
            value={sourceWeight}
            onChangeText={setSourceWeight}
            placeholder="напр. 10.5"
            keyboardType="decimal-pad"
          />
          <Text style={styles.hint}>
            Введіть фактичну вагу продукту для фасування
          </Text>
        </View>

        {/* Planned Quantity */}
        <View style={styles.section}>
          <Text style={styles.label}>Планова кількість (шт, опціонально)</Text>
          <TextInput
            style={styles.input}
            value={plannedQty}
            onChangeText={setPlannedQty}
            placeholder="напр. 200"
            keyboardType="number-pad"
          />
          <Text style={styles.hint}>
            Приблизна кількість одиниць для фасування
          </Text>
        </View>

        {/* Notes */}
        <View style={styles.section}>
          <Text style={styles.label}>Примітки (опціонально)</Text>
          <TextInput
            style={styles.textArea}
            value={notes}
            onChangeText={setNotes}
            placeholder="Додаткова інформація..."
            multiline
            numberOfLines={3}
          />
        </View>

        {/* Submit Button */}
        <TouchableOpacity
          style={[
            styles.submitButton,
            createBatchMutation.isPending && styles.submitButtonDisabled,
          ]}
          onPress={handleSubmit}
          disabled={createBatchMutation.isPending}
        >
          {createBatchMutation.isPending ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <>
              <MaterialCommunityIcons name="package-variant-closed" size={20} color="#fff" />
              <Text style={styles.submitButtonText}>Створити партію</Text>
            </>
          )}
        </TouchableOpacity>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  content: {
    padding: 16,
    paddingBottom: 32,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 24,
  },
  backButton: {
    marginRight: 12,
    padding: 4,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#333',
  },
  section: {
    marginBottom: 24,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333',
    marginBottom: 12,
  },
  emptyText: {
    fontSize: 14,
    color: '#999',
    textAlign: 'center',
    padding: 20,
  },
  recipeList: {
    gap: 12,
  },
  recipeCard: {
    backgroundColor: '#fff',
    padding: 16,
    borderRadius: 12,
    borderWidth: 2,
    borderColor: '#e0e0e0',
  },
  recipeCardSelected: {
    borderColor: '#4CAF50',
    backgroundColor: '#E8F5E9',
  },
  recipeHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  recipeName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
    flex: 1,
  },
  typeBadge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
  },
  vacuumBadge: {
    backgroundColor: '#2196F3',
  },
  skinBadge: {
    backgroundColor: '#FF9800',
  },
  weightBadge: {
    backgroundColor: '#9C27B0',
  },
  typeBadgeText: {
    color: '#fff',
    fontSize: 11,
    fontWeight: '600',
  },
  recipeSource: {
    fontSize: 14,
    color: '#666',
    marginBottom: 4,
  },
  recipeWeight: {
    fontSize: 14,
    color: '#666',
  },
  selectedCheck: {
    position: 'absolute',
    top: 8,
    right: 8,
  },
  label: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
    marginBottom: 8,
  },
  input: {
    backgroundColor: '#fff',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#ddd',
    padding: 12,
    fontSize: 16,
    color: '#333',
  },
  hint: {
    fontSize: 12,
    color: '#999',
    marginTop: 6,
  },
  textArea: {
    backgroundColor: '#fff',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#ddd',
    padding: 12,
    fontSize: 16,
    color: '#333',
    minHeight: 80,
    textAlignVertical: 'top',
  },
  submitButton: {
    backgroundColor: '#007AFF',
    borderRadius: 12,
    padding: 16,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    marginTop: 8,
  },
  submitButtonDisabled: {
    backgroundColor: '#ccc',
  },
  submitButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
});
