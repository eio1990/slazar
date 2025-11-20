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

export default function MassageFormScreen() {
  const router = useRouter();
  const { batchId, stepId, currentWeight } = useLocalSearchParams();
  const queryClient = useQueryClient();

  const [waterQuantity, setWaterQuantity] = useState('');
  const [notes, setNotes] = useState('');

  // Default: 15л на 100кг
  const recommendedWater = currentWeight 
    ? ((parseFloat(currentWeight as string) / 100) * 15).toFixed(1)
    : '0';

  const { data: batch, isLoading: batchLoading } = useQuery({
    queryKey: ['batch', batchId],
    queryFn: async () => {
      const response = await fetch(`${API_URL}/api/production/batches/${batchId}`);
      if (!response.ok) throw new Error('Failed to fetch batch');
      return response.json();
    },
  });

  // Get stock balances (water is not tracked, but we load for consistency)
  const { data: stockBalances } = useQuery({
    queryKey: ['stock-balances'],
    queryFn: async () => {
      const response = await fetch(`${API_URL}/api/stock/balances`);
      if (!response.ok) return [];
      return response.json();
    },
  });

  const processMassageMutation = useMutation({
    mutationFn: async (massageData: any) => {
      const response = await fetch(`${API_URL}/api/production/batches/${batchId}/massage`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(massageData),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to process massage');
      }
      return response.json();
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['batch', batchId] });
      Alert.alert('Успіх', `Масаж виконано\n\nВикористано води: ${parseFloat(waterQuantity).toFixed(1)} л`, [
        { text: 'OK', onPress: () => router.back() }
      ]);
    },
    onError: (error: any) => {
      Alert.alert('Помилка', error.message);
    },
  });

  const handleSubmit = () => {
    const water = parseFloat(waterQuantity);

    if (!waterQuantity || isNaN(water) || water <= 0) {
      Alert.alert('Помилка', 'Введіть коректну кількість води');
      return;
    }

    Alert.alert(
      'Підтвердження',
      `Буде використано ${water.toFixed(1)} л води\n\nПродовжити?`,
      [
        { text: 'Скасувати', style: 'cancel' },
        {
          text: 'Так',
          onPress: () => {
            const massageData = {
              water_quantity: water,
              notes: notes || 'Масаж з водою виконано',
              idempotency_key: `massage-${batchId}-${Date.now()}`,
            };
            processMassageMutation.mutate(massageData);
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
          <Text style={styles.title}>Масажер з водою</Text>
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
          <Text style={styles.sectionTitle}>Масажування з водою</Text>
          <Text style={styles.instruction}>
            Стандартна норма: 15 л на 100 кг м'яса\nМасажування з водою покращує консистенцію
          </Text>

          <View style={styles.recommendedCard}>
            <MaterialCommunityIcons name="water" size={20} color="#2196F3" />
            <View style={styles.recommendedText}>
              <Text style={styles.recommendedLabel}>Рекомендовано:</Text>
              <Text style={styles.recommendedValue}>{recommendedWater} л води</Text>
            </View>
          </View>

          <View style={styles.inputGroup}>
            <Text style={styles.label}>Фактична кількість води (л) *</Text>
            <View style={styles.inputWrapper}>
              <MaterialCommunityIcons name="water" size={20} color="#666" />
              <TextInput
                style={styles.input}
                value={waterQuantity}
                onChangeText={setWaterQuantity}
                placeholder={recommendedWater}
                keyboardType="decimal-pad"
              />
              <Text style={styles.unit}>л</Text>
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
            processMassageMutation.isPending && styles.submitButtonDisabled,
          ]}
          onPress={handleSubmit}
          disabled={processMassageMutation.isPending}
        >
          {processMassageMutation.isPending ? (
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
  recommendedCard: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#E1F5FE', padding: 12, borderRadius: 8, marginBottom: 16, gap: 12 },
  recommendedText: { flex: 1 },
  recommendedLabel: { fontSize: 12, color: '#01579B', fontWeight: '600' },
  recommendedValue: { fontSize: 16, color: '#01579B', fontWeight: 'bold', marginTop: 2 },
  inputGroup: { marginBottom: 16 },
  label: { fontSize: 14, fontWeight: '600', color: '#333', marginBottom: 8 },
  inputWrapper: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#fff', borderRadius: 8, borderWidth: 1, borderColor: '#ddd', paddingHorizontal: 12, gap: 8 },
  input: { flex: 1, paddingVertical: 12, fontSize: 16, color: '#333' },
  unit: { fontSize: 14, color: '#999', fontWeight: '600' },
  textArea: { backgroundColor: '#fff', borderRadius: 8, borderWidth: 1, borderColor: '#ddd', padding: 12, fontSize: 16, color: '#333', minHeight: 80, textAlignVertical: 'top' },
  submitButton: { backgroundColor: '#007AFF', borderRadius: 12, padding: 16, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8, marginTop: 8 },
  submitButtonDisabled: { backgroundColor: '#ccc' },
  submitButtonText: { color: '#fff', fontSize: 16, fontWeight: '600' },
});
