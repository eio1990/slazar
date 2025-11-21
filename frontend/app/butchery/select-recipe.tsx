import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
  TextInput,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { useQuery } from '@tanstack/react-query';

const API_URL = process.env.EXPO_PUBLIC_BACKEND_URL || 'http://localhost:8001';

interface RecipeOutput {
  output_nomenclature_id: number;
  output_name: string;
  yield_percentage: number;
  is_main_output: boolean;
  output_type: string;
}

interface Recipe {
  id: number;
  name: string;
  source_nomenclature_id: number;
  source_name: string;
  description: string;
  level: number;
  is_active: boolean;
  outputs: RecipeOutput[];
}

export default function SelectRecipeScreen() {
  const router = useRouter();
  const [selectedRecipe, setSelectedRecipe] = useState<Recipe | null>(null);
  const [inputWeight, setInputWeight] = useState('');
  const [notes, setNotes] = useState('');

  // Отримати список рецептів
  const { data: recipes, isLoading } = useQuery({
    queryKey: ['butchery-recipes'],
    queryFn: async () => {
      const response = await fetch(`${API_URL}/api/butchery/recipes`);
      if (!response.ok) throw new Error('Не вдалося завантажити рецепти');
      return response.json() as Promise<Recipe[]>;
    },
  });

  const handleCreateOperation = async () => {
    if (!selectedRecipe) {
      Alert.alert('Помилка', 'Оберіть рецепт розділки');
      return;
    }

    const weight = parseFloat(inputWeight);
    if (!weight || weight <= 0) {
      Alert.alert('Помилка', 'Введіть коректну вагу (більше 0)');
      return;
    }

    try {
      const idempotencyKey = `butchery-${Date.now()}-${Math.random()}`;
      
      const response = await fetch(`${API_URL}/api/butchery/operations`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          recipe_id: selectedRecipe.id,
          source_nomenclature_id: selectedRecipe.source_nomenclature_id,
          input_weight: weight,
          notes: notes || undefined,
          idempotency_key: idempotencyKey,
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Помилка створення операції');
      }

      const result = await response.json();
      
      Alert.alert(
        'Успіх',
        `Операцію розділки розпочато\n№${result.operation_number}`,
        [
          {
            text: 'OK',
            onPress: () => router.push(`/butchery/${result.operation_id}` as any),
          },
        ]
      );
    } catch (error: any) {
      Alert.alert('Помилка', error.message);
    }
  };

  const calculateExpectedOutputs = () => {
    if (!selectedRecipe || !inputWeight) return [];
    const weight = parseFloat(inputWeight);
    if (!weight) return [];

    return selectedRecipe.outputs.map((output) => ({
      ...output,
      expected_weight: (weight * output.yield_percentage) / 100,
    }));
  };

  const expectedOutputs = calculateExpectedOutputs();

  if (isLoading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#007AFF" />
      </View>
    );
  }

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <ScrollView style={styles.content}>
        {/* Header */}
        <View style={styles.header}>
          <TouchableOpacity onPress={() => router.push('/(tabs)/butchery' as any)} style={styles.backButton}>
            <MaterialCommunityIcons name="arrow-left" size={24} color="#007AFF" />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>Нова розділка</Text>
        </View>

        {/* Recipe selection */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>1. Оберіть рецепт розділки</Text>
          {recipes?.map((recipe) => (
            <TouchableOpacity
              key={recipe.id}
              style={[
                styles.recipeCard,
                selectedRecipe?.id === recipe.id && styles.recipeCardSelected,
              ]}
              onPress={() => setSelectedRecipe(recipe)}
            >
              <View style={styles.recipeHeader}>
                <View style={styles.recipeTitleRow}>
                  <MaterialCommunityIcons
                    name={selectedRecipe?.id === recipe.id ? 'radiobox-marked' : 'radiobox-blank'}
                    size={24}
                    color={selectedRecipe?.id === recipe.id ? '#007AFF' : '#999'}
                  />
                  <View style={styles.recipeTitleContainer}>
                    <Text style={styles.recipeName}>{recipe.name}</Text>
                    <Text style={styles.recipeSource}>
                      <MaterialCommunityIcons name="arrow-right" size={14} color="#666" />
                      {' '}{recipe.source_name}
                    </Text>
                  </View>
                </View>
                <View style={styles.levelBadge}>
                  <Text style={styles.levelText}>Рівень {recipe.level}</Text>
                </View>
              </View>

              {recipe.description && (
                <Text style={styles.recipeDescription}>{recipe.description}</Text>
              )}

              <View style={styles.outputsContainer}>
                <Text style={styles.outputsTitle}>Виходи:</Text>
                {recipe.outputs.map((output, idx) => (
                  <View key={idx} style={styles.outputRow}>
                    <View style={styles.outputDot} />
                    <Text style={styles.outputText}>
                      {output.output_name}
                    </Text>
                  </View>
                ))}
              </View>
            </TouchableOpacity>
          ))}
        </View>

        {/* Input weight */}
        {selectedRecipe && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>2. Введіть вагу сировини</Text>
            <View style={styles.inputCard}>
              <Text style={styles.inputLabel}>Вага туші, кг</Text>
              <TextInput
                style={styles.input}
                value={inputWeight}
                onChangeText={setInputWeight}
                keyboardType="decimal-pad"
                placeholder="Наприклад: 150.5"
                placeholderTextColor="#999"
              />
            </View>

            {/* Expected outputs preview */}
            {expectedOutputs.length > 0 && (
              <View style={styles.previewCard}>
                <Text style={styles.previewTitle}>Очікувані виходи при {inputWeight} кг:</Text>
                {expectedOutputs.map((output, idx) => (
                  <View key={idx} style={styles.previewRow}>
                    <Text style={styles.previewName}>{output.output_name}</Text>
                    <Text style={styles.previewValue}>
                      {output.expected_weight.toFixed(2)} кг
                    </Text>
                  </View>
                ))}
              </View>
            )}
          </View>
        )}

        {/* Notes */}
        {selectedRecipe && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>3. Примітки (опціонально)</Text>
            <View style={styles.inputCard}>
              <TextInput
                style={[styles.input, styles.textArea]}
                value={notes}
                onChangeText={setNotes}
                placeholder="Додаткова інформація..."
                placeholderTextColor="#999"
                multiline
                numberOfLines={3}
              />
            </View>
          </View>
        )}

        {/* Create button */}
        {selectedRecipe && (
          <View style={styles.buttonContainer}>
            <TouchableOpacity
              style={styles.createButton}
              onPress={handleCreateOperation}
            >
              <MaterialCommunityIcons name="plus-circle" size={20} color="#fff" />
              <Text style={styles.createButtonText}>Розпочати розділку</Text>
            </TouchableOpacity>
          </View>
        )}

        <View style={{ height: 40 }} />
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  content: {
    flex: 1,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  backButton: {
    marginRight: 12,
    padding: 4,
  },
  headerTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#333',
  },
  section: {
    marginTop: 16,
    paddingHorizontal: 16,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
    marginBottom: 12,
  },
  recipeCard: {
    backgroundColor: '#fff',
    padding: 16,
    borderRadius: 12,
    marginBottom: 12,
    borderWidth: 2,
    borderColor: '#e0e0e0',
  },
  recipeCardSelected: {
    borderColor: '#007AFF',
    backgroundColor: '#F0F8FF',
  },
  recipeHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 8,
  },
  recipeTitleRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    flex: 1,
  },
  recipeTitleContainer: {
    marginLeft: 12,
    flex: 1,
  },
  recipeName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
    marginBottom: 4,
  },
  recipeSource: {
    fontSize: 14,
    color: '#666',
  },
  levelBadge: {
    backgroundColor: '#E3F2FD',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 8,
  },
  levelText: {
    fontSize: 12,
    color: '#1976D2',
    fontWeight: '600',
  },
  recipeDescription: {
    fontSize: 14,
    color: '#666',
    marginBottom: 12,
    marginLeft: 36,
  },
  outputsContainer: {
    marginTop: 8,
    marginLeft: 36,
  },
  outputsTitle: {
    fontSize: 13,
    fontWeight: '600',
    color: '#666',
    marginBottom: 6,
  },
  outputRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 4,
  },
  outputDot: {
    width: 4,
    height: 4,
    borderRadius: 2,
    backgroundColor: '#999',
    marginRight: 8,
  },
  outputText: {
    fontSize: 13,
    color: '#666',
  },
  inputCard: {
    backgroundColor: '#fff',
    padding: 16,
    borderRadius: 12,
    marginBottom: 12,
  },
  inputLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
    marginBottom: 8,
  },
  input: {
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 8,
    padding: 12,
    fontSize: 16,
    color: '#333',
  },
  textArea: {
    height: 80,
    textAlignVertical: 'top',
  },
  previewCard: {
    backgroundColor: '#FFF9E6',
    padding: 16,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#FFE082',
  },
  previewTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#F57C00',
    marginBottom: 12,
  },
  previewRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 6,
  },
  previewName: {
    fontSize: 14,
    color: '#666',
  },
  previewValue: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
  },
  buttonContainer: {
    paddingHorizontal: 16,
    marginTop: 16,
  },
  createButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#4CAF50',
    padding: 16,
    borderRadius: 12,
    gap: 8,
  },
  createButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
});
