import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  TextInput,
  Alert,
  Modal,
  FlatList,
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import {
  apiService,
  checkNetworkConnectivity,
  generateIdempotencyKey,
  addToOfflineQueue,
  Nomenclature,
} from '../../services/api';
import { useStore } from '../../stores/useStore';

type OperationType = 'receipt' | 'withdrawal';

export default function OperationsScreen() {
  const { balances, setPendingOperationsCount } = useStore();
  const [operationType, setOperationType] = useState<OperationType>('receipt');
  const [selectedItem, setSelectedItem] = useState<Nomenclature | null>(null);
  const [quantity, setQuantity] = useState('');
  const [pricePerUnit, setPricePerUnit] = useState('');
  const [notes, setNotes] = useState('');
  const [modalVisible, setModalVisible] = useState(false);
  const [nomenclature, setNomenclature] = useState<Nomenclature[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [availableBalance, setAvailableBalance] = useState<number | null>(null);

  useEffect(() => {
    loadNomenclature();
  }, []);

  useEffect(() => {
    if (selectedItem && operationType === 'withdrawal') {
      // Get available balance for selected item
      const balance = balances.find(b => b.nomenclature_id === selectedItem.id);
      setAvailableBalance(balance ? balance.quantity : 0);
    } else {
      setAvailableBalance(null);
    }
  }, [selectedItem, operationType, balances]);

  const loadNomenclature = async () => {
    try {
      setLoading(true);
      const data = await apiService.getNomenclature();
      setNomenclature(data);
    } catch (error) {
      console.error('Error loading nomenclature:', error);
      Alert.alert('Помилка', 'Не вдалося завантажити номенклатуру');
    } finally {
      setLoading(false);
    }
  };

  // Get unique categories
  const categories = Array.from(new Set(nomenclature.map(item => item.category))).sort();

  // Filter and sort nomenclature
  const filteredNomenclature = nomenclature
    .filter(item => {
      const matchesSearch = item.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.category.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesCategory = !selectedCategory || item.category === selectedCategory;
      return matchesSearch && matchesCategory;
    })
    .sort((a, b) => {
      // Finished products go last
      const aIsFinished = a.category === 'Готова продукція';
      const bIsFinished = b.category === 'Готова продукція';
      
      if (aIsFinished && !bIsFinished) return 1;
      if (!aIsFinished && bIsFinished) return -1;
      
      // Alphabetical order within groups
      return a.name.localeCompare(b.name, 'uk');
    });

  const handleSelectItem = (item: Nomenclature) => {
    setSelectedItem(item);
    setModalVisible(false);
    setSearchQuery('');
  };

  const handleSubmit = async () => {
    if (!selectedItem) {
      Alert.alert('Помилка', 'Оберіть номенклатуру');
      return;
    }

    const qty = parseFloat(quantity);
    if (isNaN(qty) || qty <= 0) {
      Alert.alert('Помилка', 'Введіть коректну кількість');
      return;
    }

    // Validate price for receipt
    if (operationType === 'receipt' && pricePerUnit) {
      const price = parseFloat(pricePerUnit);
      if (isNaN(price) || price < 0) {
        Alert.alert('Помилка', 'Введіть коректну ціну');
        return;
      }
    }

    // Check available balance for withdrawal
    if (operationType === 'withdrawal' && availableBalance !== null && qty > availableBalance) {
      Alert.alert(
        'Недостатньо товару',
        `Доступно: ${availableBalance} ${selectedItem.unit}\nЗапитано: ${qty} ${selectedItem.unit}\n\nНа складі недостатньо товару для списання.`,
        [{ text: 'Зрозуміло' }]
      );
      return;
    }

    try {
      setSubmitting(true);
      const isOnline = await checkNetworkConnectivity();
      
      const operation = {
        nomenclature_id: selectedItem.id,
        quantity: qty,
        price_per_unit: operationType === 'receipt' && pricePerUnit ? parseFloat(pricePerUnit) : undefined,
        idempotency_key: generateIdempotencyKey(),
        metadata: notes ? { notes } : undefined,
      };

      if (isOnline) {
        // Process online
        if (operationType === 'receipt') {
          await apiService.receipt(operation);
        } else {
          await apiService.withdrawal(operation);
        }
        Alert.alert(
          'Успіх',
          `${operationType === 'receipt' ? 'Прихід' : 'Розхід'} успішно оброблено`
        );
      } else {
        // Queue for offline processing
        await addToOfflineQueue({
          type: operationType,
          data: operation,
        });
        const { getOfflineQueue: getQueue } = require('../../services/api');
        const currentQueue = await getQueue();
        setPendingOperationsCount(currentQueue.length);
        Alert.alert(
          'Офлайн режим',
          'Операція збережена та буде синхронізована при підключенні до мережі'
        );
      }

      // Reset form
      setSelectedItem(null);
      setQuantity('');
      setPricePerUnit('');
      setNotes('');
      setAvailableBalance(null);
    } catch (error: any) {
      console.error('Error submitting operation:', error);
      Alert.alert(
        'Помилка',
        error.response?.data?.detail || 'Не вдалося обробити операцію'
      );
    } finally {
      setSubmitting(false);
    }
  };

  const renderNomenclatureItem = ({ item }: { item: Nomenclature }) => (
    <TouchableOpacity
      style={styles.nomenclatureItem}
      onPress={() => handleSelectItem(item)}
    >
      <View style={styles.nomenclatureItemContent}>
        <Text style={styles.nomenclatureName}>{item.name}</Text>
        <Text style={styles.nomenclatureCategory}>{item.category}</Text>
      </View>
      <Text style={styles.nomenclatureUnit}>{item.unit}</Text>
    </TouchableOpacity>
  );

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <ScrollView style={styles.scrollView} contentContainerStyle={styles.content}>
        {/* Operation type selector */}
        <View style={styles.typeSelector}>
          <TouchableOpacity
            style={[
              styles.typeButton,
              operationType === 'receipt' && styles.typeButtonActive,
            ]}
            onPress={() => setOperationType('receipt')}
          >
            <MaterialCommunityIcons
              name="arrow-down-bold"
              size={24}
              color={operationType === 'receipt' ? '#fff' : '#4CAF50'}
            />
            <Text
              style={[
                styles.typeButtonText,
                operationType === 'receipt' && styles.typeButtonTextActive,
              ]}
            >
              Прихід
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[
              styles.typeButton,
              operationType === 'withdrawal' && styles.typeButtonActive,
            ]}
            onPress={() => setOperationType('withdrawal')}
          >
            <MaterialCommunityIcons
              name="arrow-up-bold"
              size={24}
              color={operationType === 'withdrawal' ? '#fff' : '#FF5722'}
            />
            <Text
              style={[
                styles.typeButtonText,
                operationType === 'withdrawal' && styles.typeButtonTextActive,
              ]}
            >
              Розхід
            </Text>
          </TouchableOpacity>
        </View>

        {/* Selected item */}
        <View style={styles.formSection}>
          <Text style={styles.label}>Номенклатура *</Text>
          <TouchableOpacity
            style={styles.selectButton}
            onPress={() => setModalVisible(true)}
          >
            <Text style={selectedItem ? styles.selectedText : styles.placeholderText}>
              {selectedItem ? selectedItem.name : 'Оберіть номенклатуру'}
            </Text>
            <MaterialCommunityIcons name="chevron-down" size={24} color="#666" />
          </TouchableOpacity>
          {selectedItem && (
            <Text style={styles.helperText}>
              Категорія: {selectedItem.category} | Од. виміру: {selectedItem.unit}
            </Text>
          )}
        </View>

        {/* Available balance (for withdrawal) */}
        {operationType === 'withdrawal' && selectedItem && availableBalance !== null && (
          <View style={styles.balanceInfo}>
            <MaterialCommunityIcons name="information" size={20} color="#2196F3" />
            <Text style={styles.balanceText}>
              Доступно на складі: <Text style={styles.balanceValue}>{availableBalance} {selectedItem.unit}</Text>
            </Text>
          </View>
        )}

        {/* Quantity input */}
        <View style={styles.formSection}>
          <Text style={styles.label}>Кількість *</Text>
          <TextInput
            style={styles.input}
            placeholder={`Введіть кількість${selectedItem ? ` (${selectedItem.unit})` : ''}`}
            value={quantity}
            onChangeText={setQuantity}
            keyboardType="decimal-pad"
          />
        </View>

        {/* Price per unit (only for receipt) */}
        {operationType === 'receipt' && (
          <View style={styles.formSection}>
            <Text style={styles.label}>Ціна за одиницю (необов'язково)</Text>
            <TextInput
              style={styles.input}
              placeholder={`Ціна за ${selectedItem?.unit || 'одиницю'} (грн)`}
              value={pricePerUnit}
              onChangeText={setPricePerUnit}
              keyboardType="decimal-pad"
            />
          </View>
        )}

        {/* Notes */}
        <View style={styles.formSection}>
          <Text style={styles.label}>Примітки</Text>
          <TextInput
            style={[styles.input, styles.textArea]}
            placeholder="Додаткова інформація (необов'язково)"
            value={notes}
            onChangeText={setNotes}
            multiline
            numberOfLines={3}
          />
        </View>

        {/* Submit button */}
        <TouchableOpacity
          style={[
            styles.submitButton,
            operationType === 'withdrawal' && styles.submitButtonWithdrawal,
            submitting && styles.submitButtonDisabled,
          ]}
          onPress={handleSubmit}
          disabled={submitting}
        >
          {submitting ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <>
              <MaterialCommunityIcons
                name={operationType === 'receipt' ? 'check-circle' : 'arrow-up-bold-circle'}
                size={24}
                color="#fff"
              />
              <Text style={styles.submitButtonText}>
                {operationType === 'receipt' ? 'Оформити прихід' : 'Оформити розхід'}
              </Text>
            </>
          )}
        </TouchableOpacity>
      </ScrollView>

      {/* Nomenclature selection modal */}
      <Modal
        visible={modalVisible}
        animationType="slide"
        onRequestClose={() => setModalVisible(false)}
      >
        <View style={styles.modalContainer}>
          <View style={styles.modalHeader}>
            <Text style={styles.modalTitle}>Оберіть номенклатуру</Text>
            <TouchableOpacity onPress={() => setModalVisible(false)}>
              <MaterialCommunityIcons name="close" size={28} color="#333" />
            </TouchableOpacity>
          </View>

          <View style={styles.modalSearchContainer}>
            <MaterialCommunityIcons name="magnify" size={24} color="#666" />
            <TextInput
              style={styles.modalSearchInput}
              placeholder="Пошук..."
              value={searchQuery}
              onChangeText={setSearchQuery}
            />
            {searchQuery.length > 0 && (
              <TouchableOpacity onPress={() => setSearchQuery('')}>
                <MaterialCommunityIcons name="close-circle" size={20} color="#999" />
              </TouchableOpacity>
            )}
          </View>

          {/* Category filters */}
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            style={styles.categoryFilterContainer}
            contentContainerStyle={styles.categoryFilterContent}
          >
            <TouchableOpacity
              style={[styles.categoryChip, !selectedCategory && styles.categoryChipActive]}
              onPress={() => setSelectedCategory(null)}
            >
              <Text style={[styles.categoryChipText, !selectedCategory && styles.categoryChipTextActive]}>
                Всі
              </Text>
            </TouchableOpacity>
            {categories.map((category) => (
              <TouchableOpacity
                key={category}
                style={[styles.categoryChip, selectedCategory === category && styles.categoryChipActive]}
                onPress={() => setSelectedCategory(category)}
              >
                <Text style={[styles.categoryChipText, selectedCategory === category && styles.categoryChipTextActive]}>
                  {category}
                </Text>
              </TouchableOpacity>
            ))}
          </ScrollView>

          {loading ? (
            <View style={styles.modalLoading}>
              <ActivityIndicator size="large" color="#4CAF50" />
            </View>
          ) : (
            <FlatList
              data={filteredNomenclature}
              renderItem={renderNomenclatureItem}
              keyExtractor={(item) => item.id.toString()}
              contentContainerStyle={styles.modalList}
            />
          )}
        </View>
      </Modal>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  scrollView: {
    flex: 1,
  },
  content: {
    padding: 16,
  },
  typeSelector: {
    flexDirection: 'row',
    gap: 12,
    marginBottom: 24,
  },
  typeButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    padding: 16,
    borderRadius: 12,
    backgroundColor: '#fff',
    borderWidth: 2,
    borderColor: '#e0e0e0',
  },
  typeButtonActive: {
    backgroundColor: '#4CAF50',
    borderColor: '#4CAF50',
  },
  typeButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#666',
  },
  typeButtonTextActive: {
    color: '#fff',
  },
  formSection: {
    marginBottom: 20,
  },
  label: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
    marginBottom: 8,
  },
  selectButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: '#fff',
    padding: 16,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#e0e0e0',
  },
  selectedText: {
    fontSize: 16,
    color: '#333',
  },
  placeholderText: {
    fontSize: 16,
    color: '#999',
  },
  helperText: {
    fontSize: 12,
    color: '#666',
    marginTop: 4,
  },
  balanceInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#E3F2FD',
    padding: 12,
    borderRadius: 8,
    marginBottom: 16,
    gap: 8,
  },
  balanceText: {
    flex: 1,
    fontSize: 14,
    color: '#1976D2',
  },
  balanceValue: {
    fontWeight: 'bold',
    fontSize: 16,
  },
  input: {
    backgroundColor: '#fff',
    padding: 16,
    borderRadius: 12,
    fontSize: 16,
    borderWidth: 1,
    borderColor: '#e0e0e0',
  },
  textArea: {
    minHeight: 80,
    textAlignVertical: 'top',
  },
  submitButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    backgroundColor: '#4CAF50',
    padding: 16,
    borderRadius: 12,
    marginTop: 8,
  },
  submitButtonWithdrawal: {
    backgroundColor: '#FF5722',
  },
  submitButtonDisabled: {
    opacity: 0.6,
  },
  submitButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  modalContainer: {
    flex: 1,
    backgroundColor: '#fff',
  },
  modalHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  modalTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#333',
  },
  modalSearchContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#f5f5f5',
    margin: 16,
    paddingHorizontal: 12,
    borderRadius: 12,
  },
  modalSearchInput: {
    flex: 1,
    paddingVertical: 12,
    paddingHorizontal: 8,
    fontSize: 16,
  },
  categoryFilterContainer: {
    flexGrow: 0,
    marginHorizontal: 16,
    marginBottom: 12,
  },
  categoryFilterContent: {
    paddingRight: 16,
  },
  categoryChip: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    marginRight: 8,
    borderRadius: 20,
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: '#e0e0e0',
  },
  categoryChipActive: {
    backgroundColor: '#4CAF50',
    borderColor: '#4CAF50',
  },
  categoryChipText: {
    fontSize: 14,
    fontWeight: '500',
    color: '#666',
  },
  categoryChipTextActive: {
    color: '#fff',
  },
  modalLoading: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  modalList: {
    padding: 16,
    paddingTop: 0,
  },
  nomenclatureItem: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: '#f9f9f9',
    padding: 16,
    borderRadius: 12,
    marginBottom: 8,
  },
  nomenclatureItemContent: {
    flex: 1,
    marginRight: 12,
  },
  nomenclatureName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
    marginBottom: 4,
  },
  nomenclatureCategory: {
    fontSize: 12,
    color: '#666',
  },
  nomenclatureUnit: {
    fontSize: 14,
    fontWeight: '600',
    color: '#4CAF50',
  },
});
