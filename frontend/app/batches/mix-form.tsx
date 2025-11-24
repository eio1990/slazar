import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  TextInput,
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Toast from 'react-native-toast-message';

const API_URL = process.env.EXPO_PUBLIC_BACKEND_URL || 'http://localhost:8001';

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

  // Get all stock balances
  const { data: stockBalances } = useQuery({
    queryKey: ['stock-balances'],
    queryFn: async () => {
      const response = await fetch(`${API_URL}/api/stock/balances`);
      if (!response.ok) return [];
      return response.json();
    },
  });

  // Get warehouse mix balance
  const warehouseBalance = stockBalances?.find(
    (b: any) => b.nomenclature_id === parseInt(mixId as string)
  )?.quantity || 0;

  // Helper to get stock for a nomenclature
  const getStock = (nomenclatureId: number) => {
    return stockBalances?.find((b: any) => b.nomenclature_id === nomenclatureId)?.quantity || 0;
  };

  // Calculate recommended quantity for each spice based on batch weight
  const getRecommendedQuantity = (quantityPer100kg: number) => {
    if (!batch?.initial_weight) return 0;
    return (batch.initial_weight * quantityPer100kg) / 100;
  };

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

      // Then, record mix production
      const response = await fetch(
        `${API_URL}/api/production/batches/${batchId}/steps/${stepId}/mix`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(mixData),
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to produce mix');
      }

      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['batch', batchId] });
      queryClient.invalidateQueries({ queryKey: ['stock-balances'] });
      
      Toast.show({
        type: 'success',
        text1: 'Виробництво мікса завершено!',
        text2: 'Чаман успішно виготовлено',
        position: 'top',
        visibilityTime: 3000,
      });

      setTimeout(() => {
        router.push('/(tabs)/production' as any);
      }, 500);
    },
    onError: (error: any) => {
      Toast.show({
        type: 'error',
        text1: 'Помилка',
        text2: error.message || 'Не вдалося виготовити мікс',
        position: 'top',
        visibilityTime: 4000,
      });
    },
  });

  // Calculate fenugreek quantity and required water
  const calculateFenugreek = () => {
    return parseFloat(spiceQuantities[FENUGREEK_ID] || '0');
  };

  // Calculate total produced mix (with water)
  const calculateProducedMix = () => {
    const totalSpices = Object.values(spiceQuantities)
      .reduce((sum, qty) => sum + parseFloat(qty || '0'), 0);
    
    const fenugreekQty = calculateFenugreek();
    const waterQty = fenugreekQty * WATER_RATIO;
    
    return totalSpices + waterQty;
  };

  // Calculate used mix
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
      Toast.show({
        type: 'error',
        text1: 'Помилка',
        text2: 'Введіть кількість специй або складського мікса',
        position: 'top',
        visibilityTime: 3000,
      });
      return;
    }

    if (leftoverQty > producedMix) {
      Toast.show({
        type: 'error',
        text1: 'Помилка',
        text2: 'Залишок не може перевищувати вироблений мікс',
        position: 'top',
        visibilityTime: 3000,
      });
      return;
    }

    if (warehouseQty > (warehouseBalance || 0)) {
      Toast.show({
        type: 'error',
        text1: 'Помилка',
        text2: `На складі недостатньо мікса. Доступно: ${warehouseBalance?.toFixed(2) || 0} кг`,
        position: 'top',
        visibilityTime: 4000,
      });
      return;
    }

    // Check if all spices are available in stock
    for (const [nomenclatureId, qty] of Object.entries(spiceQuantities)) {
      const neededQty = parseFloat(qty || '0');
      if (neededQty > 0) {
        const stockQty = getStock(parseInt(nomenclatureId));
        if (stockQty < neededQty) {
          const spice = recipeData?.spices?.find((s: Spice) => s.nomenclature_id === parseInt(nomenclatureId));
          Toast.show({
            type: 'error',
            text1: 'Недостатньо специй на складі!',
            text2: `${spice?.name}: потрібно ${neededQty.toFixed(2)} кг, на складі ${stockQty.toFixed(2)} кг`,
            position: 'top',
            visibilityTime: 4000,
          });
          return;
        }
      }
    }

    Toast.show({
      type: 'info',
      text1: 'Обробка...',
      text2: 'Виготовлення мікса',
      position: 'top',
      visibilityTime: 2000,
    });

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
  const fenugreekQuantity = calculateFenugreek();
  const requiredWater = fenugreekQuantity * WATER_RATIO;

  return (
    <KeyboardAvoidingView 
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <ScrollView style={styles.scrollView} contentContainerStyle={styles.scrollContent}>
        {/* Header */}
        <View style={styles.header}>
          <TouchableOpacity onPress={() => router.push('/(tabs)/production' as any)} style={styles.backButton}>
            <MaterialCommunityIcons name="arrow-left" size={24} color="#333" />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>Виробництво чаману</Text>
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
              <Text style={styles.infoValue}>{batch?.initial_weight?.toFixed(2)} кг</Text>
            </View>
          </View>
        </View>

        {/* Spices Section */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Специї для чаману</Text>
          <View style={styles.formCard}>
            {recipeData?.spices?.map((spice: Spice, index: number) => (
              <View key={spice.id}>
                {index > 0 && <View style={styles.divider} />}
                
                <View style={styles.spiceSection}>
                  <View style={styles.labelRow}>
                    <View style={styles.spiceLabelContainer}>
                      <MaterialCommunityIcons 
                        name={spice.is_fenugreek ? "leaf" : "shaker-outline"} 
                        size={20} 
                        color={spice.is_fenugreek ? "#FF9800" : "#666"} 
                      />
                      <Text style={styles.label}>{spice.name} (кг) *</Text>
                    </View>
                    <Text style={styles.recommendedText}>
                      {getRecommendedQuantity(spice.quantity_per_100kg).toFixed(2)} кг
                    </Text>
                  </View>
                  
                  {spice.is_fenugreek && (
                    <Text style={styles.fenugreekNote}>
                      ⚠️ До пажитника автоматично додається вода (1:4)
                    </Text>
                  )}
                  
                  <Text style={styles.stockHint}>
                    На складі: {getStock(spice.nomenclature_id).toFixed(2)} кг
                  </Text>
                  
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
                    placeholder="Введіть кількість"
                    placeholderTextColor="#999"
                  />
                </View>
              </View>
            ))}
          </View>
        </View>

        {/* Water Calculation */}
        {fenugreekQuantity > 0 && (
          <View style={styles.section}>
            <View style={styles.waterCard}>
              <MaterialCommunityIcons name="water" size={32} color="#2196F3" />
              <View style={styles.waterInfo}>
                <Text style={styles.waterTitle}>Автоматично додається вода</Text>
                <Text style={styles.waterAmount}>{requiredWater.toFixed(2)} л</Text>
                <Text style={styles.waterFormula}>
                  {fenugreekQuantity.toFixed(2)} кг пажитника × 4 = {requiredWater.toFixed(2)} л
                </Text>
              </View>
            </View>
          </View>
        )}

        {/* Mix Calculation */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Розрахунок мікса</Text>
          <View style={styles.calculationCard}>
            <View style={styles.calculationRow}>
              <Text style={styles.calculationLabel}>Вироблено мікса:</Text>
              <Text style={styles.calculationValue}>{producedMix.toFixed(2)} кг</Text>
            </View>
            
            <View style={styles.divider} />
            
            <Text style={styles.label}>Залишок мікса (кг)</Text>
            <Text style={styles.hint}>Мікс що залишився після нанесення</Text>
            <TextInput
              style={styles.input}
              value={leftover}
              onChangeText={setLeftover}
              keyboardType="decimal-pad"
              placeholder="0"
              placeholderTextColor="#999"
            />

            <View style={[styles.checkboxContainer, { marginTop: 16 }]}>
              <TouchableOpacity
                style={styles.checkbox}
                onPress={() => setUseWarehouseMix(!useWarehouseMix)}
              >
                <MaterialCommunityIcons
                  name={useWarehouseMix ? "checkbox-marked" : "checkbox-blank-outline"}
                  size={24}
                  color={useWarehouseMix ? "#4CAF50" : "#999"}
                />
              </TouchableOpacity>
              <Text style={styles.checkboxLabel}>Використати мікс зі складу</Text>
            </View>

            {useWarehouseMix && (
              <>
                <Text style={[styles.label, { marginTop: 12 }]}>Складський мікс (кг)</Text>
                <Text style={styles.stockHint}>На складі: {warehouseBalance.toFixed(2)} кг</Text>
                <TextInput
                  style={styles.input}
                  value={warehouseMixUsed}
                  onChangeText={setWarehouseMixUsed}
                  keyboardType="decimal-pad"
                  placeholder="0"
                  placeholderTextColor="#999"
                />
              </>
            )}

            <View style={[styles.divider, { marginVertical: 16 }]} />
            
            <View style={styles.calculationRow}>
              <Text style={styles.totalLabel}>Використано мікса:</Text>
              <Text style={styles.totalValue}>{usedMix.toFixed(2)} кг</Text>
            </View>
          </View>
        </View>

        {/* Submit Button */}
        <TouchableOpacity
          style={[styles.submitButton, produceMixMutation.isPending && styles.submitButtonDisabled]}
          onPress={handleSubmit}
          disabled={produceMixMutation.isPending}
        >
          {produceMixMutation.isPending ? (
            <ActivityIndicator color="#FFF" />
          ) : (
            <>
              <MaterialCommunityIcons name="check-circle" size={20} color="#FFF" />
              <Text style={styles.submitButtonText}>Виготовити чаман</Text>
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
  centerContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
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
    padding: 8,
    width: 40,
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
    marginBottom: 8,
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
  spiceSection: {
    marginBottom: 8,
  },
  labelRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 4,
  },
  spiceLabelContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  label: {
    fontSize: 14,
    fontWeight: '500',
    color: '#333',
  },
  recommendedText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#f44336',
  },
  fenugreekNote: {
    fontSize: 12,
    color: '#FF9800',
    marginBottom: 6,
    fontStyle: 'italic',
  },
  stockHint: {
    fontSize: 12,
    color: '#2196F3',
    marginBottom: 6,
    fontStyle: 'italic',
  },
  hint: {
    fontSize: 12,
    color: '#999',
    marginBottom: 6,
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
  divider: {
    height: 1,
    backgroundColor: '#E0E0E0',
    marginVertical: 12,
  },
  waterCard: {
    backgroundColor: '#E3F2FD',
    borderRadius: 12,
    padding: 16,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  waterInfo: {
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
    color: '#0D47A1',
    marginBottom: 4,
  },
  waterFormula: {
    fontSize: 12,
    color: '#1976D2',
    fontStyle: 'italic',
  },
  calculationCard: {
    backgroundColor: '#FFF',
    borderRadius: 12,
    padding: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  calculationRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  calculationLabel: {
    fontSize: 14,
    color: '#666',
  },
  calculationValue: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
  },
  totalLabel: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
  },
  totalValue: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#4CAF50',
  },
  checkboxContainer: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  checkbox: {
    marginRight: 8,
  },
  checkboxLabel: {
    fontSize: 14,
    color: '#333',
  },
  submitButton: {
    backgroundColor: '#4CAF50',
    borderRadius: 12,
    padding: 16,
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    marginHorizontal: 16,
    marginTop: 24,
    gap: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.2,
    shadowRadius: 4,
    elevation: 4,
  },
  submitButtonDisabled: {
    backgroundColor: '#9E9E9E',
  },
  submitButtonText: {
    color: '#FFF',
    fontSize: 16,
    fontWeight: '600',
  },
});
