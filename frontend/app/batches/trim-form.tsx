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
import { useRouter, useLocalSearchParams } from 'expo-router';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

const API_URL = process.env.EXPO_PUBLIC_BACKEND_URL || 'http://85.238.112.232:8001';

export default function TrimFormScreen() {
  const router = useRouter();
  const { batchId, stepId, initialWeight } = useLocalSearchParams();
  const queryClient = useQueryClient();

  const [trimWeight, setTrimWeight] = useState('');
  const [notes, setNotes] = useState('');

  // Get batch details
  const { data: batch, isLoading: batchLoading } = useQuery({
    queryKey: ['batch', batchId],
    queryFn: async () => {
      const response = await fetch(`${API_URL}/api/production/batches/${batchId}`);
      if (!response.ok) throw new Error('Failed to fetch batch');
      return response.json();
    },
  });

  // Process trim mutation
  const processTrimMutation = useMutation({
    mutationFn: async (trimData: any) => {
      const response = await fetch(`${API_URL}/api/production/batches/${batchId}/operations`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(trimData),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to process trim');
      }
      return response.json();
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['batch', batchId] });
      queryClient.invalidateQueries({ queryKey: ['batch-operations', batchId] });

      Alert.alert('Успіх', `Обрізку виконано\n\nОбрізано: ${parseFloat(trimWeight).toFixed(2)} кг`, [
        { text: 'OK', onPress: () => router.push('/(tabs)/production' as any) }
      ]);
    },
    onError: (error: any) => {
      Alert.alert('Помилка', error.message || 'Не вдалося виконати обрізку');
    },
  });

  const handleSubmit = () => {
    const trim = parseFloat(trimWeight);
    const initial = parseFloat(initialWeight as string);

    if (!trimWeight || isNaN(trim) || trim < 0) {
      Alert.alert('Помилка', 'Введіть коректну вагу обрізок');
      return;
    }

    if (trim > initial) {
      Alert.alert('Помилка', 'Вага обрізок не може перевищувати початкову вагу');
      return;
    }

    const weightAfter = initial - trim;

    Alert.alert(
      'Підтвердження',
      `Обрізки: ${trim.toFixed(2)} кг\nЗалишиться: ${weightAfter.toFixed(2)} кг\n\nПродовжити?`,
      [
        { text: 'Скасувати', style: 'cancel' },
        {
          text: 'Так',
          onPress: () => {
            const trimData = {
              step_id: parseInt(stepId as string),
              operation_type: 'trim',
              weight_before: initial,
              weight_after: weightAfter,
              parameters: {
                trim_waste: trim
              },
              notes: notes || 'Обрізка виконана',
              idempotency_key: `trim-${batchId}-${Date.now()}`,
            };

            processTrimMutation.mutate(trimData);
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

  const initial = parseFloat(initialWeight as string);
  const trim = parseFloat(trimWeight);
  const remaining = !isNaN(trim) ? initial - trim : initial;
  const trimPercent = !isNaN(trim) ? (trim / initial * 100).toFixed(1) : '0.0';

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      style={styles.container}
    >
      <ScrollView style={styles.container} contentContainerStyle={styles.content}>
        {/* Header */}
        <View style={styles.header}>
          <TouchableOpacity onPress={() => router.push('/(tabs)/production' as any)} style={styles.backButton}>
            <MaterialCommunityIcons name="arrow-left" size={24} color="#007AFF" />
          </TouchableOpacity>
          <Text style={styles.title}>Обрізка та підготовка</Text>
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
              <Text style={styles.infoLabel}>Початкова вага:</Text>
              <Text style={styles.infoValue}>{initial.toFixed(2)} кг</Text>
            </View>
          </View>
        )}

        {/* Trim Input */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Обрізка</Text>
          <Text style={styles.instruction}>
            Введіть вагу обрізаного м'яса (жир, плівки, сухожилля)
          </Text>

          <View style={styles.inputGroup}>
            <Text style={styles.label}>Вага обрізок (кг) *</Text>
            <View style={styles.inputWrapper}>
              <MaterialCommunityIcons name="weight" size={20} color="#666" />
              <TextInput
                style={styles.input}
                value={trimWeight}
                onChangeText={setTrimWeight}
                placeholder="напр. 5.0"
                keyboardType="decimal-pad"
              />
              <Text style={styles.unit}>кг</Text>
            </View>
          </View>

          {/* Calculation Card */}
          {trimWeight && !isNaN(trim) && (
            <View style={styles.calculationCard}>
              <View style={styles.calculationRow}>
                <Text style={styles.calculationLabel}>Обрізано:</Text>
                <Text style={styles.calculationValue}>
                  {trim.toFixed(2)} кг ({trimPercent}%)
                </Text>
              </View>
              <View style={styles.calculationRow}>
                <Text style={styles.calculationLabel}>Залишиться:</Text>
                <Text style={[styles.calculationValue, styles.highlight]}>
                  {remaining.toFixed(2)} кг
                </Text>
              </View>
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
            processTrimMutation.isPending && styles.submitButtonDisabled,
          ]}
          onPress={handleSubmit}
          disabled={processTrimMutation.isPending}
        >
          {processTrimMutation.isPending ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <>
              <MaterialCommunityIcons name="scissors-cutting" size={20} color="#fff" />
              <Text style={styles.submitButtonText}>Підтвердити обрізку</Text>
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
  highlight: {
    fontSize: 18,
    color: '#1976D2',
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
