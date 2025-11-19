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
import { useRouter, useLocalSearchParams } from 'expo-router';
import { useQuery } from '@tanstack/react-query';

const API_URL = process.env.EXPO_PUBLIC_BACKEND_URL || 'http://localhost:8001';

interface OutputInput {
  output_nomenclature_id: number;
  output_name: string;
  expected_weight: number;
  actual_weight: string;
  notes: string;
}

export default function CompleteButcheryFormScreen() {
  const router = useRouter();
  const { operationId } = useLocalSearchParams();
  const [outputs, setOutputs] = useState<OutputInput[]>([]);
  const [generalNotes, setGeneralNotes] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ['butchery-operation-complete', operationId],
    queryFn: async () => {
      const response = await fetch(`${API_URL}/api/butchery/operations/${operationId}`);
      if (!response.ok) throw new Error('Не вдалося завантажити операцію');
      const result = await response.json();

      // Ініціалізувати поля з очікуваними виходами
      const initialOutputs = result.expected_outputs.map((output: any) => ({
        output_nomenclature_id: output.output_nomenclature_id,
        output_name: output.output_name,
        expected_weight: output.expected_weight,
        actual_weight: '',
        notes: '',
      }));
      setOutputs(initialOutputs);

      return result;
    },
  });

  const updateOutputWeight = (index: number, value: string) => {
    const updated = [...outputs];
    updated[index].actual_weight = value;
    setOutputs(updated);
  };

  const updateOutputNotes = (index: number, value: string) => {
    const updated = [...outputs];
    updated[index].notes = value;
    setOutputs(updated);
  };

  const fillWithExpected = (index: number) => {
    const updated = [...outputs];
    updated[index].actual_weight = updated[index].expected_weight.toFixed(2);
    setOutputs(updated);
  };

  const getTotalActualWeight = () => {
    return outputs.reduce((sum, output) => {
      const weight = parseFloat(output.actual_weight);
      return sum + (isNaN(weight) ? 0 : weight);
    }, 0);
  };

  const handleComplete = async () => {
    // Валідація
    const invalidOutputs = outputs.filter((output) => {
      const weight = parseFloat(output.actual_weight);
      return isNaN(weight) || weight < 0;
    });

    if (invalidOutputs.length > 0) {
      Alert.alert('Помилка', 'Введіть коректну вагу для всіх виходів (≥ 0)');
      return;
    }

    const totalActual = getTotalActualWeight();
    const inputWeight = data.operation.input_weight;

    if (totalActual > inputWeight * 1.05) {
      Alert.alert(
        'Увага',
        `Сума виходів (${totalActual.toFixed(2)} кг) перевищує вхід (${inputWeight} кг) більше ніж на 5%.\n\nПродовжити?`,
        [
          { text: 'Скасувати', style: 'cancel' },
          { text: 'Продовжити', onPress: () => submitCompletion() },
        ]
      );
    } else {
      submitCompletion();
    }
  };

  const submitCompletion = async () => {
    setIsSubmitting(true);
    try {
      const completionData = {
        outputs: outputs.map((output) => ({
          output_nomenclature_id: output.output_nomenclature_id,
          actual_weight: parseFloat(output.actual_weight),
          notes: output.notes || undefined,
        })),
        notes: generalNotes || undefined,
      };

      const response = await fetch(
        `${API_URL}/api/butchery/operations/${operationId}/complete`,
        {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(completionData),
        }
      );

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Помилка завершення розділки');
      }

      const result = await response.json();

      Alert.alert('Успіх', result.message, [
        {
          text: 'OK',
          onPress: () => router.replace(`/butchery/${operationId}` as any),
        },
      ]);
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

  if (!data) {
    return (
      <View style={styles.errorContainer}>
        <Text style={styles.errorText}>Операцію не знайдено</Text>
      </View>
    );
  }

  const totalExpected = data.expected_outputs.reduce(
    (sum: number, out: any) => sum + out.expected_weight,
    0
  );
  const totalActual = getTotalActualWeight();

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
          <MaterialCommunityIcons name="arrow-left" size={24} color="#007AFF" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Завершення розділки</Text>
      </View>

      <ScrollView style={styles.content}>
        {/* Operation info */}
        <View style={styles.infoCard}>
          <Text style={styles.operationNumber}>{data.operation.operation_number}</Text>
          <Text style={styles.recipeName}>{data.operation.recipe_name}</Text>
          <View style={styles.weightInfo}>
            <View style={styles.weightItem}>
              <Text style={styles.weightLabel}>Вхід:</Text>
              <Text style={styles.weightValue}>{data.operation.input_weight} кг</Text>
            </View>
            <View style={styles.weightItem}>
              <Text style={styles.weightLabel}>Очікувано:</Text>
              <Text style={styles.weightValue}>{totalExpected.toFixed(2)} кг</Text>
            </View>
          </View>
        </View>

        {/* Output inputs */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Фактичні виходи</Text>
          {outputs.map((output, index) => (
            <View key={index} style={styles.outputCard}>
              <View style={styles.outputHeader}>
                <Text style={styles.outputName}>{output.output_name}</Text>
                <TouchableOpacity
                  style={styles.fillButton}
                  onPress={() => fillWithExpected(index)}
                >
                  <MaterialCommunityIcons name="auto-fix" size={16} color="#007AFF" />
                  <Text style={styles.fillButtonText}>Заповнити</Text>
                </TouchableOpacity>
              </View>

              <View style={styles.expectedRow}>
                <Text style={styles.expectedLabel}>Очікувано:</Text>
                <Text style={styles.expectedValue}>{output.expected_weight.toFixed(2)} кг</Text>
              </View>

              <View style={styles.inputRow}>
                <Text style={styles.inputLabel}>Фактична вага, кг</Text>
                <TextInput
                  style={styles.input}
                  value={output.actual_weight}
                  onChangeText={(value) => updateOutputWeight(index, value)}
                  keyboardType="decimal-pad"
                  placeholder="0.00"
                  placeholderTextColor="#999"
                />
              </View>

              {output.actual_weight && (
                <View style={styles.differenceRow}>
                  <Text style={styles.differenceLabel}>Різниця:</Text>
                  <Text
                    style={[
                      styles.differenceValue,
                      parseFloat(output.actual_weight) >= output.expected_weight
                        ? styles.differencePositive
                        : styles.differenceNegative,
                    ]}
                  >
                    {parseFloat(output.actual_weight) >= output.expected_weight ? '+' : ''}
                    {(parseFloat(output.actual_weight) - output.expected_weight).toFixed(2)} кг
                  </Text>
                </View>
              )}

              <TextInput
                style={styles.notesInput}
                value={output.notes}
                onChangeText={(value) => updateOutputNotes(index, value)}
                placeholder="Примітки (опціонально)"
                placeholderTextColor="#999"
              />
            </View>
          ))}
        </View>

        {/* Total summary */}
        <View style={styles.summaryCard}>
          <View style={styles.summaryRow}>
            <Text style={styles.summaryLabel}>Загальна фактична вага:</Text>
            <Text style={styles.summaryValue}>{totalActual.toFixed(2)} кг</Text>
          </View>
          <View style={styles.summaryRow}>
            <Text style={styles.summaryLabel}>Загальна різниця:</Text>
            <Text
              style={[
                styles.summaryValue,
                totalActual >= totalExpected ? styles.differencePositive : styles.differenceNegative,
              ]}
            >
              {totalActual >= totalExpected ? '+' : ''}
              {(totalActual - totalExpected).toFixed(2)} кг
            </Text>
          </View>
        </View>

        {/* General notes */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Загальні примітки</Text>
          <View style={styles.inputCard}>
            <TextInput
              style={[styles.input, styles.textArea]}
              value={generalNotes}
              onChangeText={setGeneralNotes}
              placeholder="Додаткова інформація про розділку..."
              placeholderTextColor="#999"
              multiline
              numberOfLines={4}
            />
          </View>
        </View>

        {/* Submit button */}
        <View style={styles.buttonContainer}>
          <TouchableOpacity
            style={[styles.submitButton, isSubmitting && styles.submitButtonDisabled]}
            onPress={handleComplete}
            disabled={isSubmitting}
          >
            {isSubmitting ? (
              <ActivityIndicator size="small" color="#fff" />
            ) : (
              <>
                <MaterialCommunityIcons name="check-circle" size={20} color="#fff" />
                <Text style={styles.submitButtonText}>Завершити розділку</Text>
              </>
            )}
          </TouchableOpacity>
        </View>

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
  },
  errorText: {
    fontSize: 18,
    color: '#666',
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
  content: {
    flex: 1,
  },
  infoCard: {
    backgroundColor: '#fff',
    padding: 16,
    marginBottom: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  operationNumber: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#007AFF',
    marginBottom: 4,
  },
  recipeName: {
    fontSize: 15,
    color: '#333',
    marginBottom: 12,
  },
  weightInfo: {
    flexDirection: 'row',
    gap: 24,
  },
  weightItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  weightLabel: {
    fontSize: 14,
    color: '#666',
  },
  weightValue: {
    fontSize: 16,
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
  outputCard: {
    backgroundColor: '#fff',
    padding: 16,
    borderRadius: 12,
    marginBottom: 12,
    elevation: 1,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 1,
  },
  outputHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  outputName: {
    fontSize: 15,
    fontWeight: '600',
    color: '#333',
    flex: 1,
  },
  fillButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#E3F2FD',
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderRadius: 8,
    gap: 4,
  },
  fillButtonText: {
    fontSize: 12,
    color: '#007AFF',
    fontWeight: '600',
  },
  expectedRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 12,
    paddingBottom: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0',
  },
  expectedLabel: {
    fontSize: 13,
    color: '#999',
  },
  expectedValue: {
    fontSize: 14,
    fontWeight: '600',
    color: '#666',
  },
  inputRow: {
    marginBottom: 8,
  },
  inputLabel: {
    fontSize: 13,
    fontWeight: '600',
    color: '#333',
    marginBottom: 6,
  },
  input: {
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 8,
    padding: 12,
    fontSize: 16,
    color: '#333',
    backgroundColor: '#fff',
  },
  differenceRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 4,
    marginBottom: 8,
  },
  differenceLabel: {
    fontSize: 12,
    color: '#999',
  },
  differenceValue: {
    fontSize: 14,
    fontWeight: '600',
  },
  differencePositive: {
    color: '#4CAF50',
  },
  differenceNegative: {
    color: '#f44336',
  },
  notesInput: {
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 8,
    padding: 10,
    fontSize: 14,
    color: '#333',
    backgroundColor: '#fafafa',
  },
  summaryCard: {
    backgroundColor: '#FFF9E6',
    marginHorizontal: 16,
    marginTop: 8,
    padding: 16,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#FFE082',
  },
  summaryRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  summaryLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#F57C00',
  },
  summaryValue: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333',
  },
  inputCard: {
    backgroundColor: '#fff',
    padding: 16,
    borderRadius: 12,
  },
  textArea: {
    height: 100,
    textAlignVertical: 'top',
  },
  buttonContainer: {
    paddingHorizontal: 16,
    marginTop: 24,
  },
  submitButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#4CAF50',
    padding: 16,
    borderRadius: 12,
    gap: 8,
  },
  submitButtonDisabled: {
    backgroundColor: '#999',
  },
  submitButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
});
