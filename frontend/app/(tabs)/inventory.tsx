import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  FlatList,
  TextInput,
  Alert,
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { apiService, Nomenclature, StockBalance } from '../../services/api';

interface InventoryItem {
  nomenclature: Nomenclature & { currentQty: number };
  actualQty: string;
}

export default function InventoryScreen() {
  const [sessionActive, setSessionActive] = useState(false);
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [sessionType, setSessionType] = useState<'full' | 'partial'>('full');
  const [items, setItems] = useState<InventoryItem[]>([]);
  const [nomenclature, setNomenclature] = useState<Nomenclature[]>([]);
  const [balances, setBalances] = useState<StockBalance[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [nomData, balData] = await Promise.all([
        apiService.getNomenclature(),
        apiService.getBalances(),
      ]);
      setNomenclature(nomData);
      setBalances(balData);
    } catch (error) {
      console.error('Error loading data:', error);
      Alert.alert('Помилка', 'Не вдалося завантажити дані');
    } finally {
      setLoading(false);
    }
  };

  const startInventory = async () => {
    try {
      setLoading(true);
      const session = await apiService.startInventory(sessionType);
      setSessionId(session.id);
      setSessionActive(true);

      // Initialize items based on session type
      if (sessionType === 'full') {
        const inventoryItems: InventoryItem[] = nomenclature.map(nom => {
          const balance = balances.find(b => b.nomenclature_id === nom.id);
          return {
            nomenclature: { ...nom, currentQty: balance?.quantity || 0 },
            actualQty: '',
          };
        });
        setItems(inventoryItems);
      } else {
        setItems([]);
      }

      Alert.alert('Успіх', 'Інвентаризацію розпочато');
    } catch (error) {
      console.error('Error starting inventory:', error);
      Alert.alert('Помилка', 'Не вдалося розпочати інвентаризацію');
    } finally {
      setLoading(false);
    }
  };

  const addItemToPartialInventory = (nom: Nomenclature) => {
    if (items.some(i => i.nomenclature.id === nom.id)) {
      Alert.alert('Увага', 'Цей товар вже додано до інвентаризації');
      return;
    }

    const balance = balances.find(b => b.nomenclature_id === nom.id);
    setItems([...items, {
      nomenclature: { ...nom, currentQty: balance?.quantity || 0 },
      actualQty: '',
    }]);
  };

  const updateActualQty = (index: number, value: string) => {
    const updated = [...items];
    updated[index].actualQty = value;
    setItems(updated);
  };

  const removeItem = (index: number) => {
    const updated = items.filter((_, i) => i !== index);
    setItems(updated);
  };

  const completeInventory = async () => {
    if (!sessionId) return;

    // Validate all items have actual quantity
    const invalidItems = items.filter(i => !i.actualQty || parseFloat(i.actualQty) < 0);
    if (invalidItems.length > 0) {
      Alert.alert(
        'Помилка',
        `Будь ласка, заповніть фактичну кількість для всіх позицій (${invalidItems.length} незаповнених)`
      );
      return;
    }

    Alert.alert(
      'Підтвердження',
      `Завершити інвентаризацію? Буде оброблено ${items.length} позицій.`,
      [
        { text: 'Скасувати', style: 'cancel' },
        {
          text: 'Завершити',
          style: 'destructive',
          onPress: async () => {
            try {
              setLoading(true);
              const inventoryItems = items.map(i => ({
                nomenclature_id: i.nomenclature.id,
                actual_quantity: parseFloat(i.actualQty),
              }));

              const result = await apiService.completeInventory(sessionId, inventoryItems);
              
              Alert.alert(
                'Успіх',
                `Інвентаризацію завершено. Коригувань: ${result.adjustments_count}`,
                [{ text: 'OK', onPress: resetInventory }]
              );
            } catch (error: any) {
              console.error('Error completing inventory:', error);
              Alert.alert(
                'Помилка',
                error.response?.data?.detail || 'Не вдалося завершити інвентаризацію'
              );
            } finally {
              setLoading(false);
            }
          },
        },
      ]
    );
  };

  const resetInventory = () => {
    setSessionActive(false);
    setSessionId(null);
    setItems([]);
    setSearchQuery('');
    loadData();
  };

  const filteredNomenclature = nomenclature.filter(
    nom =>
      nom.name.toLowerCase().includes(searchQuery.toLowerCase()) &&
      !items.some(i => i.nomenclature.id === nom.id)
  );

  const filteredItems = items.filter(i =>
    i.nomenclature.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const renderInventoryItem = ({ item, index }: { item: InventoryItem; index: number }) => {
    const diff = item.actualQty ? parseFloat(item.actualQty) - item.nomenclature.currentQty : 0;
    
    return (
      <View style={styles.inventoryCard}>
        <View style={styles.inventoryHeader}>
          <Text style={styles.itemName} numberOfLines={2}>
            {item.nomenclature.name}
          </Text>
          {sessionType === 'partial' && (
            <TouchableOpacity onPress={() => removeItem(index)}>
              <MaterialCommunityIcons name="close-circle" size={24} color="#FF5722" />
            </TouchableOpacity>
          )}
        </View>

        <Text style={styles.categoryText}>{item.nomenclature.category}</Text>

        <View style={styles.quantityRow}>
          <View style={styles.quantityCol}>
            <Text style={styles.quantityLabel}>Системна кількість</Text>
            <Text style={styles.systemQty}>
              {item.nomenclature.currentQty} {item.nomenclature.unit}
            </Text>
          </View>

          <View style={styles.quantityCol}>
            <Text style={styles.quantityLabel}>Фактична кількість</Text>
            <TextInput
              style={styles.actualQtyInput}
              placeholder="0"
              value={item.actualQty}
              onChangeText={(value) => updateActualQty(index, value)}
              keyboardType="decimal-pad"
            />
          </View>
        </View>

        {item.actualQty && (
          <View style={[styles.diffBadge, diff !== 0 && (diff > 0 ? styles.diffPositive : styles.diffNegative)]}>
            <Text style={styles.diffText}>
              Різниця: {diff > 0 ? '+' : ''}{diff.toFixed(2)} {item.nomenclature.unit}
            </Text>
          </View>
        )}
      </View>
    );
  };

  const renderNomenclatureItem = ({ item }: { item: Nomenclature }) => (
    <TouchableOpacity
      style={styles.nomenclatureCard}
      onPress={() => addItemToPartialInventory(item)}
    >
      <View style={styles.nomenclatureContent}>
        <Text style={styles.nomenclatureName}>{item.name}</Text>
        <Text style={styles.nomenclatureCategory}>{item.category}</Text>
      </View>
      <MaterialCommunityIcons name="plus-circle" size={28} color="#4CAF50" />
    </TouchableOpacity>
  );

  if (loading && !sessionActive) {
    return (
      <View style={styles.centerContainer}>
        <ActivityIndicator size="large" color="#4CAF50" />
        <Text style={styles.loadingText}>Завантаження...</Text>
      </View>
    );
  }

  if (!sessionActive) {
    return (
      <View style={styles.container}>
        <View style={styles.startContainer}>
          <MaterialCommunityIcons name="clipboard-check-outline" size={80} color="#4CAF50" />
          <Text style={styles.startTitle}>Інвентаризація складу</Text>
          <Text style={styles.startDescription}>
            Оберіть тип інвентаризації та почніть облік фактичних залишків
          </Text>

          <View style={styles.typeCards}>
            <TouchableOpacity
              style={[
                styles.typeCard,
                sessionType === 'full' && styles.typeCardActive,
              ]}
              onPress={() => setSessionType('full')}
            >
              <MaterialCommunityIcons
                name="format-list-checkbox"
                size={32}
                color={sessionType === 'full' ? '#4CAF50' : '#666'}
              />
              <Text style={styles.typeCardTitle}>Повна</Text>
              <Text style={styles.typeCardDesc}>Всі позиції складу</Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={[
                styles.typeCard,
                sessionType === 'partial' && styles.typeCardActive,
              ]}
              onPress={() => setSessionType('partial')}
            >
              <MaterialCommunityIcons
                name="format-list-checks"
                size={32}
                color={sessionType === 'partial' ? '#4CAF50' : '#666'}
              />
              <Text style={styles.typeCardTitle}>Часткова</Text>
              <Text style={styles.typeCardDesc}>Вибрані позиції</Text>
            </TouchableOpacity>
          </View>

          <TouchableOpacity
            style={styles.startButton}
            onPress={startInventory}
          >
            <MaterialCommunityIcons name="play-circle" size={24} color="#fff" />
            <Text style={styles.startButtonText}>Розпочати інвентаризацію</Text>
          </TouchableOpacity>
        </View>
      </View>
    );
  }

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <View style={styles.activeHeader}>
        <View>
          <Text style={styles.activeHeaderTitle}>
            {sessionType === 'full' ? 'Повна інвентаризація' : 'Часткова інвентаризація'}
          </Text>
          <Text style={styles.activeHeaderSubtitle}>
            Оброблено: {items.filter(i => i.actualQty).length} / {items.length}
          </Text>
        </View>
        <TouchableOpacity onPress={resetInventory} style={styles.cancelButton}>
          <Text style={styles.cancelButtonText}>Скасувати</Text>
        </TouchableOpacity>
      </View>

      {sessionType === 'partial' && items.length === 0 && (
        <View style={styles.addItemsHint}>
          <MaterialCommunityIcons name="information" size={24} color="#2196F3" />
          <Text style={styles.addItemsHintText}>
            Додайте позиції для інвентаризації через пошук нижче
          </Text>
        </View>
      )}

      <View style={styles.searchContainer}>
        <MaterialCommunityIcons name="magnify" size={24} color="#666" />
        <TextInput
          style={styles.searchInput}
          placeholder={
            sessionType === 'partial' && items.length === 0
              ? 'Пошук для додавання позицій...'
              : 'Пошук...'
          }
          value={searchQuery}
          onChangeText={setSearchQuery}
        />
      </View>

      {sessionType === 'partial' && searchQuery && filteredNomenclature.length > 0 ? (
        <FlatList
          data={filteredNomenclature}
          renderItem={renderNomenclatureItem}
          keyExtractor={(item) => item.id.toString()}
          contentContainerStyle={styles.listContent}
        />
      ) : (
        <FlatList
          data={filteredItems}
          renderItem={renderInventoryItem}
          keyExtractor={(item, index) => `${item.nomenclature.id}-${index}`}
          contentContainerStyle={styles.listContent}
          ListEmptyComponent={
            <View style={styles.emptyContainer}>
              <Text style={styles.emptyText}>Немає позицій для інвентаризації</Text>
            </View>
          }
        />
      )}

      {items.length > 0 && (
        <View style={styles.footer}>
          <TouchableOpacity
            style={styles.completeButton}
            onPress={completeInventory}
            disabled={loading}
          >
            {loading ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <>
                <MaterialCommunityIcons name="check-circle" size={24} color="#fff" />
                <Text style={styles.completeButtonText}>Завершити інвентаризацію</Text>
              </>
            )}
          </TouchableOpacity>
        </View>
      )}
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  centerContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#f5f5f5',
  },
  loadingText: {
    marginTop: 16,
    fontSize: 16,
    color: '#666',
  },
  startContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 24,
  },
  startTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#333',
    marginTop: 16,
    marginBottom: 8,
  },
  startDescription: {
    fontSize: 14,
    color: '#666',
    textAlign: 'center',
    marginBottom: 32,
  },
  typeCards: {
    flexDirection: 'row',
    gap: 16,
    marginBottom: 32,
  },
  typeCard: {
    flex: 1,
    alignItems: 'center',
    backgroundColor: '#fff',
    padding: 20,
    borderRadius: 12,
    borderWidth: 2,
    borderColor: '#e0e0e0',
  },
  typeCardActive: {
    borderColor: '#4CAF50',
    backgroundColor: '#E8F5E9',
  },
  typeCardTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
    marginTop: 8,
  },
  typeCardDesc: {
    fontSize: 12,
    color: '#666',
    marginTop: 4,
  },
  startButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    backgroundColor: '#4CAF50',
    paddingHorizontal: 32,
    paddingVertical: 16,
    borderRadius: 12,
  },
  startButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  activeHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: '#fff',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  activeHeaderTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333',
  },
  activeHeaderSubtitle: {
    fontSize: 12,
    color: '#666',
    marginTop: 2,
  },
  cancelButton: {
    padding: 8,
  },
  cancelButtonText: {
    color: '#FF5722',
    fontWeight: '600',
  },
  addItemsHint: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    backgroundColor: '#E3F2FD',
    padding: 16,
    margin: 16,
    borderRadius: 8,
  },
  addItemsHintText: {
    flex: 1,
    fontSize: 14,
    color: '#1976D2',
  },
  searchContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fff',
    margin: 16,
    marginTop: 8,
    paddingHorizontal: 12,
    borderRadius: 12,
  },
  searchInput: {
    flex: 1,
    paddingVertical: 12,
    paddingHorizontal: 8,
    fontSize: 16,
  },
  listContent: {
    padding: 16,
    paddingTop: 0,
  },
  inventoryCard: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
  },
  inventoryHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 8,
  },
  itemName: {
    flex: 1,
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
  },
  categoryText: {
    fontSize: 12,
    color: '#999',
    marginBottom: 12,
  },
  quantityRow: {
    flexDirection: 'row',
    gap: 12,
    marginBottom: 12,
  },
  quantityCol: {
    flex: 1,
  },
  quantityLabel: {
    fontSize: 12,
    color: '#666',
    marginBottom: 4,
  },
  systemQty: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
  },
  actualQtyInput: {
    backgroundColor: '#f5f5f5',
    padding: 8,
    borderRadius: 8,
    fontSize: 16,
    fontWeight: '600',
  },
  diffBadge: {
    padding: 8,
    borderRadius: 8,
    backgroundColor: '#f5f5f5',
  },
  diffPositive: {
    backgroundColor: '#E8F5E9',
  },
  diffNegative: {
    backgroundColor: '#FFEBEE',
  },
  diffText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
    textAlign: 'center',
  },
  nomenclatureCard: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: '#fff',
    padding: 16,
    borderRadius: 12,
    marginBottom: 12,
  },
  nomenclatureContent: {
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
  emptyContainer: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 64,
  },
  emptyText: {
    fontSize: 16,
    color: '#999',
  },
  footer: {
    padding: 16,
    backgroundColor: '#fff',
    borderTopWidth: 1,
    borderTopColor: '#e0e0e0',
  },
  completeButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    backgroundColor: '#4CAF50',
    padding: 16,
    borderRadius: 12,
  },
  completeButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
});
