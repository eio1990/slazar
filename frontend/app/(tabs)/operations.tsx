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
  const { setPendingOperationsCount } = useStore();
  const [operationType, setOperationType] = useState<OperationType>('receipt');
  const [selectedItem, setSelectedItem] = useState<Nomenclature | null>(null);
  const [quantity, setQuantity] = useState('');
  const [notes, setNotes] = useState('');
  const [modalVisible, setModalVisible] = useState(false);
  const [nomenclature, setNomenclature] = useState<Nomenclature[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    loadNomenclature();
  }, []);

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

  const filteredNomenclature = nomenclature.filter(item =>
    item.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    item.category.toLowerCase().includes(searchQuery.toLowerCase())
  );

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

    try {
      setSubmitting(true);
      const isOnline = await checkNetworkConnectivity();
      
      const operation = {
        nomenclature_id: selectedItem.id,
        quantity: qty,
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
        addToOfflineQueue({
          type: operationType,
          data: operation,
        });
        setPendingOperationsCount(require('../../services/api').getOfflineQueue().length);
        Alert.alert(
          'Офлайн режим',
          'Операція збережена та буде синхронізована при підключенні до мережі'
        );
      }

      // Reset form
      setSelectedItem(null);
      setQuantity('');
      setNotes('');
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
          </View>

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
