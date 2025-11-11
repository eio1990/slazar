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
  Platform,
} from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Constants from 'expo-constants';

const API_URL = Constants.expoConfig?.extra?.EXPO_PUBLIC_BACKEND_URL || 'http://localhost:8001';

interface RecipeStep {
  id: number;
  step_order: number;
  step_type: string;
  step_name: string;
  duration_days: number;
  parameters?: any;
}

interface Recipe {
  id: number;
  name: string;
  target_product_id: number;
  target_product_name: string;
  expected_yield_min: number;
  expected_yield_max: number;
  description?: string;
  steps: RecipeStep[];
}

export default function RecipeDetailScreen() {
  const router = useRouter();
  const { id } = useLocalSearchParams();
  const queryClient = useQueryClient();
  
  const [initialWeight, setInitialWeight] = useState('');
  const [trimWaste, setTrimWaste] = useState('0');
  const [hasTrim, setHasTrim] = useState(false);
  const [trimReturned, setTrimReturned] = useState(false);

  const { data: recipe, isLoading } = useQuery({
    queryKey: ['recipe', id],
    queryFn: async () => {
      const response = await fetch(`${API_URL}/api/production/recipes/${id}`);
      if (!response.ok) throw new Error('Failed to fetch recipe');
      return response.json();
    },
  });

  const createBatchMutation = useMutation({
    mutationFn: async (batchData: any) => {
      const response = await fetch(`${API_URL}/api/production/batches`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(batchData),
      });
      if (!response.ok) throw new Error('Failed to create batch');
      return response.json();
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['batches'] });
      Alert.alert(
        'Успіх',
        `Партія ${data.batch_number} створена`,
        [
          {
            text: 'Переглянути',
            onPress: () => router.push(`/batches/${data.id}` as any),
          },
          {
            text: 'Закрити',
            onPress: () => router.back(),
          },
        ]
      );
    },
    onError: (error) => {
      Alert.alert('Помилка', 'Не вдалося створити партію');
    },
  });

  const handleCreateBatch = () => {
    if (!initialWeight || parseFloat(initialWeight) <= 0) {
      Alert.alert('Помилка', 'Введіть початкову вагу');
      return;
    }

    if (hasTrim && (!trimWaste || parseFloat(trimWaste) < 0)) {
      Alert.alert('Помилка', 'Введіть вагу обрізків');
      return;
    }

    createBatchMutation.mutate({
      recipe_id: parseInt(id as string),
      initial_weight: parseFloat(initialWeight),
      trim_waste: hasTrim ? parseFloat(trimWaste) : 0,
      trim_returned: trimReturned,
      operator_notes: hasTrim ? 'Обрізки зафіксовано' : '',
    });
  };

  const getStepIcon = (stepType: string) => {
    switch (stepType) {
      case 'trim': return 'scissors-cutting';
      case 'salt': return 'shaker-outline';
      case 'wash': return 'water';
      case 'dry': return 'weather-sunny';
      case 'press': return 'hydraulic-oil-level';
      case 'mix': return 'mixer';
      case 'marinade': return 'bottle-tonic-plus';
      case 'vacuum': return 'package-variant-closed';
      case 'sugar': return 'cube-outline';
      case 'grind': return 'blender';
      case 'massage': return 'rotate-3d-variant';
      case 'stuff': return 'food-drumstick';
      case 'cure': return 'thermometer-low';
      default: return 'checkbox-marked-circle-outline';
    }
  };

  if (isLoading || !recipe) {
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator size="large" color="#4CAF50" />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity style={styles.backButton} onPress={() => router.back()}>
          <MaterialCommunityIcons name="arrow-left" size={24} color="#fff" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>{recipe.name}</Text>
        <View style={styles.placeholder} />
      </View>

      <ScrollView style={styles.content}>
        {/* Recipe Info */}
        <View style={styles.infoCard}>
          <Text style={styles.infoLabel}>Готовий продукт:</Text>
          <Text style={styles.infoValue}>{recipe.target_product_name}</Text>
          
          <View style={styles.yieldContainer}>
            <MaterialCommunityIcons name="chart-line" size={20} color="#4CAF50" />
            <Text style={styles.yieldText}>
              Очікуваний вихід: {recipe.expected_yield_min}% - {recipe.expected_yield_max}%
            </Text>
          </View>
        </View>

        {/* Production Steps */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Етапи виробництва</Text>
          {recipe.steps.map((step, index) => (
            <View key={step.id} style={styles.stepCard}>
              <View style={styles.stepHeader}>
                <View style={styles.stepIconContainer}>
                  <MaterialCommunityIcons
                    name={getStepIcon(step.step_type) as any}
                    size={24}
                    color="#4CAF50"
                  />
                </View>
                <View style={styles.stepInfo}>
                  <Text style={styles.stepOrder}>Крок {step.step_order}</Text>
                  <Text style={styles.stepName}>{step.step_name}</Text>
                </View>
              </View>
              {step.duration_days > 0 && (
                <View style={styles.durationContainer}>
                  <MaterialCommunityIcons name="clock-outline" size={16} color="#666" />
                  <Text style={styles.durationText}>
                    Тривалість: {step.duration_days} {step.duration_days === 1 ? 'день' : 'днів'}
                  </Text>
                </View>
              )}
            </View>
          ))}
        </View>

        {/* Create Batch Form */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Створити нову партію</Text>
          
          <View style={styles.formCard}>
            <Text style={styles.label}>Початкова вага (кг) *</Text>
            <TextInput
              style={styles.input}
              value={initialWeight}
              onChangeText={setInitialWeight}
              keyboardType="decimal-pad"
              placeholder="Введіть вагу"
            />

            {/* Trim Question */}
            <View style={styles.checkboxContainer}>
              <TouchableOpacity
                style={styles.checkbox}
                onPress={() => {
                  setHasTrim(!hasTrim);
                  if (!hasTrim === false) {
                    setTrimWaste('0');
                    setTrimReturned(false);
                  }
                }}
              >
                <MaterialCommunityIcons
                  name={hasTrim ? 'checkbox-marked' : 'checkbox-blank-outline'}
                  size={24}
                  color="#4CAF50"
                />
                <Text style={styles.checkboxLabel}>Є обрізки?</Text>
              </TouchableOpacity>
            </View>

            {hasTrim && (
              <>
                <Text style={styles.label}>Вага обрізків (кг) *</Text>
                <TextInput
                  style={styles.input}
                  value={trimWaste}
                  onChangeText={setTrimWaste}
                  keyboardType="decimal-pad"
                  placeholder="Введіть вагу обрізків"
                />

                <View style={styles.checkboxContainer}>
                  <TouchableOpacity
                    style={styles.checkbox}
                    onPress={() => setTrimReturned(!trimReturned)}
                  >
                    <MaterialCommunityIcons
                      name={trimReturned ? 'checkbox-marked' : 'checkbox-blank-outline'}
                      size={24}
                      color="#4CAF50"
                    />
                    <Text style={styles.checkboxLabel}>Повернути обрізки на склад</Text>
                  </TouchableOpacity>
                </View>
              </>
            )}

            <TouchableOpacity
              style={[styles.createButton, createBatchMutation.isPending && styles.createButtonDisabled]}
              onPress={handleCreateBatch}
              disabled={createBatchMutation.isPending}
            >
              {createBatchMutation.isPending ? (
                <ActivityIndicator color="#fff" />
              ) : (
                <>
                  <MaterialCommunityIcons name="plus-circle" size={20} color="#fff" />
                  <Text style={styles.createButtonText}>Створити партію</Text>
                </>
              )}
            </TouchableOpacity>
          </View>
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
    fontSize: 18,
    fontWeight: 'bold',
    color: '#fff',
    flex: 1,
    textAlign: 'center',
    marginHorizontal: 16,
  },
  placeholder: {
    width: 32,
  },
  centerContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  content: {
    flex: 1,
  },
  infoCard: {
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
  infoLabel: {
    fontSize: 14,
    color: '#666',
    marginBottom: 4,
  },
  infoValue: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
    marginBottom: 12,
  },
  yieldContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 8,
    paddingHorizontal: 12,
    backgroundColor: '#E8F5E9',
    borderRadius: 8,
  },
  yieldText: {
    fontSize: 14,
    color: '#4CAF50',
    marginLeft: 8,
    fontWeight: '600',
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
  stepCard: {
    backgroundColor: '#fff',
    padding: 12,
    borderRadius: 8,
    marginBottom: 8,
    ...Platform.select({
      ios: {
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 1 },
        shadowOpacity: 0.05,
        shadowRadius: 2,
      },
      android: {
        elevation: 1,
      },
      web: {
        boxShadow: '0 1px 2px rgba(0,0,0,0.05)',
      },
    }),
  },
  stepHeader: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  stepIconContainer: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: '#E8F5E9',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  stepInfo: {
    flex: 1,
  },
  stepOrder: {
    fontSize: 12,
    color: '#999',
    marginBottom: 2,
  },
  stepName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
  },
  durationContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 8,
    paddingTop: 8,
    borderTopWidth: 1,
    borderTopColor: '#f0f0f0',
  },
  durationText: {
    fontSize: 14,
    color: '#666',
    marginLeft: 8,
  },
  formCard: {
    backgroundColor: '#fff',
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
  label: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
    marginBottom: 8,
  },
  input: {
    borderWidth: 1,
    borderColor: '#e0e0e0',
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 16,
    marginBottom: 16,
    backgroundColor: '#fff',
  },
  checkboxContainer: {
    marginBottom: 16,
  },
  checkbox: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  checkboxLabel: {
    fontSize: 16,
    color: '#333',
    marginLeft: 8,
  },
  createButton: {
    flexDirection: 'row',
    backgroundColor: '#4CAF50',
    paddingVertical: 14,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 8,
  },
  createButtonDisabled: {
    opacity: 0.6,
  },
  createButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
    marginLeft: 8,
  },
});
