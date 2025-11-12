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

export default function SaltingFormScreen() {
  const router = useRouter();
  const { batchId, stepId, saltPer100kg, waterPer100kg, initialWeight } = useLocalSearchParams();
  const queryClient = useQueryClient();
  
  const saltPer100 = parseFloat(saltPer100kg as string) || 20;
  const waterPer100 = parseFloat(waterPer100kg as string) || 60;
  const weight = parseFloat(initialWeight as string) || 100;
  
  // Calculate recommended quantities
  const recommendedSalt = (weight / 100) * saltPer100;
  const recommendedWater = (weight / 100) * waterPer100;
  
  const [saltQuantity, setSaltQuantity] = useState(recommendedSalt.toFixed(2));
  const [waterQuantity, setWaterQuantity] = useState(recommendedWater.toFixed(2));
  const [notes, setNotes] = useState('');

  // Get batch details
  const { data: batch } = useQuery({
    queryKey: ['batch', batchId],
    queryFn: async () => {
      const response = await fetch(`${API_URL}/api/production/batches/${batchId}`);
      if (!response.ok) throw new Error('Failed to fetch batch');
      return response.json();
    },
  });

  const processSaltingMutation = useMutation({
    mutationFn: async (saltingData: any) => {
      const response = await fetch(`${API_URL}/api/production/batches/${batchId}/salting`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(saltingData),
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to process salting');
      }
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['batch', batchId] });
      queryClient.invalidateQueries({ queryKey: ['batch-operations', batchId] });
      Alert.alert('Успіх', 'Засолку виконано', [
        { text: 'OK', onPress: () => router.back() }
      ]);
    },
    onError: (error: any) => {
      Alert.alert('Помилка', error.message || 'Не вдалося виконати засолку');
    },
  });

  const handleSubmit = () => {
    const salt = parseFloat(saltQuantity);
    const water = parseFloat(waterQuantity);

    if (isNaN(salt) || salt <= 0) {
      Alert.alert('Помилка', 'Введіть коректну кількість солі');
      return;
    }

    if (isNaN(water) || water <= 0) {
      Alert.alert('Помилка', 'Введіть коректну кількість води');
      return;
    }

    Alert.alert(
      'Підтвердження',
      `Засолити партію?\n\nСіль: ${salt} кг\nВода: ${water} л\n\nЦі інгредієнти будуть списані зі складу.`,
      [
        { text: 'Скасувати', style: 'cancel' },
        {
          text: 'Підтвердити',
          onPress: () => {
            processSaltingMutation.mutate({
              salt_quantity: salt,
              water_quantity: water,
              notes: notes || undefined,
              idempotency_key: `salting-${batchId}-${Date.now()}`
            });
          }
        }
      ]
    );
  };

  return (
    <KeyboardAvoidingView 
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <ScrollView style={styles.scrollView} contentContainerStyle={styles.scrollContent}>
        {/* Header */}
        <View style={styles.header}>
          <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
            <MaterialCommunityIcons name="arrow-left" size={24} color="#333" />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>Засолка</Text>
          <View style={styles.backButton} />
        </View>

        {/* Batch Info */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Інформація про партію</Text>
          <View style={styles.infoCard}>
            <View style={styles.infoRow}>
              <Text style={styles.infoLabel}>Партія:</Text>
              <Text style={styles.infoValue}>{batch?.batch_number}</Text>
            </View>
            <View style={styles.infoRow}>
              <Text style={styles.infoLabel}>Початкова вага:</Text>
              <Text style={styles.infoValue}>{weight} кг</Text>
            </View>
          </View>
        </View>

        {/* Recommended Quantities */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Рекомендована кількість</Text>
          <View style={styles.recommendedCard}>
            <View style={styles.recommendedRow}>
              <MaterialCommunityIcons name="shaker" size={24} color="#2196F3" />
              <View style={styles.recommendedInfo}>
                <Text style={styles.recommendedLabel}>Сіль</Text>
                <Text style={styles.recommendedValue}>{recommendedSalt.toFixed(2)} кг</Text>
                <Text style={styles.recommendedNote}>({saltPer100} кг на 100 кг сировини)</Text>
              </View>
            </View>
            <View style={styles.divider} />
            <View style={styles.recommendedRow}>
              <MaterialCommunityIcons name="water" size={24} color="#03A9F4" />
              <View style={styles.recommendedInfo}>
                <Text style={styles.recommendedLabel}>Вода</Text>
                <Text style={styles.recommendedValue}>{recommendedWater.toFixed(2)} л</Text>
                <Text style={styles.recommendedNote}>({waterPer100} л на 100 кг сировини)</Text>
              </View>
            </View>
          </View>
        </View>

        {/* Input Form */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Фактична кількість</Text>
          
          <View style={styles.formCard}>
            <Text style={styles.label}>Сіль (кг) *</Text>
            <TextInput
              style={styles.input}
              value={saltQuantity}
              onChangeText={setSaltQuantity}
              keyboardType="decimal-pad"
              placeholder="Введіть кількість солі"
            />

            <Text style={[styles.label, { marginTop: 16 }]}>Вода (л) *</Text>
            <TextInput
              style={styles.input}
              value={waterQuantity}
              onChangeText={setWaterQuantity}
              keyboardType="decimal-pad"
              placeholder="Введіть кількість води"
            />

            <Text style={[styles.label, { marginTop: 16 }]}>Примітки</Text>
            <TextInput
              style={[styles.input, styles.textArea]}
              value={notes}
              onChangeText={setNotes}
              multiline
              numberOfLines={3}
              placeholder="Додаткова інформація (необов'язково)"
            />
          </View>
        </View>

        {/* Submit Button */}
        <TouchableOpacity
          style={[styles.submitButton, processSaltingMutation.isPending && styles.submitButtonDisabled]}
          onPress={handleSubmit}
          disabled={processSaltingMutation.isPending}
        >
          {processSaltingMutation.isPending ? (
            <ActivityIndicator color="#FFF" />
          ) : (
            <>
              <MaterialCommunityIcons name="check-circle" size={20} color="#FFF" />
              <Text style={styles.submitButtonText}>Виконати засолку</Text>
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
    backgroundColor: '#F5F5F5',
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    paddingBottom: 100,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    backgroundColor: '#FFF',
    borderBottomWidth: 1,
    borderBottomColor: '#E0E0E0',
  },
  backButton: {
    width: 40,
    height: 40,
    justifyContent: 'center',
    alignItems: 'center',
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: '600',
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
  infoCard: {
    backgroundColor: '#FFF',
    borderRadius: 12,
    padding: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
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
  recommendedCard: {
    backgroundColor: '#FFF',
    borderRadius: 12,
    padding: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  recommendedRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 12,
  },
  recommendedInfo: {
    marginLeft: 12,
    flex: 1,
  },
  recommendedLabel: {
    fontSize: 14,
    color: '#666',
    marginBottom: 4,
  },
  recommendedValue: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333',
    marginBottom: 2,
  },
  recommendedNote: {
    fontSize: 12,
    color: '#999',
  },
  divider: {
    height: 1,
    backgroundColor: '#E0E0E0',
    marginVertical: 8,
  },
  formCard: {
    backgroundColor: '#FFF',
    borderRadius: 12,
    padding: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  label: {
    fontSize: 14,
    fontWeight: '500',
    color: '#333',
    marginBottom: 8,
  },
  input: {
    backgroundColor: '#F8F8F8',
    borderWidth: 1,
    borderColor: '#E0E0E0',
    borderRadius: 8,
    padding: 12,
    fontSize: 16,
    color: '#333',
  },
  textArea: {
    minHeight: 80,
    textAlignVertical: 'top',
  },
  submitButton: {
    backgroundColor: '#4CAF50',
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 16,
    borderRadius: 12,
    marginHorizontal: 16,
    marginTop: 24,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.2,
    shadowRadius: 4,
    elevation: 4,
  },
  submitButtonDisabled: {
    backgroundColor: '#A5D6A7',
  },
  submitButtonText: {
    color: '#FFF',
    fontSize: 16,
    fontWeight: '600',
    marginLeft: 8,
  },
});
