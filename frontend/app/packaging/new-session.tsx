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
import { useRouter } from 'expo-router';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

const API_URL = process.env.EXPO_PUBLIC_BACKEND_URL || 'http://localhost:8001';

export default function NewPackagingSessionScreen() {
  const router = useRouter();
  const queryClient = useQueryClient();

  const [selectedProduct, setSelectedProduct] = useState<any>(null);
  const [sourceWeight, setSourceWeight] = useState('');
  const [notes, setNotes] = useState('');

  // Get nomenclature for source products (finished bulk products)
  const { data: products, isLoading: productsLoading } = useQuery({
    queryKey: ['nomenclature-bulk-products'],
    queryFn: async () => {
      const response = await fetch(`${API_URL}/api/nomenclature`);
      if (!response.ok) throw new Error('Failed to fetch products');
      const allNomenclature = await response.json();
      // Filter for bulk finished products (category "Готова продукція")
      return allNomenclature.filter((n: any) => 
        n.category === 'Готова продукція' && n.name.includes('вагова')
      );
    },
  });

  // Get stock balances
  const { data: balances } = useQuery({
    queryKey: ['stock-balances'],
    queryFn: async () => {
      const response = await fetch(`${API_URL}/api/stock/balances`);
      if (!response.ok) throw new Error('Failed to fetch balances');
      return response.json();
    },
  });

  // Create session mutation
  const createSessionMutation = useMutation({
    mutationFn: async (sessionData: any) => {
      const response = await fetch(`${API_URL}/api/packaging/sessions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(sessionData),
      });
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to create session');
      }
      return response.json();
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['packaging-sessions'] });
      Alert.alert('Успіх', `Сесію фасування створено: ${data.session_number}`, [
        { text: 'OK', onPress: () => router.replace(`/packaging/${data.session_id}` as any) }
      ]);
    },
    onError: (error: any) => {
      Alert.alert('Помилка', error.message || 'Не вдалося створити сесію');
    },
  });

  const handleSubmit = () => {
    if (!selectedProduct) {
      Alert.alert('Помилка', 'Оберіть вихідний продукт');
      return;
    }

    const weight = parseFloat(sourceWeight);
    if (!sourceWeight || isNaN(weight) || weight <= 0) {
      Alert.alert('Помилка', 'Введіть коректну вагу продукту');
      return;
    }

    const sessionData = {
      source_product_id: selectedProduct.id,
      source_weight_taken: weight,
      notes: notes || null,
    };

    createSessionMutation.mutate(sessionData);
  };

  const getProductBalance = (productId: number) => {
    if (!balances) return 0;
    const balance = balances.find((b: any) => b.nomenclature_id === productId);
    return balance ? balance.quantity : 0;
  };

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      style={styles.container}
    >
      <ScrollView style={styles.container} contentContainerStyle={styles.content}>
        {/* Header */}
        <View style={styles.header}>
          <TouchableOpacity onPress={() => router.push('/(tabs)/packaging' as any)} style={styles.backButton}>
            <MaterialCommunityIcons name="arrow-left" size={24} color="#007AFF" />
          </TouchableOpacity>
          <Text style={styles.title}>Нова сесія фасування</Text>
        </View>

        <Text style={styles.description}>
          Оберіть весовий продукт та введіть вагу, яку берете для фасування.{'\n'}
          В одній сесії можна буде фасувати у різні SKU.
        </Text>

        {/* Product Selection */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Вихідний продукт *</Text>
          
          {productsLoading ? (
            <ActivityIndicator color="#007AFF" />
          ) : !products || products.length === 0 ? (
            <Text style={styles.emptyText}>Весові продукти не знайдено</Text>
          ) : (
            <View style={styles.productList}>
              {products.map((product: any) => {
                const balance = getProductBalance(product.id);
                return (
                  <TouchableOpacity
                    key={product.id}
                    style={[
                      styles.productCard,
                      selectedProduct?.id === product.id && styles.productCardSelected,
                    ]}
                    onPress={() => setSelectedProduct(product)}
                  >
                    <View style={styles.productHeader}>
                      <Text style={styles.productName}>{product.name}</Text>
                      {selectedProduct?.id === product.id && (
                        <MaterialCommunityIcons name="check-circle" size={24} color="#4CAF50" />
                      )}
                    </View>
                    <Text style={styles.productBalance}>
                      На складі: {balance.toFixed(2)} {product.unit}
                    </Text>
                  </TouchableOpacity>
                );
              })}
            </View>
          )}
        </View>

        {/* Source Weight */}
        <View style={styles.section}>
          <Text style={styles.label}>Вага взятого продукту (кг) *</Text>
          {selectedProduct && (
            <Text style={styles.hint}>
              Доступно: {getProductBalance(selectedProduct.id).toFixed(2)} кг
            </Text>
          )}
          <TextInput
            style={styles.input}
            value={sourceWeight}
            onChangeText={setSourceWeight}
            placeholder="напр. 10.5"
            keyboardType="decimal-pad"
          />
        </View>

        {/* Notes */}
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

        {/* Submit Button */}
        <TouchableOpacity
          style={[
            styles.submitButton,
            createSessionMutation.isPending && styles.submitButtonDisabled,
          ]}
          onPress={handleSubmit}
          disabled={createSessionMutation.isPending}
        >
          {createSessionMutation.isPending ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <>
              <MaterialCommunityIcons name="package-variant-closed" size={20} color="#fff" />
              <Text style={styles.submitButtonText}>Створити сесію</Text>
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
    backgroundColor: '#f5f5f5',
  },
  content: {
    padding: 16,
    paddingBottom: 32,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 16,
  },
  backButton: {
    marginRight: 12,
    padding: 4,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#333',
  },
  description: {
    fontSize: 14,
    color: '#666',
    marginBottom: 24,
    lineHeight: 20,
  },
  section: {
    marginBottom: 24,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333',
    marginBottom: 12,
  },
  emptyText: {
    fontSize: 14,
    color: '#999',
    textAlign: 'center',
    padding: 20,
  },
  productList: {
    gap: 12,
  },
  productCard: {
    backgroundColor: '#fff',
    padding: 16,
    borderRadius: 12,
    borderWidth: 2,
    borderColor: '#e0e0e0',
  },
  productCardSelected: {
    borderColor: '#4CAF50',
    backgroundColor: '#E8F5E9',
  },
  productHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  productName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
    flex: 1,
  },
  productBalance: {
    fontSize: 14,
    color: '#666',
  },
  label: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
    marginBottom: 8,
  },
  hint: {
    fontSize: 12,
    color: '#4CAF50',
    marginBottom: 8,
  },
  input: {
    backgroundColor: '#fff',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#ddd',
    padding: 12,
    fontSize: 16,
    color: '#333',
  },
  textArea: {
    backgroundColor: '#fff',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#ddd',
    padding: 12,
    fontSize: 16,
    color: '#333',
    minHeight: 80,
    textAlignVertical: 'top',
  },
  submitButton: {
    backgroundColor: '#007AFF',
    borderRadius: 12,
    padding: 16,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    marginTop: 8,
  },
  submitButtonDisabled: {
    backgroundColor: '#ccc',
  },
  submitButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
});
