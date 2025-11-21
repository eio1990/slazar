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
  Modal,
} from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

const API_URL = process.env.EXPO_PUBLIC_BACKEND_URL || 'http://localhost:8001';

export default function PackagingBatchDetailScreen() {
  const router = useRouter();
  const { id } = useLocalSearchParams();
  const queryClient = useQueryClient();

  const [recordModalVisible, setRecordModalVisible] = useState(false);
  const [packedQty, setPackedQty] = useState('');
  const [sourceUsed, setSourceUsed] = useState('');
  const [waste, setWaste] = useState('0');
  const [opNotes, setOpNotes] = useState('');

  // Get batch details
  const { data: batch, isLoading } = useQuery({
    queryKey: ['packaging-batch', id],
    queryFn: async () => {
      const response = await fetch(`${API_URL}/api/packaging/batches/${id}`);
      if (!response.ok) throw new Error('Failed to fetch batch');
      return response.json();
    },
  });

  // Record operation mutation
  const recordOperationMutation = useMutation({
    mutationFn: async (opData: any) => {
      const response = await fetch(`${API_URL}/api/packaging/batches/${id}/operations`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(opData),
      });
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to record operation');
      }
      return response.json();
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['packaging-batch', id] });
      queryClient.invalidateQueries({ queryKey: ['packaging-batches'] });
      
      setRecordModalVisible(false);
      setPackedQty('');
      setSourceUsed('');
      setWaste('0');
      setOpNotes('');
      
      // Показати які матеріали були автоматично списані
      const materialsInfo = data.materials_used
        ?.map((m: any) => `${m.material_name}: ${m.quantity} ${m.unit}`)
        .join('\n');
      
      Alert.alert(
        'Успіх',
        `Операцію записано!\n\nЗафасовано: ${data.packed_quantity} шт\n\nСписано матеріали:\n${materialsInfo}`
      );
    },
    onError: (error: any) => {
      Alert.alert('Помилка', error.message);
    },
  });

  // Complete batch mutation
  const completeBatchMutation = useMutation({
    mutationFn: async () => {
      const response = await fetch(`${API_URL}/api/packaging/batches/${id}/complete`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ notes: 'Партію завершено' }),
      });
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to complete batch');
      }
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['packaging-batch', id] });
      queryClient.invalidateQueries({ queryKey: ['packaging-batches'] });
      Alert.alert('Успіх', 'Партію завершено');
    },
    onError: (error: any) => {
      Alert.alert('Помилка', error.message);
    },
  });

  const handleRecordOperation = () => {
    const qty = parseInt(packedQty);
    const used = parseFloat(sourceUsed);
    const wasteQty = parseFloat(waste);

    if (!packedQty || isNaN(qty) || qty <= 0) {
      Alert.alert('Помилка', 'Введіть кількість запакованих одиниць');
      return;
    }

    if (!sourceUsed || isNaN(used) || used <= 0) {
      Alert.alert('Помилка', 'Введіть фактично використаний продукт');
      return;
    }

    if (isNaN(wasteQty) || wasteQty < 0) {
      Alert.alert('Помилка', 'Введіть коректну кількість відходів');
      return;
    }

    const operationData = {
      packed_quantity: qty,
      source_used: used,
      waste_quantity: wasteQty,
      notes: opNotes || null,
      idempotency_key: `pack-op-${id}-${Date.now()}`,
    };

    recordOperationMutation.mutate(operationData);
  };

  const handleCompleteBatch = () => {
    Alert.alert(
      'Підтвердження',
      'Завершити партію фасування?\n\nПісля завершення додати нові операції буде неможливо.',
      [
        { text: 'Скасувати', style: 'cancel' },
        { text: 'Завершити', onPress: () => completeBatchMutation.mutate() },
      ]
    );
  };

  if (isLoading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#007AFF" />
      </View>
    );
  }

  if (!batch) {
    return (
      <View style={styles.loadingContainer}>
        <Text>Партія не знайдена</Text>
      </View>
    );
  }

  const progress = batch.planned_quantity
    ? Math.min(100, (batch.actual_packed_quantity / batch.planned_quantity) * 100)
    : 0;

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
          <MaterialCommunityIcons name="arrow-left" size={24} color="#007AFF" />
        </TouchableOpacity>
        <View style={styles.headerInfo}>
          <Text style={styles.batchNumber}>{batch.batch_number}</Text>
          <View style={[
            styles.statusBadge,
            { backgroundColor: batch.status === 'completed' ? '#4CAF50' : '#FF9800' }
          ]}>
            <Text style={styles.statusText}>
              {batch.status === 'completed' ? 'Завершена' : 'В процесі'}
            </Text>
          </View>
        </View>
      </View>

      <ScrollView style={styles.content}>
        {/* Product Info */}
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Продукт</Text>
          <View style={styles.infoRow}>
            <Text style={styles.label}>Фасована продукція:</Text>
            <Text style={styles.value}>{batch.target_product_name}</Text>
          </View>
          <View style={styles.infoRow}>
            <Text style={styles.label}>Вихідний продукт:</Text>
            <Text style={styles.value}>{batch.source_product_name}</Text>
          </View>
          <View style={styles.infoRow}>
            <Text style={styles.label}>Тип фасування:</Text>
            <Text style={styles.value}>
              {batch.packaging_type === 'vacuum' ? '🔷 Вакуум' :
               batch.packaging_type === 'skin' ? '📦 Скін' : '⚖️ Ваговий'}
            </Text>
          </View>
        </View>

        {/* Stats */}
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Статистика</Text>
          
          {batch.planned_quantity && (
            <>
              <View style={styles.infoRow}>
                <Text style={styles.label}>Заплановано:</Text>
                <Text style={styles.value}>{batch.planned_quantity} шт</Text>
              </View>
              <View style={styles.progressBar}>
                <View style={[styles.progressFill, { width: `${progress}%` }]} />
              </View>
            </>
          )}
          
          <View style={styles.infoRow}>
            <Text style={styles.label}>Зафасовано:</Text>
            <Text style={[styles.value, styles.highlight]}>{batch.actual_packed_quantity} шт</Text>
          </View>
          <View style={styles.infoRow}>
            <Text style={styles.label}>Взято продукту:</Text>
            <Text style={styles.value}>{batch.source_weight_taken} кг</Text>
          </View>
          <View style={styles.infoRow}>
            <Text style={styles.label}>Використано:</Text>
            <Text style={styles.value}>{batch.actual_source_used} кг</Text>
          </View>
          <View style={styles.infoRow}>
            <Text style={styles.label}>Відходи:</Text>
            <Text style={styles.value}>{batch.waste_quantity.toFixed(2)} кг</Text>
          </View>
        </View>

        {/* Actions */}
        {batch.status !== 'completed' && (
          <View style={styles.actionsCard}>
            <TouchableOpacity
              style={styles.actionButton}
              onPress={() => setRecordModalVisible(true)}
            >
              <MaterialCommunityIcons name="plus-circle" size={24} color="#007AFF" />
              <Text style={styles.actionButtonText}>Записати операцію</Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={[styles.actionButton, styles.completeButton]}
              onPress={handleCompleteBatch}
              disabled={completeBatchMutation.isPending}
            >
              <MaterialCommunityIcons name="check-circle" size={24} color="#4CAF50" />
              <Text style={[styles.actionButtonText, { color: '#4CAF50' }]}>
                Завершити партію
              </Text>
            </TouchableOpacity>
          </View>
        )}
      </ScrollView>

      {/* Record Operation Modal */}
      <Modal
        visible={recordModalVisible}
        animationType="slide"
        transparent={true}
        onRequestClose={() => setRecordModalVisible(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Записати операцію</Text>
              <TouchableOpacity onPress={() => setRecordModalVisible(false)}>
                <MaterialCommunityIcons name="close" size={24} color="#666" />
              </TouchableOpacity>
            </View>

            <ScrollView style={styles.modalBody}>
              <Text style={styles.modalInfo}>
                Система автоматично розрахує та спише матеріали за нормами
              </Text>

              <View style={styles.inputGroup}>
                <Text style={styles.inputLabel}>Кількість запакованих одиниць (шт) *</Text>
                <TextInput
                  style={styles.input}
                  value={packedQty}
                  onChangeText={setPackedQty}
                  placeholder="напр. 50"
                  keyboardType="number-pad"
                />
              </View>

              <View style={styles.inputGroup}>
                <Text style={styles.inputLabel}>Використано вихідного продукту (кг) *</Text>
                <TextInput
                  style={styles.input}
                  value={sourceUsed}
                  onChangeText={setSourceUsed}
                  placeholder="напр. 2.5"
                  keyboardType="decimal-pad"
                />
              </View>

              <View style={styles.inputGroup}>
                <Text style={styles.inputLabel}>Відходи (кг)</Text>
                <TextInput
                  style={styles.input}
                  value={waste}
                  onChangeText={setWaste}
                  placeholder="0"
                  keyboardType="decimal-pad"
                />
              </View>

              <View style={styles.inputGroup}>
                <Text style={styles.inputLabel}>Примітки</Text>
                <TextInput
                  style={styles.textArea}
                  value={opNotes}
                  onChangeText={setOpNotes}
                  placeholder="Додаткова інформація..."
                  multiline
                  numberOfLines={2}
                />
              </View>

              <TouchableOpacity
                style={styles.submitButton}
                onPress={handleRecordOperation}
                disabled={recordOperationMutation.isPending}
              >
                {recordOperationMutation.isPending ? (
                  <ActivityIndicator color="#fff" />
                ) : (
                  <Text style={styles.submitButtonText}>Записати</Text>
                )}
              </TouchableOpacity>
            </ScrollView>
          </View>
        </View>
      </Modal>
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
  headerInfo: {
    flex: 1,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  batchNumber: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
  },
  statusBadge: {
    paddingHorizontal: 12,
    paddingVertical: 4,
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
    elevation: 1,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
  },
  cardTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
    marginBottom: 12,
  },
  infoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 10,
  },
  label: {
    fontSize: 14,
    color: '#666',
  },
  value: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
  },
  highlight: {
    fontSize: 18,
    color: '#007AFF',
  },
  progressBar: {
    height: 6,
    backgroundColor: '#e0e0e0',
    borderRadius: 3,
    marginBottom: 12,
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    backgroundColor: '#4CAF50',
    borderRadius: 3,
  },
  actionsCard: {
    backgroundColor: '#fff',
    marginHorizontal: 16,
    marginTop: 16,
    marginBottom: 32,
    padding: 16,
    borderRadius: 12,
    elevation: 1,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
  },
  actionButton: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#007AFF',
    marginBottom: 12,
  },
  completeButton: {
    borderColor: '#4CAF50',
    marginBottom: 0,
  },
  actionButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#007AFF',
    marginLeft: 12,
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'flex-end',
  },
  modalContent: {
    backgroundColor: '#fff',
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    maxHeight: '80%',
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 20,
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333',
  },
  modalBody: {
    padding: 20,
  },
  modalInfo: {
    fontSize: 14,
    color: '#666',
    backgroundColor: '#E3F2FD',
    padding: 12,
    borderRadius: 8,
    marginBottom: 20,
  },
  inputGroup: {
    marginBottom: 16,
  },
  inputLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
    marginBottom: 8,
  },
  input: {
    backgroundColor: '#f5f5f5',
    borderRadius: 8,
    padding: 12,
    fontSize: 16,
    color: '#333',
  },
  textArea: {
    backgroundColor: '#f5f5f5',
    borderRadius: 8,
    padding: 12,
    fontSize: 16,
    color: '#333',
    minHeight: 60,
    textAlignVertical: 'top',
  },
  submitButton: {
    backgroundColor: '#007AFF',
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
    marginTop: 8,
  },
  submitButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
});
