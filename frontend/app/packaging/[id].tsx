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

export default function PackagingSessionDetailScreen() {
  const router = useRouter();
  const { id } = useLocalSearchParams();
  const queryClient = useQueryClient();

  const [outputModalVisible, setOutputModalVisible] = useState(false);
  const [remainderModalVisible, setRemainderModalVisible] = useState(false);
  const [wasteModalVisible, setWasteModalVisible] = useState(false);

  // Output form state
  const [selectedSKU, setSelectedSKU] = useState<any>(null);
  const [packedQty, setPackedQty] = useState('');
  const [defectQty, setDefectQty] = useState('0');
  const [outputNotes, setOutputNotes] = useState('');

  // Remainder form state
  const [selectedRemainderNom, setSelectedRemainderNom] = useState<any>(null);
  const [remainderWeight, setRemainderWeight] = useState('');
  const [remainderDesc, setRemainderDesc] = useState('');
  const [remainderNotes, setRemainderNotes] = useState('');

  // Waste form state
  const [wasteWeight, setWasteWeight] = useState('');
  const [wasteDesc, setWasteDesc] = useState('');
  const [wasteNotes, setWasteNotes] = useState('');

  // Get session details
  const { data: session, isLoading } = useQuery({
    queryKey: ['packaging-session', id],
    queryFn: async () => {
      const response = await fetch(`${API_URL}/api/packaging/sessions/${id}`);
      if (!response.ok) throw new Error('Failed to fetch session');
      return response.json();
    },
  });

  // Get packaging recipes (for SKU selection)
  const { data: recipes } = useQuery({
    queryKey: ['packaging-recipes', session?.source_product_id],
    queryFn: async () => {
      if (!session?.source_product_id) return [];
      const response = await fetch(`${API_URL}/api/packaging/recipes?source_product_id=${session.source_product_id}`);
      if (!response.ok) throw new Error('Failed to fetch recipes');
      return response.json();
    },
    enabled: !!session?.source_product_id,
  });

  // Get nomenclature (for remainder selection)
  const { data: nomenclature } = useQuery({
    queryKey: ['nomenclature'],
    queryFn: async () => {
      const response = await fetch(`${API_URL}/api/nomenclature`);
      if (!response.ok) throw new Error('Failed to fetch nomenclature');
      return response.json();
    },
  });

  // Add output mutation
  const addOutputMutation = useMutation({
    mutationFn: async (outputData: any) => {
      const response = await fetch(`${API_URL}/api/packaging/sessions/${id}/outputs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(outputData),
      });
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to add output');
      }
      return response.json();
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['packaging-session', id] });
      setOutputModalVisible(false);
      setSelectedSKU(null);
      setPackedQty('');
      setDefectQty('0');
      setOutputNotes('');
      
      const materialsInfo = data.materials_used
        ?.map((m: any) => `${m.material_name}: ${m.quantity} ${m.unit}`)
        .join('\n');
      
      Alert.alert('Успіх', `Вихід додано!\n\nЗафасовано: ${data.quantity_packed} шт\n\nМатеріали списано:\n${materialsInfo}`);
    },
    onError: (error: any) => {
      Alert.alert('Помилка', error.message);
    },
  });

  // Add remainder mutation
  const addRemainderMutation = useMutation({
    mutationFn: async (remainderData: any) => {
      const response = await fetch(`${API_URL}/api/packaging/sessions/${id}/remainders`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(remainderData),
      });
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to add remainder');
      }
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['packaging-session', id] });
      setRemainderModalVisible(false);
      setSelectedRemainderNom(null);
      setRemainderWeight('');
      setRemainderDesc('');
      setRemainderNotes('');
      Alert.alert('Успіх', 'Залишок додано та оприбутковано на склад');
    },
    onError: (error: any) => {
      Alert.alert('Помилка', error.message);
    },
  });

  // Add waste mutation
  const addWasteMutation = useMutation({
    mutationFn: async (wasteData: any) => {
      const response = await fetch(`${API_URL}/api/packaging/sessions/${id}/waste`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(wasteData),
      });
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to add waste');
      }
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['packaging-session', id] });
      setWasteModalVisible(false);
      setWasteWeight('');
      setWasteDesc('');
      setWasteNotes('');
      Alert.alert('Успіх', 'Відходи зафіксовано');
    },
    onError: (error: any) => {
      Alert.alert('Помилка', error.message);
    },
  });

  // Complete session mutation
  const completeSessionMutation = useMutation({
    mutationFn: async () => {
      const response = await fetch(`${API_URL}/api/packaging/sessions/${id}/complete`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ notes: 'Сесію завершено' }),
      });
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to complete session');
      }
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['packaging-session', id] });
      queryClient.invalidateQueries({ queryKey: ['packaging-sessions'] });
      Alert.alert('Успіх', 'Сесію фасування завершено');
    },
    onError: (error: any) => {
      Alert.alert('Помилка', error.message);
    },
  });

  const handleAddOutput = () => {
    if (!selectedSKU) {
      Alert.alert('Помилка', 'Оберіть SKU для фасування');
      return;
    }

    const qty = parseInt(packedQty);
    if (!packedQty || isNaN(qty) || qty <= 0) {
      Alert.alert('Помилка', 'Введіть кількість упакованих одиниць');
      return;
    }

    const defect = parseInt(defectQty);
    if (isNaN(defect) || defect < 0) {
      Alert.alert('Помилка', 'Введіть коректну кількість браку');
      return;
    }

    const outputData = {
      target_product_id: selectedSKU.target_product_id,
      quantity_packed: qty,
      defect_quantity: defect,
      notes: outputNotes || null,
    };

    addOutputMutation.mutate(outputData);
  };

  const handleAddRemainder = () => {
    if (!selectedRemainderNom) {
      Alert.alert('Помилка', 'Оберіть номенклатуру залишку');
      return;
    }

    const weight = parseFloat(remainderWeight);
    if (!remainderWeight || isNaN(weight) || weight <= 0) {
      Alert.alert('Помилка', 'Введіть вагу залишку');
      return;
    }

    const remainderData = {
      nomenclature_id: selectedRemainderNom.id,
      weight_kg: weight,
      description: remainderDesc || null,
      notes: remainderNotes || null,
    };

    addRemainderMutation.mutate(remainderData);
  };

  const handleAddWaste = () => {
    const weight = parseFloat(wasteWeight);
    if (!wasteWeight || isNaN(weight) || weight <= 0) {
      Alert.alert('Помилка', 'Введіть вагу відходів');
      return;
    }

    const wasteData = {
      waste_weight_kg: weight,
      waste_description: wasteDesc || null,
      notes: wasteNotes || null,
    };

    addWasteMutation.mutate(wasteData);
  };

  const handleCompleteSession = () => {
    Alert.alert(
      'Підтвердження',
      'Завершити сесію фасування?\n\nПісля завершення додати нові операції буде неможливо.',
      [
        { text: 'Скасувати', style: 'cancel' },
        { text: 'Завершити', onPress: () => completeSessionMutation.mutate() },
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

  if (!session) {
    return (
      <View style={styles.loadingContainer}>
        <Text>Сесію не знайдено</Text>
      </View>
    );
  }

  const totalOutputs = session.outputs?.length || 0;
  const totalPacked = session.outputs?.reduce((sum: number, o: any) => sum + o.quantity_packed, 0) || 0;

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
          <MaterialCommunityIcons name="arrow-left" size={24} color="#007AFF" />
        </TouchableOpacity>
        <View style={styles.headerInfo}>
          <Text style={styles.sessionNumber}>{session.session_number}</Text>
          <View style={[
            styles.statusBadge,
            { backgroundColor: session.status === 'completed' ? '#4CAF50' : '#FF9800' }
          ]}>
            <Text style={styles.statusText}>
              {session.status === 'completed' ? 'Завершена' : 'В процесі'}
            </Text>
          </View>
        </View>
      </View>

      <ScrollView style={styles.content}>
        {/* Product Info */}
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Продукт</Text>
          <View style={styles.infoRow}>
            <Text style={styles.label}>Вихідний продукт:</Text>
            <Text style={styles.value}>{session.source_product_name}</Text>
          </View>
          <View style={styles.infoRow}>
            <Text style={styles.label}>Взято для фасування:</Text>
            <Text style={styles.value}>{session.source_weight_taken} кг</Text>
          </View>
        </View>

        {/* Statistics */}
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Статистика</Text>
          <View style={styles.infoRow}>
            <Text style={styles.label}>Різних виходів (SKU):</Text>
            <Text style={[styles.value, styles.highlight]}>{totalOutputs}</Text>
          </View>
          <View style={styles.infoRow}>
            <Text style={styles.label}>Всього упаковано:</Text>
            <Text style={[styles.value, styles.highlight]}>{totalPacked} шт</Text>
          </View>
          <View style={styles.infoRow}>
            <Text style={styles.label}>Залишків:</Text>
            <Text style={styles.value}>{session.remainders?.length || 0}</Text>
          </View>
          <View style={styles.infoRow}>
            <Text style={styles.label}>Записів відходів:</Text>
            <Text style={styles.value}>{session.waste?.length || 0}</Text>
          </View>
        </View>

        {/* Outputs List */}
        {session.outputs && session.outputs.length > 0 && (
          <View style={styles.card}>
            <Text style={styles.cardTitle}>Виходи (готова продукція)</Text>
            {session.outputs.map((output: any, index: number) => (
              <View key={output.id} style={[styles.outputItem, index > 0 && styles.outputItemBorder]}>
                <Text style={styles.outputName}>{output.target_product_name}</Text>
                <Text style={styles.outputDetail}>Кількість: {output.quantity_packed} шт</Text>
                {output.defect_quantity > 0 && (
                  <Text style={styles.outputDefect}>Брак: {output.defect_quantity} шт</Text>
                )}
              </View>
            ))}
          </View>
        )}

        {/* Remainders List */}
        {session.remainders && session.remainders.length > 0 && (
          <View style={styles.card}>
            <Text style={styles.cardTitle}>Залишки (оприбутковано)</Text>
            {session.remainders.map((remainder: any) => (
              <View key={remainder.id} style={styles.remainderItem}>
                <Text style={styles.remainderName}>{remainder.nomenclature_name}</Text>
                <Text style={styles.remainderDetail}>Вага: {remainder.weight_kg} кг</Text>
                {remainder.description && (
                  <Text style={styles.remainderDesc}>{remainder.description}</Text>
                )}
              </View>
            ))}
          </View>
        )}

        {/* Waste List */}
        {session.waste && session.waste.length > 0 && (
          <View style={styles.card}>
            <Text style={styles.cardTitle}>Відходи (втрати)</Text>
            {session.waste.map((waste: any) => (
              <View key={waste.id} style={styles.wasteItem}>
                <Text style={styles.wasteWeight}>Вага: {waste.waste_weight_kg} кг</Text>
                {waste.waste_description && (
                  <Text style={styles.wasteDesc}>{waste.waste_description}</Text>
                )}
              </View>
            ))}
          </View>
        )}

        {/* Actions */}
        {session.status !== 'completed' && (
          <View style={styles.actionsCard}>
            <TouchableOpacity
              style={styles.actionButton}
              onPress={() => setOutputModalVisible(true)}
            >
              <MaterialCommunityIcons name="package-variant" size={24} color="#007AFF" />
              <Text style={styles.actionButtonText}>Додати вихід (SKU)</Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={styles.actionButton}
              onPress={() => setRemainderModalVisible(true)}
            >
              <MaterialCommunityIcons name="restart" size={24} color="#FF9800" />
              <Text style={[styles.actionButtonText, { color: '#FF9800' }]}>Додати залишок</Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={styles.actionButton}
              onPress={() => setWasteModalVisible(true)}
            >
              <MaterialCommunityIcons name="delete-outline" size={24} color="#f44336" />
              <Text style={[styles.actionButtonText, { color: '#f44336' }]}>Додати відходи</Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={[styles.actionButton, styles.completeButton]}
              onPress={handleCompleteSession}
              disabled={completeSessionMutation.isPending}
            >
              <MaterialCommunityIcons name="check-circle" size={24} color="#4CAF50" />
              <Text style={[styles.actionButtonText, { color: '#4CAF50' }]}>
                Завершити сесію
              </Text>
            </TouchableOpacity>
          </View>
        )}
      </ScrollView>

      {/* Add Output Modal */}
      <Modal
        visible={outputModalVisible}
        animationType="slide"
        transparent={true}
        onRequestClose={() => setOutputModalVisible(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Додати вихід (SKU)</Text>
              <TouchableOpacity onPress={() => setOutputModalVisible(false)}>
                <MaterialCommunityIcons name="close" size={24} color="#666" />
              </TouchableOpacity>
            </View>

            <ScrollView style={styles.modalBody}>
              <Text style={styles.modalInfo}>
                Система автоматично розрахує та спише матеріали
              </Text>

              <Text style={styles.inputLabel}>Оберіть SKU *</Text>
              <ScrollView style={styles.skuList} nestedScrollEnabled>
                {recipes?.map((recipe: any) => (
                  <TouchableOpacity
                    key={recipe.id}
                    style={[
                      styles.skuCard,
                      selectedSKU?.id === recipe.id && styles.skuCardSelected,
                    ]}
                    onPress={() => setSelectedSKU(recipe)}
                  >
                    <Text style={styles.skuName}>{recipe.target_product_name}</Text>
                    <Text style={styles.skuWeight}>{recipe.target_weight_grams}г - {recipe.packaging_type}</Text>
                  </TouchableOpacity>
                ))}
              </ScrollView>

              <View style={styles.inputGroup}>
                <Text style={styles.inputLabel}>Кількість упакованих (шт) *</Text>
                <TextInput
                  style={styles.input}
                  value={packedQty}
                  onChangeText={setPackedQty}
                  placeholder="напр. 50"
                  keyboardType="number-pad"
                />
              </View>

              <View style={styles.inputGroup}>
                <Text style={styles.inputLabel}>Брак (шт)</Text>
                <TextInput
                  style={styles.input}
                  value={defectQty}
                  onChangeText={setDefectQty}
                  placeholder="0"
                  keyboardType="number-pad"
                />
              </View>

              <View style={styles.inputGroup}>
                <Text style={styles.inputLabel}>Примітки</Text>
                <TextInput
                  style={styles.textArea}
                  value={outputNotes}
                  onChangeText={setOutputNotes}
                  placeholder="Додаткова інформація..."
                  multiline
                  numberOfLines={2}
                />
              </View>

              <TouchableOpacity
                style={styles.submitButton}
                onPress={handleAddOutput}
                disabled={addOutputMutation.isPending}
              >
                {addOutputMutation.isPending ? (
                  <ActivityIndicator color="#fff" />
                ) : (
                  <Text style={styles.submitButtonText}>Додати вихід</Text>
                )}
              </TouchableOpacity>
            </ScrollView>
          </View>
        </View>
      </Modal>

      {/* Add Remainder Modal */}
      <Modal
        visible={remainderModalVisible}
        animationType="slide"
        transparent={true}
        onRequestClose={() => setRemainderModalVisible(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Додати залишок</Text>
              <TouchableOpacity onPress={() => setRemainderModalVisible(false)}>
                <MaterialCommunityIcons name="close" size={24} color="#666" />
              </TouchableOpacity>
            </View>

            <ScrollView style={styles.modalBody}>
              <Text style={styles.modalInfo}>
                Залишок буде оприбутковано на склад
              </Text>

              <Text style={styles.inputLabel}>Оберіть номенклатуру *</Text>
              <ScrollView style={styles.skuList} nestedScrollEnabled>
                {nomenclature?.filter((n: any) => n.category === 'Спеції' || n.name.includes('Залишки')).map((nom: any) => (
                  <TouchableOpacity
                    key={nom.id}
                    style={[
                      styles.skuCard,
                      selectedRemainderNom?.id === nom.id && styles.skuCardSelected,
                    ]}
                    onPress={() => setSelectedRemainderNom(nom)}
                  >
                    <Text style={styles.skuName}>{nom.name}</Text>
                    <Text style={styles.skuWeight}>{nom.unit}</Text>
                  </TouchableOpacity>
                ))}
              </ScrollView>

              <View style={styles.inputGroup}>
                <Text style={styles.inputLabel}>Вага (кг) *</Text>
                <TextInput
                  style={styles.input}
                  value={remainderWeight}
                  onChangeText={setRemainderWeight}
                  placeholder="напр. 1.5"
                  keyboardType="decimal-pad"
                />
              </View>

              <View style={styles.inputGroup}>
                <Text style={styles.inputLabel}>Опис</Text>
                <TextInput
                  style={styles.input}
                  value={remainderDesc}
                  onChangeText={setRemainderDesc}
                  placeholder="напр. Упавші спеції"
                />
              </View>

              <View style={styles.inputGroup}>
                <Text style={styles.inputLabel}>Примітки</Text>
                <TextInput
                  style={styles.textArea}
                  value={remainderNotes}
                  onChangeText={setRemainderNotes}
                  placeholder="Додаткова інформація..."
                  multiline
                  numberOfLines={2}
                />
              </View>

              <TouchableOpacity
                style={styles.submitButton}
                onPress={handleAddRemainder}
                disabled={addRemainderMutation.isPending}
              >
                {addRemainderMutation.isPending ? (
                  <ActivityIndicator color="#fff" />
                ) : (
                  <Text style={styles.submitButtonText}>Додати залишок</Text>
                )}
              </TouchableOpacity>
            </ScrollView>
          </View>
        </View>
      </Modal>

      {/* Add Waste Modal */}
      <Modal
        visible={wasteModalVisible}
        animationType="slide"
        transparent={true}
        onRequestClose={() => setWasteModalVisible(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Додати відходи</Text>
              <TouchableOpacity onPress={() => setWasteModalVisible(false)}>
                <MaterialCommunityIcons name="close" size={24} color="#666" />
              </TouchableOpacity>
            </View>

            <ScrollView style={styles.modalBody}>
              <Text style={styles.modalInfo}>
                Відходи будуть зафіксовані тільки для аналітики
              </Text>

              <View style={styles.inputGroup}>
                <Text style={styles.inputLabel}>Вага відходів (кг) *</Text>
                <TextInput
                  style={styles.input}
                  value={wasteWeight}
                  onChangeText={setWasteWeight}
                  placeholder="напр. 0.5"
                  keyboardType="decimal-pad"
                />
              </View>

              <View style={styles.inputGroup}>
                <Text style={styles.inputLabel}>Опис</Text>
                <TextInput
                  style={styles.input}
                  value={wasteDesc}
                  onChangeText={setWasteDesc}
                  placeholder="напр. Втрати при фасуванні"
                />
              </View>

              <View style={styles.inputGroup}>
                <Text style={styles.inputLabel}>Примітки</Text>
                <TextInput
                  style={styles.textArea}
                  value={wasteNotes}
                  onChangeText={setWasteNotes}
                  placeholder="Додаткова інформація..."
                  multiline
                  numberOfLines={2}
                />
              </View>

              <TouchableOpacity
                style={styles.submitButton}
                onPress={handleAddWaste}
                disabled={addWasteMutation.isPending}
              >
                {addWasteMutation.isPending ? (
                  <ActivityIndicator color="#fff" />
                ) : (
                  <Text style={styles.submitButtonText}>Додати відходи</Text>
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
  sessionNumber: {
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
  outputItem: {
    paddingVertical: 8,
  },
  outputItemBorder: {
    borderTopWidth: 1,
    borderTopColor: '#e0e0e0',
    marginTop: 8,
  },
  outputName: {
    fontSize: 15,
    fontWeight: '600',
    color: '#333',
    marginBottom: 4,
  },
  outputDetail: {
    fontSize: 14,
    color: '#666',
  },
  outputDefect: {
    fontSize: 14,
    color: '#f44336',
  },
  remainderItem: {
    paddingVertical: 8,
    borderTopWidth: 1,
    borderTopColor: '#e0e0e0',
    marginTop: 8,
  },
  remainderName: {
    fontSize: 15,
    fontWeight: '600',
    color: '#333',
    marginBottom: 4,
  },
  remainderDetail: {
    fontSize: 14,
    color: '#666',
  },
  remainderDesc: {
    fontSize: 13,
    color: '#999',
    fontStyle: 'italic',
  },
  wasteItem: {
    paddingVertical: 8,
    borderTopWidth: 1,
    borderTopColor: '#e0e0e0',
    marginTop: 8,
  },
  wasteWeight: {
    fontSize: 14,
    fontWeight: '600',
    color: '#f44336',
    marginBottom: 4,
  },
  wasteDesc: {
    fontSize: 13,
    color: '#999',
    fontStyle: 'italic',
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
    maxHeight: '85%',
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
  skuList: {
    maxHeight: 150,
    marginBottom: 16,
  },
  skuCard: {
    backgroundColor: '#f5f5f5',
    padding: 12,
    borderRadius: 8,
    borderWidth: 2,
    borderColor: '#e0e0e0',
    marginBottom: 8,
  },
  skuCardSelected: {
    borderColor: '#4CAF50',
    backgroundColor: '#E8F5E9',
  },
  skuName: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
    marginBottom: 4,
  },
  skuWeight: {
    fontSize: 13,
    color: '#666',
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
