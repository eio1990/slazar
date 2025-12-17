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

export default function MarinadeFormScreen() {
  const router = useRouter();
  const { batchId, stepId, recipeId, marinadeType } = useLocalSearchParams();
  const queryClient = useQueryClient();

  const [producedQty, setProducedQty] = useState('');
  const [usedQty, setUsedQty] = useState('');
  const [leftoverQty, setLeftoverQty] = useState('');
  const [warehouseUsed, setWarehouseUsed] = useState('0');
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

  // Get marinade spices from recipe
  const { data: spices, isLoading: spicesLoading } = useQuery({
    queryKey: ['recipe-spices', recipeId],
    queryFn: async () => {
      const response = await fetch(`${API_URL}/api/production/recipes/${recipeId}/spices`);
      if (!response.ok) throw new Error('Failed to fetch spices');
      return response.json();
    },
  });

  // Get stock balances
  const { data: stockBalances } = useQuery({
    queryKey: ['stock-balances'],
    queryFn: async () => {
      const response = await fetch(`${API_URL}/api/stock/balances`);
      if (!response.ok) return [];
      return response.json();
    },
  });

  const getStock = (nomenclatureId: number) => {
    return stockBalances?.find((b: any) => b.nomenclature_id === nomenclatureId)?.quantity || 0;
  };

  // Get warehouse marinade balance
  const { data: warehouseBalance } = useQuery({
    queryKey: ['warehouse-marinade'],
    queryFn: async () => {
      // ID маринаду залежить від типу (для конини 41, для інших - інші)
      const marinadeId = marinadeType === 'horse' ? 41 : 40;
      const response = await fetch(`${API_URL}/api/stock/balance/${marinadeId}`);
      if (!response.ok) return { balance: 0 };
      return response.json();
    },
  });

  const produceMarinادeMutation = useMutation({
    mutationFn: async (marinadeData: any) => {
      // Використовуємо той самий endpoint /mix, але з marinade параметрами
      const response = await fetch(`${API_URL}/api/production/batches/${batchId}/mix`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(marinadeData),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to produce marinade');
      }
      return response.json();
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['batch', batchId] });
      queryClient.invalidateQueries({ queryKey: ['batch-operations', batchId] });
      
      Alert.alert('Успіх', 'Маринад виготовлено успішно!', [
        { text: 'OK', onPress: () => router.push('/(tabs)/production' as any) }
      ]);
    },
    onError: (error: any) => {
      Alert.alert('Помилка', error.message);
    },
  });

  const handleAutoCalculate = () => {
    if (!spices || spices.length === 0) return;

    const initialWeight = batch?.initial_weight || 100;
    
    // Розрахунок загальної кількості специй
    let totalSpices = 0;
    let waterFromFenugreek = 0;
    
    spices.forEach((spice: any) => {
      const qty = (initialWeight / 100) * spice.quantity_per_100kg;
      totalSpices += qty;
      
      // Пажитник 1:4
      if (spice.spice_name?.toLowerCase().includes('пажитник')) {
        waterFromFenugreek = qty * 4;
      }
    });

    const totalProduced = totalSpices + waterFromFenugreek;
    
    setProducedQty(totalProduced.toFixed(2));
    // За замовчуванням використовуємо 95%, 5% залишок
    setUsedQty((totalProduced * 0.95).toFixed(2));
    setLeftoverQty((totalProduced * 0.05).toFixed(2));
  };

  const handleSubmit = () => {
    const produced = parseFloat(producedQty);
    const used = parseFloat(usedQty);
    const leftover = parseFloat(leftoverQty);
    const warehouse = parseFloat(warehouseUsed);

    if (isNaN(produced) || produced <= 0) {
      Alert.alert('Помилка', 'Введіть кількість виробленого маринаду');
      return;
    }

    if (isNaN(used) || used < 0) {
      Alert.alert('Помилка', 'Введіть кількість використаного маринаду');
      return;
    }

    if (isNaN(leftover) || leftover < 0) {
      Alert.alert('Помилка', 'Введіть кількість залишку');
      return;
    }

    // Перевірка балансу
    const balance = produced + warehouse - used - leftover;
    if (Math.abs(balance) > 0.1) {
      Alert.alert('Помилка', `Баланс не сходиться!\n\nВироблено + Зі складу = Використано + Залишок\n${produced.toFixed(2)} + ${warehouse.toFixed(2)} ≠ ${used.toFixed(2)} + ${leftover.toFixed(2)}`);
      return;
    }

    Alert.alert(
      'Підтвердження',
      `Буде списано ВСІ специї з рецепту\n\nВироблено: ${produced.toFixed(2)} кг\nВикористано: ${used.toFixed(2)} кг\nЗалишок: ${leftover.toFixed(2)} кг\n\nПродовжити?`,
      [
        { text: 'Скасувати', style: 'cancel' },
        {
          text: 'Так',
          onPress: () => {
            const marinadeData = {
              produced_quantity: produced,
              used_quantity: used,
              leftover_quantity: leftover,
              warehouse_mix_used: warehouse,
              notes: notes || 'Маринад виготовлено',
              idempotency_key: `marinade-${batchId}-${Date.now()}`,
            };

            produceMarinادeMutation.mutate(marinadeData);
          },
        },
      ]
    );
  };

  if (batchLoading || spicesLoading) {
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
          <TouchableOpacity onPress={() => router.push('/(tabs)/production' as any)} style={styles.backButton}>
            <MaterialCommunityIcons name="arrow-left" size={24} color="#007AFF" />
          </TouchableOpacity>
          <Text style={styles.title}>Виготовлення маринаду</Text>
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
              <Text style={styles.infoLabel}>Вага:</Text>
              <Text style={styles.infoValue}>{batch.initial_weight} кг</Text>
            </View>
          </View>
        )}

        {/* Spices List */}
        {spices && spices.length > 0 && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Специї для маринаду</Text>
            <View style={styles.spicesCard}>
              {spices.map((spice: any, index: number) => {
                const qty = ((batch?.initial_weight || 100) / 100) * spice.quantity_per_100kg;
                return (
                  <View key={index} style={styles.spiceRow}>
                    <Text style={styles.spiceName}>{spice.spice_name}</Text>
                    <Text style={styles.spiceQty}>{qty.toFixed(2)} {spice.unit}</Text>
                  </View>
                );
              })}
            </View>
            
            <TouchableOpacity style={styles.autoButton} onPress={handleAutoCalculate}>
              <MaterialCommunityIcons name="calculator" size={20} color="#007AFF" />
              <Text style={styles.autoButtonText}>Розрахувати автоматично</Text>
            </TouchableOpacity>
          </View>
        )}

        {/* Warehouse Balance */}
        {warehouseBalance && warehouseBalance.balance > 0 && (
          <View style={styles.warehouseCard}>
            <MaterialCommunityIcons name="warehouse" size={20} color="#FF9800" />
            <Text style={styles.warehouseText}>
              На складі готовий маринад: <Text style={styles.warehouseBold}>{warehouseBalance.balance} кг</Text>
            </Text>
          </View>
        )}

        {/* Quantities */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Кількості</Text>

          <View style={styles.inputGroup}>
            <Text style={styles.label}>Вироблено маринаду (кг) *</Text>
            <View style={styles.inputWrapper}>
              <MaterialCommunityIcons name="bottle-tonic-plus" size={20} color="#666" />
              <TextInput
                style={styles.input}
                value={producedQty}
                onChangeText={setProducedQty}
                placeholder="напр. 6.0"
                keyboardType="decimal-pad"
              />
              <Text style={styles.unit}>кг</Text>
            </View>
          </View>

          <View style={styles.inputGroup}>
            <Text style={styles.label}>Використано на партію (кг) *</Text>
            <View style={styles.inputWrapper}>
              <MaterialCommunityIcons name="arrow-down-bold" size={20} color="#666" />
              <TextInput
                style={styles.input}
                value={usedQty}
                onChangeText={setUsedQty}
                placeholder="напр. 5.7"
                keyboardType="decimal-pad"
              />
              <Text style={styles.unit}>кг</Text>
            </View>
          </View>

          <View style={styles.inputGroup}>
            <Text style={styles.label}>Залишок (повернеться на склад) (кг) *</Text>
            <View style={styles.inputWrapper}>
              <MaterialCommunityIcons name="package-variant" size={20} color="#666" />
              <TextInput
                style={styles.input}
                value={leftoverQty}
                onChangeText={setLeftoverQty}
                placeholder="напр. 0.3"
                keyboardType="decimal-pad"
              />
              <Text style={styles.unit}>кг</Text>
            </View>
          </View>

          <View style={styles.inputGroup}>
            <Text style={styles.label}>Використано зі складу (опціонально) (кг)</Text>
            <View style={styles.inputWrapper}>
              <MaterialCommunityIcons name="warehouse" size={20} color="#666" />
              <TextInput
                style={styles.input}
                value={warehouseUsed}
                onChangeText={setWarehouseUsed}
                placeholder="0"
                keyboardType="decimal-pad"
              />
              <Text style={styles.unit}>кг</Text>
            </View>
          </View>
        </View>

        {/* Notes */}
        <View style={styles.section}>
          <Text style={styles.label}>Примітки</Text>
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
            produceMarinادeMutation.isPending && styles.submitButtonDisabled,
          ]}
          onPress={handleSubmit}
          disabled={produceMarinადeMutation.isPending}
        >
          {produceMarinадeMutation.isPending ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <>
              <MaterialCommunityIcons name="check-circle" size={20} color="#fff" />
              <Text style={styles.submitButtonText}>Виготовити маринад</Text>
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
  spicesCard: { backgroundColor: '#fff', borderRadius: 12, padding: 16, marginBottom: 12 },
  spiceRow: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 8 },
  spiceName: { fontSize: 14, color: '#333', flex: 1 },
  spiceQty: { fontSize: 14, fontWeight: '600', color: '#007AFF' },
  autoButton: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', backgroundColor: '#E3F2FD', padding: 12, borderRadius: 8, gap: 8 },
  autoButtonText: { fontSize: 14, fontWeight: '600', color: '#007AFF' },
  warehouseCard: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#FFF3CD', padding: 12, borderRadius: 8, marginBottom: 16, gap: 12 },
  warehouseText: { fontSize: 14, color: '#856404', flex: 1 },
  warehouseBold: { fontWeight: 'bold' },
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
