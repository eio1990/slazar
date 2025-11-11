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

interface Batch {
  id: number;
  batch_number: string;
  recipe_id: number;
  recipe_name: string;
  status: string;
  current_step: number;
  started_at: string;
  completed_at?: string;
  initial_weight: number;
  final_weight?: number;
  trim_waste?: number;
  trim_returned?: boolean;
  operator_notes?: string;
}

export default function BatchDetailScreen() {
  const router = useRouter();
  const { id } = useLocalSearchParams();
  const queryClient = useQueryClient();
  
  const [finalWeight, setFinalWeight] = useState('');
  const [notes, setNotes] = useState('');

  const { data: batch, isLoading, refetch } = useQuery({
    queryKey: ['batch', id],
    queryFn: async () => {
      const response = await fetch(`${API_URL}/api/production/batches/${id}`);
      if (!response.ok) throw new Error('Failed to fetch batch');
      return response.json();
    },
  });

  const { data: recipe } = useQuery({
    queryKey: ['recipe', batch?.recipe_id],
    queryFn: async () => {
      if (!batch) return null;
      const response = await fetch(`${API_URL}/api/production/recipes/${batch.recipe_id}`);
      if (!response.ok) throw new Error('Failed to fetch recipe');
      return response.json();
    },
    enabled: !!batch,
  });

  const { data: operations = [] } = useQuery({
    queryKey: ['batch-operations', id],
    queryFn: async () => {
      const response = await fetch(`${API_URL}/api/production/batches/${id}/operations`);
      if (!response.ok) return [];
      return response.json();
    },
  });

  const completeBatchMutation = useMutation({
    mutationFn: async (data: any) => {
      const response = await fetch(`${API_URL}/api/production/batches/${id}/complete`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to complete batch');
      }
      return response.json();
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['batch', id] });
      queryClient.invalidateQueries({ queryKey: ['batches'] });
      Alert.alert(
        'Успіх',
        `Партію завершено!\n\nВихід: ${data.yield_percent}%\nОчікувалось: ${data.expected_range}`,
        [{ text: 'OK', onPress: () => refetch() }]
      );
    },
    onError: (error: any) => {
      Alert.alert('Помилка', error.message || 'Не вдалося завершити партію');
    },
  });

  const handleCompleteBatch = () => {
    if (!finalWeight || parseFloat(finalWeight) <= 0) {
      Alert.alert('Помилка', 'Введіть фінальну вагу');
      return;
    }

    Alert.alert(
      'Підтвердження',
      `Завершити партію з фінальною вагою ${finalWeight} кг?`,
      [
        { text: 'Скасувати', style: 'cancel' },
        {
          text: 'Так',
          onPress: () => {
            completeBatchMutation.mutate({
              final_weight: parseFloat(finalWeight),
              notes: notes || 'Партія завершена',
              idempotency_key: `complete-${id}-${Date.now()}`,
            });
          },
        },
      ]
    );
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('uk-UA', { 
      day: '2-digit', 
      month: '2-digit', 
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'created': return '#2196F3';
      case 'in_progress': return '#FF9800';
      case 'completed': return '#4CAF50';
      default: return '#666';
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'created': return 'Створена';
      case 'in_progress': return 'В процесі';
      case 'completed': return 'Завершена';
      default: return status;
    }
  };

  const calculateYield = () => {
    if (batch && finalWeight) {
      const yield_percent = (parseFloat(finalWeight) / batch.initial_weight) * 100;
      return yield_percent.toFixed(2);
    }
    return null;
  };

  if (isLoading || !batch) {
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator size="large" color="#4CAF50" />
      </View>
    );
  }

  const yieldPercent = calculateYield();

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity style={styles.backButton} onPress={() => router.back()}>
          <MaterialCommunityIcons name="arrow-left" size={24} color="#fff" />
        </TouchableOpacity>
        <Text style={styles.headerTitle} numberOfLines={1}>
          {batch.batch_number}
        </Text>
        <View style={styles.placeholder} />
      </View>

      <ScrollView style={styles.content}>
        {/* Batch Info */}
        <View style={styles.infoCard}>
          <View style={styles.statusRow}>
            <Text style={styles.recipeName}>{batch.recipe_name}</Text>
            <View style={[styles.statusBadge, { backgroundColor: getStatusColor(batch.status) }]}>
              <Text style={styles.statusText}>{getStatusText(batch.status)}</Text>
            </View>
          </View>

          <View style={styles.detailsContainer}>
            <View style={styles.detailRow}>
              <MaterialCommunityIcons name="weight-kilogram" size={20} color="#666" />
              <View style={styles.detailContent}>
                <Text style={styles.detailLabel}>Початкова вага</Text>
                <Text style={styles.detailValue}>{batch.initial_weight.toFixed(2)} кг</Text>
              </View>
            </View>

            {batch.trim_waste && batch.trim_waste > 0 && (
              <View style={styles.detailRow}>
                <MaterialCommunityIcons name="scissors-cutting" size={20} color="#666" />
                <View style={styles.detailContent}>
                  <Text style={styles.detailLabel}>Обрізки</Text>
                  <Text style={styles.detailValue}>
                    {batch.trim_waste.toFixed(2)} кг
                    {batch.trim_returned && ' (повернуто на склад)'}
                  </Text>
                </View>
              </View>
            )}

            {batch.final_weight && (
              <View style={styles.detailRow}>
                <MaterialCommunityIcons name="check-circle" size={20} color="#4CAF50" />
                <View style={styles.detailContent}>
                  <Text style={styles.detailLabel}>Фінальна вага</Text>
                  <Text style={[styles.detailValue, { color: '#4CAF50', fontWeight: 'bold' }]}>
                    {batch.final_weight.toFixed(2)} кг
                  </Text>
                </View>
              </View>
            )}

            <View style={styles.detailRow}>
              <MaterialCommunityIcons name="clock-start" size={20} color="#666" />
              <View style={styles.detailContent}>
                <Text style={styles.detailLabel}>Початок</Text>
                <Text style={styles.detailValue}>{formatDate(batch.started_at)}</Text>
              </View>
            </View>

            {batch.completed_at && (
              <View style={styles.detailRow}>
                <MaterialCommunityIcons name="flag-checkered" size={20} color="#4CAF50" />
                <View style={styles.detailContent}>
                  <Text style={styles.detailLabel}>Завершено</Text>
                  <Text style={styles.detailValue}>{formatDate(batch.completed_at)}</Text>
                </View>
              </View>
            )}
          </View>

          {batch.operator_notes && (
            <View style={styles.notesContainer}>
              <Text style={styles.notesLabel}>Примітки:</Text>
              <Text style={styles.notesText}>{batch.operator_notes}</Text>
            </View>
          )}
        </View>

        {/* Production Progress */}
        {recipe && batch.status !== 'completed' && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Прогрес виробництва</Text>
            
            <View style={styles.progressCard}>
              {recipe.steps.map((step: any, index: number) => {
                const isCompleted = operations.some((op: any) => op.step_id === step.id);
                const isCurrent = batch.current_step === step.step_order - 1 || 
                                 (!operations.length && index === 0);
                
                return (
                  <View key={step.id} style={styles.progressStep}>
                    <View style={styles.progressStepHeader}>
                      <View style={[
                        styles.progressStepIcon,
                        isCompleted && styles.progressStepIconCompleted,
                        isCurrent && styles.progressStepIconCurrent
                      ]}>
                        {isCompleted ? (
                          <MaterialCommunityIcons name="check" size={20} color="#fff" />
                        ) : (
                          <Text style={[
                            styles.progressStepNumber,
                            isCurrent && styles.progressStepNumberCurrent
                          ]}>
                            {step.step_order}
                          </Text>
                        )}
                      </View>
                      <View style={styles.progressStepInfo}>
                        <Text style={[
                          styles.progressStepName,
                          isCompleted && styles.progressStepNameCompleted
                        ]}>
                          {step.step_name}
                        </Text>
                        {step.duration_days > 0 && (
                          <Text style={styles.progressStepDuration}>
                            {step.duration_days} {step.duration_days === 1 ? 'день' : 'днів'}
                          </Text>
                        )}
                      </View>
                      {isCurrent && !isCompleted && (
                        <TouchableOpacity
                          style={styles.progressStepButton}
                          onPress={() => {
                            // Special handling for mix step
                            if (step.step_type === 'mix') {
                              const mixParams = step.parameters || {};
                              const mixId = mixParams.mix_id || (batch.recipe_name?.includes('конини') ? 135 : 134);
                              router.push(`/batches/mix-form?batchId=${id}&stepId=${step.id}&recipeId=${batch.recipe_id}&mixId=${mixId}` as any);
                            } else {
                              // Regular step - simple weight input
                              Alert.prompt(
                                'Завершити крок',
                                `Введіть вагу після "${step.step_name}"`,
                                [
                                  { text: 'Скасувати', style: 'cancel' },
                                  {
                                    text: 'OK',
                                    onPress: (weight) => {
                                      if (weight && parseFloat(weight) > 0) {
                                        fetch(`${API_URL}/api/production/batches/${id}/operations`, {
                                          method: 'POST',
                                          headers: { 'Content-Type': 'application/json' },
                                          body: JSON.stringify({
                                            step_id: step.id,
                                            weight_after: parseFloat(weight),
                                            notes: `Крок ${step.step_order} завершено`,
                                            idempotency_key: `step-${id}-${step.id}-${Date.now()}`,
                                          }),
                                        })
                                          .then(() => {
                                            refetch();
                                            queryClient.invalidateQueries({ queryKey: ['batch-operations', id] });
                                          })
                                          .catch((err) => Alert.alert('Помилка', 'Не вдалося додати операцію'));
                                      }
                                    },
                                  },
                                ],
                                'plain-text',
                                '',
                                'decimal-pad'
                              );
                            }
                          }}
                        >
                          <MaterialCommunityIcons name="play-circle" size={20} color="#4CAF50" />
                          <Text style={styles.progressStepButtonText}>
                            {step.step_type === 'mix' ? 'Відкрити форму' : 'Почати'}
                          </Text>
                        </TouchableOpacity>
                      )}
                      {isCompleted && (
                        <MaterialCommunityIcons name="check-circle" size={20} color="#4CAF50" />
                      )}
                    </View>
                    {index < recipe.steps.length - 1 && (
                      <View style={[
                        styles.progressStepLine,
                        isCompleted && styles.progressStepLineCompleted
                      ]} />
                    )}
                  </View>
                );
              })}
            </View>
          </View>
        )}

        {/* Complete Batch Form */}
        {batch.status !== 'completed' && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Завершити партію</Text>
            
            <View style={styles.formCard}>
              <Text style={styles.label}>Фінальна вага (кг) *</Text>
              <TextInput
                style={styles.input}
                value={finalWeight}
                onChangeText={setFinalWeight}
                keyboardType="decimal-pad"
                placeholder="Введіть фінальну вагу"
              />

              {yieldPercent && (
                <View style={styles.yieldPreview}>
                  <MaterialCommunityIcons name="chart-line" size={20} color="#4CAF50" />
                  <Text style={styles.yieldPreviewText}>
                    Вихід буде: {yieldPercent}%
                  </Text>
                </View>
              )}

              <Text style={styles.label}>Примітки</Text>
              <TextInput
                style={[styles.input, styles.textArea]}
                value={notes}
                onChangeText={setNotes}
                placeholder="Додаткові примітки (необов'язково)"
                multiline
                numberOfLines={3}
              />

              <TouchableOpacity
                style={[styles.completeButton, completeBatchMutation.isPending && styles.completeButtonDisabled]}
                onPress={handleCompleteBatch}
                disabled={completeBatchMutation.isPending}
              >
                {completeBatchMutation.isPending ? (
                  <ActivityIndicator color="#fff" />
                ) : (
                  <>
                    <MaterialCommunityIcons name="check-circle" size={20} color="#fff" />
                    <Text style={styles.completeButtonText}>Завершити партію</Text>
                  </>
                )}
              </TouchableOpacity>
            </View>
          </View>
        )}

        {batch.status === 'completed' && batch.final_weight && (
          <View style={styles.completedBanner}>
            <MaterialCommunityIcons name="check-circle" size={32} color="#4CAF50" />
            <Text style={styles.completedText}>
              Партія завершена з виходом{' '}
              {((batch.final_weight / batch.initial_weight) * 100).toFixed(2)}%
            </Text>
          </View>
        )}
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
  statusRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
    paddingBottom: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0',
  },
  recipeName: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
    flex: 1,
  },
  statusBadge: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 12,
  },
  statusText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#fff',
  },
  detailsContainer: {
    gap: 12,
  },
  detailRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
  },
  detailContent: {
    marginLeft: 12,
    flex: 1,
  },
  detailLabel: {
    fontSize: 12,
    color: '#999',
    marginBottom: 2,
  },
  detailValue: {
    fontSize: 16,
    color: '#333',
    fontWeight: '600',
  },
  notesContainer: {
    marginTop: 16,
    paddingTop: 16,
    borderTopWidth: 1,
    borderTopColor: '#f0f0f0',
  },
  notesLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#666',
    marginBottom: 4,
  },
  notesText: {
    fontSize: 14,
    color: '#333',
    lineHeight: 20,
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
  textArea: {
    height: 80,
    textAlignVertical: 'top',
  },
  yieldPreview: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 12,
    paddingHorizontal: 16,
    backgroundColor: '#E8F5E9',
    borderRadius: 8,
    marginBottom: 16,
  },
  yieldPreviewText: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#4CAF50',
    marginLeft: 8,
  },
  completeButton: {
    flexDirection: 'row',
    backgroundColor: '#4CAF50',
    paddingVertical: 14,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 8,
  },
  completeButtonDisabled: {
    opacity: 0.6,
  },
  completeButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
    marginLeft: 8,
  },
  completedBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#E8F5E9',
    marginHorizontal: 16,
    marginBottom: 24,
    padding: 20,
    borderRadius: 12,
    borderWidth: 2,
    borderColor: '#4CAF50',
  },
  completedText: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#4CAF50',
    marginLeft: 12,
    flex: 1,
  },
  progressCard: {
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
  progressStep: {
    position: 'relative',
  },
  progressStepHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  progressStepIcon: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: '#e0e0e0',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  progressStepIconCompleted: {
    backgroundColor: '#4CAF50',
  },
  progressStepIconCurrent: {
    backgroundColor: '#2196F3',
  },
  progressStepNumber: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#999',
  },
  progressStepNumberCurrent: {
    color: '#fff',
  },
  progressStepInfo: {
    flex: 1,
  },
  progressStepName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
  },
  progressStepNameCompleted: {
    color: '#4CAF50',
  },
  progressStepDuration: {
    fontSize: 12,
    color: '#999',
    marginTop: 2,
  },
  progressStepButton: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 6,
    paddingHorizontal: 12,
    backgroundColor: '#E8F5E9',
    borderRadius: 16,
  },
  progressStepButtonText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#4CAF50',
    marginLeft: 4,
  },
  progressStepLine: {
    position: 'absolute',
    left: 17,
    top: 36,
    bottom: -8,
    width: 2,
    backgroundColor: '#e0e0e0',
  },
  progressStepLineCompleted: {
    backgroundColor: '#4CAF50',
  },
});
