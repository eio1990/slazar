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
  Platform,
} from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Constants from 'expo-constants';

const API_URL = Constants.expoConfig?.extra?.EXPO_PUBLIC_BACKEND_URL || 'http://localhost:8001';

const FENUGREEK_ID = 19; // Пажитник
const WATER_RATIO = 4; // 1:4 rule

interface Spice {
  id: number;
  nomenclature_id: number;
  name: string;
  quantity_per_100kg: number;
  is_fenugreek: boolean;
}

export default function MixFormScreen() {
  const router = useRouter();
  const { batchId, stepId, recipeId, mixId } = useLocalSearchParams();
  const queryClient = useQueryClient();
  
  const [spiceQuantities, setSpiceQuantities] = useState<Record<number, string>>({});
  const [leftover, setLeftover] = useState('0');
  const [warehouseMixUsed, setWarehouseMixUsed] = useState('0');
  const [useWarehouseMix, setUseWarehouseMix] = useState(false);

  // Get batch details
  const { data: batch } = useQuery({
    queryKey: ['batch', batchId],
    queryFn: async () => {
      const response = await fetch(`${API_URL}/api/production/batches/${batchId}`);
      if (!response.ok) throw new Error('Failed to fetch batch');
      return response.json();
    },
  });

  // Get spices for recipe
  const { data: recipeData, isLoading } = useQuery({
    queryKey: ['recipe-spices', recipeId],
    queryFn: async () => {
      const response = await fetch(`${API_URL}/api/production/recipes/${recipeId}/spices`);
      if (!response.ok) throw new Error('Failed to fetch spices');
      return response.json();
    },
    enabled: !!recipeId,
  });

  // Get warehouse mix balance
  const { data: warehouseBalance } = useQuery({
    queryKey: ['stock-balance', mixId],
    queryFn: async () => {
      const response = await fetch(`${API_URL}/api/stock/balances`);
      if (!response.ok) return 0;
      const balances = await response.json();
      const mix = balances.find((b: any) => b.nomenclature_id === parseInt(mixId as string));
      return mix ? parseFloat(mix.quantity) : 0;
    },
    enabled: !!mixId,
  });

  const produceMixMutation = useMutation({
    mutationFn: async (mixData: any) => {
      // First, consume spices
      const materials = Object.entries(spiceQuantities)
        .filter(([_, qty]) => parseFloat(qty || '0') > 0)
        .map(([id, qty]) => ({
          nomenclature_id: parseInt(id),
          quantity: parseFloat(qty),
          type: 'spice'
        }));

      if (materials.length > 0) {
        await fetch(`${API_URL}/api/production/batches/${batchId}/materials/consume`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            materials,
            idempotency_key: `spices-${batchId}-${Date.now()}`
          }),
        });
      }

      // Then produce mix
      const response = await fetch(`${API_URL}/api/production/batches/${batchId}/mix`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(mixData),
      });
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to produce mix');
      }
      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['batch', batchId] });
      queryClient.invalidateQueries({ queryKey: ['batch-operations', batchId] });
      Alert.alert('Успіх', 'Мікс виготовлено', [
        { text: 'OK', onPress: () => router.back() }
      ]);
    },
    onError: (error: any) => {
      Alert.alert('Помилка', error.message || 'Не вдалося виготовити мікс');
    },
  });

  const calculateProducedMix = () => {
    let total = 0;
    let fenugreekWeight = 0;

    recipeData?.spices?.forEach((spice: Spice) => {
      const quantity = parseFloat(spiceQuantities[spice.nomenclature_id] || '0');
      if (spice.nomenclature_id === FENUGREEK_ID || spice.is_fenugreek) {
        fenugreekWeight = quantity;
      } else {
        total += quantity;
      }
    });

    // Add fenugreek and its water (1:4)
    if (fenugreekWeight > 0) {
      total += fenugreekWeight + (fenugreekWeight * WATER_RATIO);
    }

    return total;
  };

  const calculateUsedMix = () => {
    const produced = calculateProducedMix();
    const leftoverQty = parseFloat(leftover || '0');
    const warehouseQty = parseFloat(warehouseMixUsed || '0');
    return produced - leftoverQty + warehouseQty;
  };

  const handleSubmit = () => {
    const producedMix = calculateProducedMix();
    const usedMix = calculateUsedMix();
    const leftoverQty = parseFloat(leftover || '0');
    const warehouseQty = parseFloat(warehouseMixUsed || '0');

    if (producedMix === 0 && warehouseQty === 0) {
      Alert.alert('Помилка', 'Введіть кількість специй або складського мікса');
      return;
    }

    if (leftoverQty > producedMix) {
      Alert.alert('Помилка', 'Залишок не може перевищувати вироблений мікс');
      return;
    }

    if (warehouseQty > (warehouseBalance || 0)) {
      Alert.alert('Помилка', `На складі недостатньо мікса. Доступно: ${warehouseBalance?.toFixed(2) || 0} кг`);
      return;
    }

    produceMixMutation.mutate({
      mix_nomenclature_id: parseInt(mixId as string),
      produced_quantity: producedMix,
      used_quantity: usedMix,
      leftover_quantity: leftoverQty,
      warehouse_mix_used: warehouseQty,
      idempotency_key: `mix-${batchId}-${Date.now()}`,
    });
  };

  if (isLoading) {
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator size="large" color="#4CAF50" />
      </View>
    );
  }

  const producedMix = calculateProducedMix();
  const usedMix = calculateUsedMix();
  const fenugreekQuantity = parseFloat(spiceQuantities[FENUGREEK_ID] || '0');
  const requiredWater = fenugreekQuantity * WATER_RATIO;

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity style={styles.backButton} onPress={() => router.back()}>
          <MaterialCommunityIcons name="arrow-left" size={24} color="#fff" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Виробництво мікса</Text>
        <View style={styles.placeholder} />
      </View>

      <ScrollView style={styles.content}>
        {/* Batch Info */}
        <View style={styles.infoCard}>
          <Text style={styles.batchNumber}>Партія: {batch?.batch_number}</Text>
        </View>

        {/* Spices List */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Специї</Text>
          
          {recipeData?.spices?.map((spice: Spice) => (
            <View key={spice.id} style={styles.spiceCard}>
              <View style={styles.spiceHeader}>
                <MaterialCommunityIcons 
                  name={spice.is_fenugreek ? "leaf" : "shaker-outline"} 
                  size={24} 
                  color={spice.is_fenugreek ? "#FF9800" : "#666"} 
                />
                <View style={styles.spiceInfo}>
                  <Text style={styles.spiceName}>{spice.name}</Text>
                  {spice.is_fenugreek && (
                    <Text style={styles.fenugreekNote}>
                      ⚠️ Додається вода 1:4
                    </Text>
                  )}
                </View>
              </View>
              
              <TextInput
                style={styles.input}
                value={spiceQuantities[spice.nomenclature_id] || ''}
                onChangeText={(text) => 
                  setSpiceQuantities(prev => ({
                    ...prev,
                    [spice.nomenclature_id]: text
                  }))
                }
                keyboardType="decimal-pad"
                placeholder="Введіть вагу (кг)"
              />
            </View>
          ))}
        </View>

        {/* Water Calculation */}
        {fenugreekQuantity > 0 && (
          <View style={styles.waterCard}>
            <MaterialCommunityIcons name="water" size={24} color="#2196F3" />
            <View style={styles.waterInfo}>
              <Text style={styles.waterTitle}>Автоматично додається вода</Text>
              <Text style={styles.waterAmount}>{requiredWater.toFixed(2)} л</Text>
              <Text style={styles.waterFormula}>
                {fenugreekQuantity.toFixed(2)} кг пажитника × 4 = {requiredWater.toFixed(2)} л
              </Text>
            </View>
          </View>
        )}

        {/* Mix Calculation */}
        <View style={styles.calculationCard}>
          <Text style={styles.calculationTitle}>Розрахунок мікса</Text>
          
          <View style={styles.calculationRow}>
            <Text style={styles.calculationLabel}>Вироблено мікса:</Text>
            <Text style={styles.calculationValue}>{producedMix.toFixed(2)} кг</Text>
          </View>
          
          <View style={styles.divider} />
          
          <View style={styles.inputRow}>
            <Text style={styles.label}>Залишок мікса (leftover):</Text>
            <TextInput
              style={styles.smallInput}
              value={leftover}
              onChangeText={setLeftover}
              keyboardType="decimal-pad"
              placeholder="0"
            />
          </View>
          
          <View style={styles.checkboxContainer}>
            <TouchableOpacity
              style={styles.checkbox}
              onPress={() => setUseWarehouseMix(!useWarehouseMix)}
            >
              <MaterialCommunityIcons
                name={useWarehouseMix ? 'checkbox-marked' : 'checkbox-blank-outline'}
                size={24}
                color="#4CAF50"
              />
              <Text style={styles.checkboxLabel}>
                Використати складський мікс (доступно: {warehouseBalance?.toFixed(2) || 0} кг)
              </Text>
            </TouchableOpacity>
          </View>
          
          {useWarehouseMix && (
            <View style={styles.inputRow}>
              <Text style={styles.label}>Вага складського мікса:</Text>
              <TextInput
                style={styles.smallInput}
                value={warehouseMixUsed}
                onChangeText={setWarehouseMixUsed}
                keyboardType="decimal-pad"
                placeholder="0"
              />
            </View>
          )}
          
          <View style={styles.divider} />
          
          <View style={styles.calculationRow}>
            <Text style={styles.calculationLabelBold}>Використано мікса:</Text>
            <Text style={styles.calculationValueBold}>{usedMix.toFixed(2)} кг</Text>
          </View>
          
          <Text style={styles.formula}>
            = ({producedMix.toFixed(2)} - {leftover || '0'}) + {warehouseMixUsed || '0'}
          </Text>
        </View>

        {/* Submit Button */}
        <TouchableOpacity
          style={[styles.submitButton, produceMixMutation.isPending && styles.submitButtonDisabled]}
          onPress={handleSubmit}
          disabled={produceMixMutation.isPending}
        >
          {produceMixMutation.isPending ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <>
              <MaterialCommunityIcons name="check-circle" size={20} color="#fff" />
              <Text style={styles.submitButtonText}>Виготовити мікс</Text>
            </>
          )}
        </TouchableOpacity>
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
  batchNumber: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
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
  spiceCard: {
    backgroundColor: '#fff',
    padding: 12,
    borderRadius: 8,
    marginBottom: 12,
    ...Platform.select({
      ios: {
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 1 },
        shadowOpacity: 0.05,
        shadowRadius: 2,
      },
      android: {
        elevation: 1,
      },
      web: {
        boxShadow: '0 1px 2px rgba(0,0,0,0.05)',
      },
    }),
  },
  spiceHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  spiceInfo: {
    marginLeft: 12,
    flex: 1,
  },
  spiceName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
  },
  fenugreekNote: {
    fontSize: 12,
    color: '#FF9800',
    marginTop: 2,
  },
  input: {
    borderWidth: 1,
    borderColor: '#e0e0e0',
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 16,
    backgroundColor: '#fff',
  },
  waterCard: {
    flexDirection: 'row',
    backgroundColor: '#E3F2FD',
    marginHorizontal: 16,
    marginBottom: 24,
    padding: 16,
    borderRadius: 12,
    borderWidth: 2,
    borderColor: '#2196F3',
  },
  waterInfo: {
    marginLeft: 12,
    flex: 1,
  },
  waterTitle: {
    fontSize: 14,
    fontWeight: '600',
    color: '#1976D2',
    marginBottom: 4,
  },
  waterAmount: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#2196F3',
    marginBottom: 4,
  },
  waterFormula: {
    fontSize: 12,
    color: '#1976D2',
  },
  calculationCard: {
    backgroundColor: '#fff',
    marginHorizontal: 16,
    marginBottom: 24,
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
  calculationTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 12,
  },
  calculationRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  calculationLabel: {
    fontSize: 14,
    color: '#666',
  },
  calculationValue: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
  },
  calculationLabelBold: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333',
  },
  calculationValueBold: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#4CAF50',
  },
  divider: {
    height: 1,
    backgroundColor: '#e0e0e0',
    marginVertical: 12,
  },
  inputRow: {
    marginBottom: 12,
  },
  label: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
    marginBottom: 8,
  },
  smallInput: {
    borderWidth: 1,
    borderColor: '#e0e0e0',
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 8,
    fontSize: 16,
    backgroundColor: '#fff',
  },
  checkboxContainer: {
    marginBottom: 12,
  },
  checkbox: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  checkboxLabel: {
    fontSize: 14,
    color: '#333',
    marginLeft: 8,
    flex: 1,
  },
  formula: {
    fontSize: 12,
    color: '#999',
    fontStyle: 'italic',
    marginTop: 4,
  },
  submitButton: {
    flexDirection: 'row',
    backgroundColor: '#4CAF50',
    marginHorizontal: 16,
    marginBottom: 32,
    paddingVertical: 14,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
  },
  submitButtonDisabled: {
    opacity: 0.6,
  },
  submitButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
    marginLeft: 8,
  },
});
