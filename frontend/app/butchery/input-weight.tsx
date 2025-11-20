import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  TextInput,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  Alert,
  ActivityIndicator,
} from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { useQuery } from '@tanstack/react-query';
import Toast from 'react-native-toast-message';

const API_URL = process.env.EXPO_PUBLIC_BACKEND_URL || 'http://localhost:8001';

export default function InputWeightScreen() {
  const router = useRouter();
  const { meatType, grade } = useLocalSearchParams();
  const [weight, setWeight] = useState('');
  const [notes, setNotes] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Get butchery recipes
  const { data: recipes, isLoading } = useQuery({
    queryKey: ['butchery-recipes'],
    queryFn: async () => {
      const response = await fetch(`${API_URL}/api/butchery/recipes`);
      if (!response.ok) throw new Error('Failed to load recipes');
      return response.json();
    },
  });

  // Get stock balances
  const { data: stockBalances } = useQuery({
    queryKey: ['stock-balances'],
    queryFn: async () => {
      const response = await fetch(`${API_URL}/api/stock/balances`);
      if (!response.ok) throw new Error('Failed to load stock balances');
      return response.json();
    },
  });

  // Find the recipe based on meat type and grade
  const findRecipe = () => {
    if (!recipes) return null;
    
    // Mapping logic to find correct recipe
    let searchTerm = '';
    
    if (meatType === 'beef') {
      if (grade === 'premium') searchTerm = 'яловичини вищого';
      else if (grade === 'first') searchTerm = 'яловичини першого';
      else if (grade === 'second') searchTerm = 'яловичини другого';
      else if (grade === 'carcass') searchTerm = 'туші яловичини';
    } else if (meatType === 'horse') {
      if (grade === 'premium') searchTerm = 'конини вищого';
      else if (grade === 'first') searchTerm = 'конини першого';
      else if (grade === 'second') searchTerm = 'конини другого';
      else if (grade === 'carcass') searchTerm = 'туші конини';
    } else if (meatType === 'pork') {
      searchTerm = 'свинини';
    } else if (meatType === 'chicken') {
      searchTerm = 'курки';
    } else if (meatType === 'turkey') {
      searchTerm = 'індички';
    }

    return recipes.find((r: any) => 
      r.name.toLowerCase().includes(searchTerm.toLowerCase())
    );
  };

  const selectedRecipe = findRecipe();
  
  // Find stock balance for the source material
  const sourceBalance = stockBalances?.find((b: any) => 
    b.nomenclature_id === selectedRecipe?.source_nomenclature_id
  );
  const availableStock = sourceBalance?.quantity || 0;

  const getMeatTypeName = () => {
    switch (meatType) {
      case 'beef': return 'Яловичина';
      case 'horse': return 'Конина';
      case 'pork': return 'Свинина';
      case 'chicken': return 'Курка';
      case 'turkey': return 'Індичка';
      default: return "М'ясо";
    }
  };

  const getGradeName = () => {
    if (!grade) return '';
    switch (grade) {
      case 'premium': return 'Вищий ґатунок';
      case 'first': return 'Перший ґатунок';
      case 'second': return 'Другий ґатунок';
      case 'carcass': return 'Туша';
      default: return '';
    }
  };

  const handleStartButchery = async () => {
    if (!selectedRecipe) {
      Toast.show({
        type: 'error',
        text1: 'Помилка',
        text2: 'Не знайдено рецепт для обраного типу м\'яса',
        position: 'top',
        visibilityTime: 3000,
      });
      return;
    }

    const weightNum = parseFloat(weight);
    if (!weightNum || weightNum <= 0) {
      Toast.show({
        type: 'error',
        text1: 'Помилка',
        text2: 'Введіть коректну вагу (більше 0)',
        position: 'top',
        visibilityTime: 3000,
      });
      return;
    }

    // Check if enough material in stock
    if (availableStock > 0 && weightNum > availableStock) {
      Toast.show({
        type: 'error',
        text1: 'Недостатньо матеріалу на складі!',
        text2: `Потрібно: ${weightNum.toFixed(2)} кг, На складі: ${availableStock.toFixed(2)} кг`,
        position: 'top',
        visibilityTime: 4000,
      });
      return;
    }

    setIsSubmitting(true);
    try {
      const idempotencyKey = `butchery-${Date.now()}-${Math.random()}`;
      
      const response = await fetch(`${API_URL}/api/butchery/operations`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          recipe_id: selectedRecipe.id,
          source_nomenclature_id: selectedRecipe.source_nomenclature_id,
          input_weight: weightNum,
          notes: notes || undefined,
          idempotency_key: idempotencyKey,
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Помилка створення операції');
      }

      const result = await response.json();
      
      // Show success toast
      Toast.show({
        type: 'success',
        text1: 'Цикл розділки запущено!',
        text2: `№${result.operation_number} - ${getMeatTypeName()}`,
        position: 'top',
        visibilityTime: 3000,
      });

      // Navigate to the butchery tab
      setTimeout(() => {
        router.push('/(tabs)/butchery' as any);
      }, 500);
    } catch (error: any) {
      Alert.alert('Помилка', error.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#007AFF" />
      </View>
    );
  }

  if (!selectedRecipe) {
    return (
      <View style={styles.errorContainer}>
        <MaterialCommunityIcons name="alert" size={60} color="#f44336" />
        <Text style={styles.errorText}>Рецепт не знайдено</Text>
        <TouchableOpacity style={styles.backBtn} onPress={() => router.back()}>
          <Text style={styles.backBtnText}>Повернутися</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
          <MaterialCommunityIcons name="arrow-left" size={24} color="#007AFF" />
        </TouchableOpacity>
        <View>
          <Text style={styles.headerTitle}>Введіть вагу сировини</Text>
          <Text style={styles.headerSubtitle}>
            {getMeatTypeName()}{grade ? ` - ${getGradeName()}` : ''}
          </Text>
        </View>
      </View>

      <ScrollView style={styles.content}>
        <Text style={styles.subtitle}>Крок {grade ? '3' : '2'} з {grade ? '3' : '2'}</Text>

        {/* Recipe info card */}
        <View style={styles.recipeCard}>
          <Text style={styles.recipeLabel}>Буде використано рецепт:</Text>
          <Text style={styles.recipeName}>{selectedRecipe.name}</Text>
          <Text style={styles.recipeSource}>{selectedRecipe.source_name}</Text>
        </View>

        {/* Weight input */}
        <View style={styles.inputCard}>
          <Text style={styles.inputLabel}>Вага сировини, кг *</Text>
          <Text style={styles.stockHint}>На складі: {availableStock.toFixed(2)} кг</Text>
          <TextInput
            style={styles.input}
            value={weight}
            onChangeText={setWeight}
            keyboardType="decimal-pad"
            placeholder="Введіть вагу"
            placeholderTextColor="#999"
            autoFocus
          />
        </View>

        {/* Notes */}
        <View style={styles.inputCard}>
          <Text style={styles.inputLabel}>Примітки (опціонально)</Text>
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

        {/* Start button */}
        <TouchableOpacity
          style={[styles.startButton, isSubmitting && styles.startButtonDisabled]}
          onPress={handleStartButchery}
          disabled={isSubmitting}
        >
          {isSubmitting ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <>
              <MaterialCommunityIcons name="play-circle" size={20} color="#fff" />
              <Text style={styles.startButtonText}>Почати розділку</Text>
            </>
          )}
        </TouchableOpacity>

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
  errorContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 32,
  },
  errorText: {
    fontSize: 18,
    color: '#666',
    marginTop: 16,
    marginBottom: 24,
  },
  backBtn: {
    backgroundColor: '#007AFF',
    paddingVertical: 12,
    paddingHorizontal: 24,
    borderRadius: 8,
  },
  backBtnText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
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
  headerSubtitle: {
    fontSize: 14,
    color: '#666',
    marginTop: 2,
  },
  content: {
    flex: 1,
    padding: 16,
  },
  subtitle: {
    fontSize: 14,
    color: '#999',
    marginBottom: 16,
  },
  recipeCard: {
    backgroundColor: '#E3F2FD',
    padding: 16,
    borderRadius: 12,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: '#2196F3',
  },
  recipeLabel: {
    fontSize: 12,
    color: '#1976D2',
    marginBottom: 4,
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
  inputCard: {
    backgroundColor: '#fff',
    padding: 16,
    borderRadius: 12,
    marginBottom: 16,
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
    marginBottom: 16,
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
  startButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#4CAF50',
    padding: 16,
    borderRadius: 12,
    gap: 8,
  },
  startButtonDisabled: {
    opacity: 0.6,
  },
  startButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  stockHint: {
    fontSize: 12,
    color: '#2196F3',
    marginBottom: 6,
    fontStyle: 'italic',
  },
});
