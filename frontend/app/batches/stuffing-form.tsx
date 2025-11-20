import React, { useState, useEffect } from 'react';
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
import { useRouter, useLocalSearchParams } from 'expo-router';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

const API_URL = process.env.EXPO_PUBLIC_BACKEND_URL || 'http://localhost:8001';

// Common casing IDs
const CASING_IDS = {
  SUDJUK: 42, // Кишка говяча для Суджука
  MAHAN: 43,  // Оболонка для Махана
};

export default function StuffingFormScreen() {
  const router = useRouter();
  const { batchId, stepId, recipeName } = useLocalSearchParams();
  const queryClient = useQueryClient();
  
  // Determine casing type based on recipe name
  const isSudjuk = (recipeName as string)?.toLowerCase().includes('суджук');
  const isMahan = (recipeName as string)?.toLowerCase().includes('махан');
  const defaultCasingId = isSudjuk ? CASING_IDS.SUDJUK : isMahan ? CASING_IDS.MAHAN : CASING_IDS.SUDJUK;
  
  // Casing weight tracking
  const [casingId, setCasingId] = useState(defaultCasingId);
  const [startWeight, setStartWeight] = useState('');
  const [endWeight, setEndWeight] = useState('');
  const [notes, setNotes] = useState('');

  // Calculate usage
  const calculatedUsage = startWeight && endWeight 
    ? (parseFloat(startWeight) - parseFloat(endWeight)).toFixed(2)
    : '0.00';

  // Get stock balances
  const { data: stockBalances } = useQuery({
    queryKey: ['stock-balances'],
    queryFn: async () => {
      const response = await fetch(`${API_URL}/api/stock/balances`);
      if (!response.ok) return [];
      return response.json();
    },
  });

  const casingStock = stockBalances?.find((b: any) => b.nomenclature_id === casingId)?.quantity || 0;

  // Get batch details
  const { data: batch, isLoading: batchLoading } = useQuery({
    queryKey: ['batch', batchId],
    queryFn: async () => {
      const response = await fetch(`${API_URL}/api/production/batches/${batchId}`);
      if (!response.ok) throw new Error('Failed to fetch batch');
      return response.json();
    },
  });

  // Casing stock is already calculated above on line 57

  // Get casing nomenclature details
  const { data: nomenclature } = useQuery({
    queryKey: ['nomenclature'],
    queryFn: async () => {
      const response = await fetch(`${API_URL}/api/nomenclature`);
      if (!response.ok) throw new Error('Failed to fetch nomenclature');
      return response.json();
    },
  });

  const casings = nomenclature?.filter((item: any) => 
    item.name.toLowerCase().includes('кишка') || 
    item.name.toLowerCase().includes('оболонка')
  ) || [];

  const processStuffingMutation = useMutation({
    mutationFn: async (stuffingData: any) => {
      const response = await fetch(`${API_URL}/api/production/batches/${batchId}/stuff`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(stuffingData),
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to process stuffing');
      }
      return response.json();
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['batch', batchId] });
      queryClient.invalidateQueries({ queryKey: ['batch-operations', batchId] });
      queryClient.invalidateQueries({ queryKey: ['stock-balances'] });
      
      const usageMsg = data.casing 
        ? `\nВикористано кишки: ${data.casing.usage_kg} ${data.casing.unit}`
        : '';
      
      Alert.alert('Успіх', `Заправку виконано${usageMsg}`, [
        { text: 'OK', onPress: () => router.back() }
      ]);
    },
    onError: (error: any) => {
      Alert.alert('Помилка', error.message || 'Не вдалося виконати заправку');
    },
  });

  const handleSubmit = () => {
    const start = parseFloat(startWeight);
    const end = parseFloat(endWeight);

    if (!startWeight || isNaN(start) || start <= 0) {
      Alert.alert('Помилка', 'Введіть початкову вагу пучка кишки');
      return;
    }

    if (!endWeight || isNaN(end) || end < 0) {
      Alert.alert('Помилка', 'Введіть кінцеву вагу залишку');
      return;
    }

    if (end > start) {
      Alert.alert('Помилка', 'Кінцева вага не може бути більшою за початкову');
      return;
    }

    const usage = start - end;
    if (usage === 0) {
      Alert.alert('Помилка', 'Використано 0 кг. Перевірте введені дані.');
      return;
    }

    Alert.alert(
      'Підтвердження',
      `Буде списано ${usage.toFixed(2)} кг кишки.\n\nПродовжити?`,
      [
        { text: 'Скасувати', style: 'cancel' },
        {
          text: 'Так',
          onPress: () => {
            const stuffingData = {
              casing: {
                casing_id: casingId,
                start_weight: start,
                end_weight: end,
              },
              materials: [], // Can be extended for threads, etc.
              notes: notes || 'Заправка в кишку виконана',
              idempotency_key: `stuff-${batchId}-${Date.now()}`,
            };

            processStuffingMutation.mutate(stuffingData);
          },
        },
      ]
    );
  };

  if (batchLoading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#007AFF" />
      </View>
    );
  }

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
          <Text style={styles.title}>Заправка в кишку</Text>
        </View>

        {/* Batch Info */}
        {batch && (
          <View style={styles.infoCard}>
            <View style={styles.infoRow}>
              <Text style={styles.infoLabel}>Партія:</Text>
              <Text style={styles.infoValue}>{batch.batch_number}</Text>
            </View>
            <View style={styles.infoRow}>
              <Text style={styles.infoLabel}>Рецепт:</Text>
              <Text style={styles.infoValue}>{batch.recipe_name}</Text>
            </View>
            <View style={styles.infoRow}>
              <Text style={styles.infoLabel}>Вага партії:</Text>
              <Text style={styles.infoValue}>{batch.initial_weight} кг</Text>
            </View>
          </View>
        )}

        {/* Casing Selection */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Тип кишки</Text>
          <View style={styles.casingSelector}>
            {casings.map((casing: any) => (
              <TouchableOpacity
                key={casing.id}
                style={[
                  styles.casingOption,
                  casingId === casing.id && styles.casingOptionSelected,
                ]}
                onPress={() => setCasingId(casing.id)}
              >
                <Text
                  style={[
                    styles.casingOptionText,
                    casingId === casing.id && styles.casingOptionTextSelected,
                  ]}
                >
                  {casing.name}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>

        {/* Stock Balance */}
        {casingStock && (
          <View style={styles.stockCard}>
            <MaterialCommunityIcons name="warehouse" size={20} color="#666" />
            <Text style={styles.stockText}>
              На складі: <Text style={styles.stockValue}>{casingStock} кг</Text>
            </Text>
          </View>
        )}

        {/* Weight Input Section */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Облік ваги кишки</Text>
          <Text style={styles.instruction}>
            1. Зважте пучок кишки перед використанням{'\n'}
            2. Після набивання зважте залишок{'\n'}
            3. Система автоматично розрахує витрату
          </Text>

          {/* Start Weight */}
          <View style={styles.inputGroup}>
            <Text style={styles.label}>Початкова вага пучка (кг) *</Text>
            <View style={styles.inputWrapper}>
              <MaterialCommunityIcons name="weight" size={20} color="#666" />
              <TextInput
                style={styles.input}
                value={startWeight}
                onChangeText={setStartWeight}
                placeholder="напр. 1.8"
                keyboardType="decimal-pad"
              />
              <Text style={styles.unit}>кг</Text>
            </View>
          </View>

          {/* End Weight */}
          <View style={styles.inputGroup}>
            <Text style={styles.label}>Вага залишку після використання (кг) *</Text>
            <View style={styles.inputWrapper}>
              <MaterialCommunityIcons name="weight" size={20} color="#666" />
              <TextInput
                style={styles.input}
                value={endWeight}
                onChangeText={setEndWeight}
                placeholder="напр. 0.3"
                keyboardType="decimal-pad"
              />
              <Text style={styles.unit}>кг</Text>
            </View>
          </View>

          {/* Calculated Usage */}
          {startWeight && endWeight && (
            <View style={styles.calculationCard}>
              <View style={styles.calculationRow}>
                <Text style={styles.calculationLabel}>Використано:</Text>
                <Text style={styles.calculationValue}>
                  {calculatedUsage} кг
                </Text>
              </View>
              {parseFloat(calculatedUsage) > 0 && casingStock && (
                <View style={styles.calculationRow}>
                  <Text style={styles.calculationLabel}>Залишиться на складі:</Text>
                  <Text style={styles.calculationValue}>
                    {(casingStock.balance - parseFloat(calculatedUsage)).toFixed(2)} кг
                  </Text>
                </View>
              )}
            </View>
          )}
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
            processStuffingMutation.isPending && styles.submitButtonDisabled,
          ]}
          onPress={handleSubmit}
          disabled={processStuffingMutation.isPending}
        >
          {processStuffingMutation.isPending ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <>
              <MaterialCommunityIcons name="check-circle" size={20} color="#fff" />
              <Text style={styles.submitButtonText}>Підтвердити заправку</Text>
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
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  content: {
    padding: 16,
    paddingBottom: 32,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 16,
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
  infoCard: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
  },
  infoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  infoLabel: {
    fontSize: 14,
    color: '#666',
  },
  infoValue: {
    fontSize: 14,
    fontWeight: '600',
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
  instruction: {
    fontSize: 14,
    color: '#666',
    backgroundColor: '#E3F2FD',
    padding: 12,
    borderRadius: 8,
    marginBottom: 16,
    lineHeight: 20,
  },
  casingSelector: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  casingOption: {
    paddingVertical: 8,
    paddingHorizontal: 16,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: '#ddd',
    backgroundColor: '#fff',
  },
  casingOptionSelected: {
    backgroundColor: '#007AFF',
    borderColor: '#007AFF',
  },
  casingOptionText: {
    fontSize: 14,
    color: '#333',
  },
  casingOptionTextSelected: {
    color: '#fff',
    fontWeight: '600',
  },
  stockCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#FFF3CD',
    padding: 12,
    borderRadius: 8,
    marginBottom: 16,
    gap: 8,
  },
  stockText: {
    fontSize: 14,
    color: '#666',
  },
  stockValue: {
    fontWeight: 'bold',
    color: '#333',
  },
  inputGroup: {
    marginBottom: 16,
  },
  label: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
    marginBottom: 8,
  },
  inputWrapper: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fff',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#ddd',
    paddingHorizontal: 12,
    gap: 8,
  },
  input: {
    flex: 1,
    paddingVertical: 12,
    fontSize: 16,
    color: '#333',
  },
  unit: {
    fontSize: 14,
    color: '#999',
    fontWeight: '600',
  },
  calculationCard: {
    backgroundColor: '#E8F5E9',
    padding: 16,
    borderRadius: 8,
    marginTop: 8,
  },
  calculationRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 4,
  },
  calculationLabel: {
    fontSize: 14,
    color: '#666',
  },
  calculationValue: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#2E7D32',
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
