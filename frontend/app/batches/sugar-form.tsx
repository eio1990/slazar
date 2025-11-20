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

const API_URL = process.env.EXPO_PUBLIC_BACKEND_URL || 'http://localhost:8001';

export default function SugarFormScreen() {
  const router = useRouter();
  const { batchId, stepId, currentWeight } = useLocalSearchParams();
  const queryClient = useQueryClient();

  const [sugarQuantity, setSugarQuantity] = useState('');
  const [notes, setNotes] = useState('');

  // Default: 20г на кг (2% від ваги)
  const recommendedSugar = currentWeight ? (parseFloat(currentWeight as string) * 0.02).toFixed(2) : '0';

  const { data: batch, isLoading: batchLoading } = useQuery({
    queryKey: ['batch', batchId],
    queryFn: async () => {
      const response = await fetch(`${API_URL}/api/production/batches/${batchId}`);
      if (!response.ok) throw new Error('Failed to fetch batch');
      return response.json();
    },
  });

  // Get stock balances (Sugar ID = 29)
  const { data: stockBalances } = useQuery({
    queryKey: ['stock-balances'],
    queryFn: async () => {
      const response = await fetch(`${API_URL}/api/stock/balances`);
      if (!response.ok) return [];
      return response.json();
    },
  });

  const sugarStock = stockBalances?.find((b: any) => b.nomenclature_id === 29)?.quantity || 0;

  const processSugarMutation = useMutation({
    mutationFn: async (sugarData: any) => {
      const response = await fetch(`${API_URL}/api/production/batches/${batchId}/sugar`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(sugarData),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to process sugar');
      }
      return response.json();
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['batch', batchId] });
      Alert.alert('Успіх', `Цукрування виконано\n\nВикористано цукру: ${parseFloat(sugarQuantity).toFixed(2)} кг`, [
        { text: 'OK', onPress: () => router.back() }
      ]);
    },
    onError: (error: any) => {
      Alert.alert('Помилка', error.message);
    },
  });

  const handleSubmit = () => {
    const sugar = parseFloat(sugarQuantity);

    if (!sugarQuantity || isNaN(sugar) || sugar <= 0) {
      Alert.alert('Помилка', 'Введіть коректну кількість цукру');
      return;
    }

    Alert.alert(
      'Підтвердження',
      `Буде використано ${sugar.toFixed(2)} кг цукру\n\nПродовжити?`,
      [
        { text: 'Скасувати', style: 'cancel' },
        {
          text: 'Так',
          onPress: () => {
            const sugarData = {
              sugar_quantity: sugar,
              notes: notes || 'Цукрування виконано',
              idempotency_key: `sugar-${batchId}-${Date.now()}`,
            };
            processSugarMutation.mutate(sugarData);
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
        <View style={styles.header}>
          <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
            <MaterialCommunityIcons name="arrow-left" size={24} color="#007AFF" />
          </TouchableOpacity>
          <Text style={styles.title}>Масажер з цукром</Text>
        </View>

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
              <Text style={styles.infoLabel}>Поточна вага:</Text>
              <Text style={styles.infoValue}>{currentWeight} кг</Text>
            </View>
          </View>
        )}

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Цукрування</Text>
          <Text style={styles.instruction}>
            Стандартна норма: 20 г на кг м'яса (2%)\nМасажування з цукром покращує текстуру
          </Text>

          <View style={styles.inputGroup}>
            <View style={styles.labelRow}>
              <Text style={styles.label}>Фактична кількість цукру (кг) *</Text>
              <Text style={styles.recommendedLabel}>Рекомендована вага: {recommendedSugar} кг</Text>
            </View>
            <View style={styles.inputWrapper}>
              <MaterialCommunityIcons name="cube-outline" size={20} color="#666" />
              <TextInput
                style={styles.input}
                value={sugarQuantity}
                onChangeText={setSugarQuantity}
                placeholder={sugarStock > 0 ? `На складі: ${sugarStock.toFixed(2)} кг` : "Введіть кількість"}
                placeholderTextColor="#999"
                keyboardType="decimal-pad"
              />
              <Text style={styles.unit}>кг</Text>
            </View>
          </View>
        </View>

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

        <TouchableOpacity
          style={[
            styles.submitButton,
            processSugarMutation.isPending && styles.submitButtonDisabled,
          ]}
          onPress={handleSubmit}
          disabled={processSugarMutation.isPending}
        >
          {processSugarMutation.isPending ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <>
              <MaterialCommunityIcons name="check-circle" size={20} color="#fff" />
              <Text style={styles.submitButtonText}>Підтвердити</Text>
            </>
          )}
        </TouchableOpacity>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f5f5f5' },
  loadingContainer: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  content: { padding: 16, paddingBottom: 32 },
  header: { flexDirection: 'row', alignItems: 'center', marginBottom: 16 },
  backButton: { marginRight: 12, padding: 4 },
  title: { fontSize: 24, fontWeight: 'bold', color: '#333' },
  infoCard: { backgroundColor: '#fff', borderRadius: 12, padding: 16, marginBottom: 16, elevation: 2, shadowColor: '#000', shadowOffset: { width: 0, height: 1 }, shadowOpacity: 0.1, shadowRadius: 2 },
  infoRow: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 8 },
  infoLabel: { fontSize: 14, color: '#666' },
  infoValue: { fontSize: 14, fontWeight: '600', color: '#333' },
  section: { marginBottom: 24 },
  sectionTitle: { fontSize: 18, fontWeight: '600', color: '#333', marginBottom: 12 },
  instruction: { fontSize: 14, color: '#666', backgroundColor: '#E3F2FD', padding: 12, borderRadius: 8, marginBottom: 16, lineHeight: 20 },
  recommendedCard: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#FFF3CD', padding: 12, borderRadius: 8, marginBottom: 16, gap: 12 },
  recommendedText: { flex: 1 },
  recommendedLabel: { fontSize: 12, color: '#856404', fontWeight: '600' },
  recommendedValue: { fontSize: 16, color: '#856404', fontWeight: 'bold', marginTop: 2 },
  inputGroup: { marginBottom: 16 },
  labelRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 },
  label: { fontSize: 14, fontWeight: '600', color: '#333' },
  recommendedLabel: { fontSize: 14, fontWeight: '600', color: '#f44336' },
  inputWrapper: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#fff', borderRadius: 8, borderWidth: 1, borderColor: '#ddd', paddingHorizontal: 12, gap: 8 },
  input: { flex: 1, paddingVertical: 12, fontSize: 16, color: '#333' },
  unit: { fontSize: 14, color: '#999', fontWeight: '600' },
  textArea: { backgroundColor: '#fff', borderRadius: 8, borderWidth: 1, borderColor: '#ddd', padding: 12, fontSize: 16, color: '#333', minHeight: 80, textAlignVertical: 'top' },
  submitButton: { backgroundColor: '#007AFF', borderRadius: 12, padding: 16, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8, marginTop: 8 },
  submitButtonDisabled: { backgroundColor: '#ccc' },
  submitButtonText: { color: '#fff', fontSize: 16, fontWeight: '600' },
});
