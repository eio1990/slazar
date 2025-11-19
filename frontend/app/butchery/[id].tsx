import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { useQuery } from '@tanstack/react-query';

const API_URL = process.env.EXPO_PUBLIC_BACKEND_URL || 'http://localhost:8001';

export default function ButcheryOperationDetailScreen() {
  const router = useRouter();
  const { id } = useLocalSearchParams();

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['butchery-operation', id],
    queryFn: async () => {
      const response = await fetch(`${API_URL}/api/butchery/operations/${id}`);
      if (!response.ok) throw new Error('Не вдалося завантажити операцію');
      return response.json();
    },
  });

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
        <MaterialCommunityIcons name="alert-circle" size={60} color="#f44336" />
        <Text style={styles.errorText}>Операцію не знайдено</Text>
        <TouchableOpacity style={styles.backButton} onPress={() => router.back()}>
          <Text style={styles.backButtonText}>Повернутися</Text>
        </TouchableOpacity>
      </View>
    );
  }

  const { operation, expected_outputs, actual_outputs } = data;
  const isCompleted = operation.status === 'completed';

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'in_progress':
        return '#FF9800';
      case 'completed':
        return '#4CAF50';
      default:
        return '#999';
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'in_progress':
        return 'В процесі';
      case 'completed':
        return 'Завершена';
      default:
        return status;
    }
  };

  const handleComplete = () => {
    router.push(`/butchery/complete-form?operationId=${id}` as any);
  };

  const totalExpectedWeight = expected_outputs.reduce(
    (sum: number, out: any) => sum + out.expected_weight,
    0
  );

  const totalActualWeight = actual_outputs.reduce(
    (sum: number, out: any) => sum + out.actual_weight,
    0
  );

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.headerBackButton}>
          <MaterialCommunityIcons name="arrow-left" size={24} color="#007AFF" />
        </TouchableOpacity>
        <View style={styles.headerContent}>
          <Text style={styles.headerTitle}>{operation.operation_number}</Text>
          <View style={[styles.statusBadge, { backgroundColor: getStatusColor(operation.status) }]}>
            <Text style={styles.statusText}>{getStatusText(operation.status)}</Text>
          </View>
        </View>
      </View>

      <ScrollView style={styles.content}>
        {/* Main info */}
        <View style={styles.card}>
          <View style={styles.cardHeader}>
            <MaterialCommunityIcons name="information" size={20} color="#007AFF" />
            <Text style={styles.cardTitle}>Інформація про розділку</Text>
          </View>

          <View style={styles.infoRow}>
            <Text style={styles.infoLabel}>Рецепт:</Text>
            <Text style={styles.infoValue}>{operation.recipe_name}</Text>
          </View>

          <View style={styles.infoRow}>
            <Text style={styles.infoLabel}>Сировина:</Text>
            <Text style={styles.infoValue}>{operation.source_name}</Text>
          </View>

          <View style={styles.infoRow}>
            <Text style={styles.infoLabel}>Вхідна вага:</Text>
            <Text style={[styles.infoValue, styles.weightValue]}>{operation.input_weight} кг</Text>
          </View>

          <View style={styles.infoRow}>
            <Text style={styles.infoLabel}>Початок:</Text>
            <Text style={styles.infoValue}>
              {new Date(operation.started_at).toLocaleString('uk-UA', {
                day: '2-digit',
                month: '2-digit',
                year: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
              })}
            </Text>
          </View>

          {operation.completed_at && (
            <View style={styles.infoRow}>
              <Text style={styles.infoLabel}>Завершено:</Text>
              <Text style={styles.infoValue}>
                {new Date(operation.completed_at).toLocaleString('uk-UA', {
                  day: '2-digit',
                  month: '2-digit',
                  year: 'numeric',
                  hour: '2-digit',
                  minute: '2-digit',
                })}
              </Text>
            </View>
          )}

          {operation.operator_notes && (
            <View style={[styles.infoRow, { marginTop: 8 }]}>
              <Text style={styles.infoLabel}>Примітки:</Text>
              <Text style={styles.notesValue}>{operation.operator_notes}</Text>
            </View>
          )}
        </View>

        {/* Expected outputs */}
        <View style={styles.card}>
          <View style={styles.cardHeader}>
            <MaterialCommunityIcons name="chart-box" size={20} color="#FF9800" />
            <Text style={styles.cardTitle}>Очікувані виходи</Text>
          </View>

          {expected_outputs.map((output: any, idx: number) => (
            <View key={idx} style={styles.outputRow}>
              <View style={styles.outputInfo}>
                <Text style={styles.outputName}>{output.output_name}</Text>
                <Text style={styles.outputPercentage}>{output.yield_percentage}%</Text>
              </View>
              <Text style={styles.outputWeight}>{output.expected_weight.toFixed(2)} кг</Text>
            </View>
          ))}

          <View style={styles.totalRow}>
            <Text style={styles.totalLabel}>Загальна очікувана вага:</Text>
            <Text style={styles.totalValue}>{totalExpectedWeight.toFixed(2)} кг</Text>
          </View>
        </View>

        {/* Actual outputs (if completed) */}
        {isCompleted && actual_outputs.length > 0 && (
          <View style={styles.card}>
            <View style={styles.cardHeader}>
              <MaterialCommunityIcons name="check-circle" size={20} color="#4CAF50" />
              <Text style={styles.cardTitle}>Фактичні виходи</Text>
            </View>

            {actual_outputs.map((output: any, idx: number) => (
              <View key={idx} style={styles.outputRow}>
                <View style={styles.outputInfo}>
                  <Text style={styles.outputName}>{output.output_name}</Text>
                  {output.yield_percentage && (
                    <Text style={styles.outputPercentage}>{output.yield_percentage.toFixed(1)}%</Text>
                  )}
                </View>
                <View style={styles.actualWeightContainer}>
                  <Text style={styles.outputWeight}>{output.actual_weight.toFixed(2)} кг</Text>
                  {output.expected_weight && (
                    <Text
                      style={[
                        styles.differenceText,
                        output.actual_weight > output.expected_weight
                          ? styles.differencePositive
                          : styles.differenceNegative,
                      ]}
                    >
                      {output.actual_weight > output.expected_weight ? '+' : ''}
                      {(output.actual_weight - output.expected_weight).toFixed(2)} кг
                    </Text>
                  )}
                </View>
              </View>
            ))}

            <View style={styles.totalRow}>
              <Text style={styles.totalLabel}>Загальна фактична вага:</Text>
              <View>
                <Text style={styles.totalValue}>{totalActualWeight.toFixed(2)} кг</Text>
                <Text
                  style={[
                    styles.totalDifference,
                    totalActualWeight > totalExpectedWeight
                      ? styles.differencePositive
                      : styles.differenceNegative,
                  ]}
                >
                  {totalActualWeight > totalExpectedWeight ? '+' : ''}
                  {(totalActualWeight - totalExpectedWeight).toFixed(2)} кг від очікуваної
                </Text>
              </View>
            </View>
          </View>
        )}

        {/* Complete button */}
        {!isCompleted && (
          <View style={styles.buttonContainer}>
            <TouchableOpacity style={styles.completeButton} onPress={handleComplete}>
              <MaterialCommunityIcons name="check-circle" size={20} color="#fff" />
              <Text style={styles.completeButtonText}>Завершити розділку</Text>
            </TouchableOpacity>
          </View>
        )}

        <View style={{ height: 40 }} />
      </ScrollView>
    </View>
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
    fontWeight: '600',
    color: '#666',
    marginTop: 16,
    marginBottom: 24,
  },
  backButton: {
    backgroundColor: '#007AFF',
    paddingVertical: 12,
    paddingHorizontal: 24,
    borderRadius: 8,
  },
  backButtonText: {
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
  headerBackButton: {
    marginRight: 12,
    padding: 4,
  },
  headerContent: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  headerTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#333',
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
  content: {
    flex: 1,
  },
  card: {
    backgroundColor: '#fff',
    marginHorizontal: 16,
    marginTop: 16,
    padding: 16,
    borderRadius: 12,
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
  },
  cardHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 16,
    paddingBottom: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0',
  },
  cardTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
    marginLeft: 8,
  },
  infoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 12,
  },
  infoLabel: {
    fontSize: 14,
    color: '#666',
    flex: 1,
  },
  infoValue: {
    fontSize: 14,
    color: '#333',
    flex: 2,
    textAlign: 'right',
  },
  weightValue: {
    fontSize: 16,
    fontWeight: '600',
    color: '#4CAF50',
  },
  notesValue: {
    fontSize: 14,
    color: '#333',
    flex: 2,
    textAlign: 'right',
    fontStyle: 'italic',
  },
  outputRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#f5f5f5',
  },
  outputInfo: {
    flex: 1,
  },
  outputName: {
    fontSize: 14,
    color: '#333',
    fontWeight: '500',
    marginBottom: 4,
  },
  outputPercentage: {
    fontSize: 12,
    color: '#999',
  },
  outputWeight: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
  },
  actualWeightContainer: {
    alignItems: 'flex-end',
  },
  differenceText: {
    fontSize: 12,
    marginTop: 4,
  },
  differencePositive: {
    color: '#4CAF50',
  },
  differenceNegative: {
    color: '#f44336',
  },
  totalRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingTop: 16,
    marginTop: 8,
    borderTopWidth: 2,
    borderTopColor: '#e0e0e0',
  },
  totalLabel: {
    fontSize: 15,
    fontWeight: '600',
    color: '#333',
  },
  totalValue: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#007AFF',
  },
  totalDifference: {
    fontSize: 12,
    textAlign: 'right',
    marginTop: 4,
  },
  buttonContainer: {
    paddingHorizontal: 16,
    marginTop: 24,
  },
  completeButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#4CAF50',
    padding: 16,
    borderRadius: 12,
    gap: 8,
  },
  completeButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
});
