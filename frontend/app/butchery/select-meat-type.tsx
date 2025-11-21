import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
} from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';

type MeatType = {
  id: string;
  name: string;
  icon: string;
  color: string;
  requiresGrade: boolean;
};

const meatTypes: MeatType[] = [
  { id: 'beef', name: 'Яловичина', icon: 'cow', color: '#D32F2F', requiresGrade: true },
  { id: 'horse', name: 'Конина', icon: 'horse-variant', color: '#7B1FA2', requiresGrade: true },
  { id: 'pork', name: 'Свинина', icon: 'pig-variant', color: '#E91E63', requiresGrade: false },
  { id: 'chicken', name: 'Курка', icon: 'food-drumstick', color: '#FF6F00', requiresGrade: false },
  { id: 'turkey', name: 'Індичка', icon: 'food-turkey', color: '#5D4037', requiresGrade: false },
];

export default function SelectMeatTypeScreen() {
  const router = useRouter();

  const handleSelect = (meatType: MeatType) => {
    if (meatType.requiresGrade) {
      // Go to grade selection screen
      router.push(`/butchery/select-grade?meatType=${meatType.id}` as any);
    } else {
      // Go directly to weight input
      router.push(`/butchery/input-weight?meatType=${meatType.id}` as any);
    }
  };

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.push('/(tabs)/butchery' as any)} style={styles.backButton}>
          <MaterialCommunityIcons name="arrow-left" size={24} color="#007AFF" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Оберіть тип м'яса</Text>
      </View>

      <ScrollView style={styles.content}>
        <Text style={styles.subtitle}>Крок 1 з 3</Text>
        
        {meatTypes.map((meat) => (
          <TouchableOpacity
            key={meat.id}
            style={styles.meatCard}
            onPress={() => handleSelect(meat)}
          >
            <View style={[styles.iconContainer, { backgroundColor: meat.color + '20' }]}>
              <MaterialCommunityIcons name={meat.icon as any} size={32} color={meat.color} />
            </View>
            <View style={styles.meatInfo}>
              <Text style={styles.meatName}>{meat.name}</Text>
              {meat.requiresGrade && (
                <Text style={styles.meatHint}>Потрібен вибір ґатунку</Text>
              )}
            </View>
            <MaterialCommunityIcons name="chevron-right" size={24} color="#999" />
          </TouchableOpacity>
        ))}
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
    padding: 16,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  backButton: {
    marginRight: 12,
    padding: 4,
  },
  headerTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#333',
  },
  content: {
    flex: 1,
    padding: 16,
  },
  subtitle: {
    fontSize: 14,
    color: '#999',
    marginBottom: 16,
  },
  meatCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fff',
    padding: 16,
    borderRadius: 12,
    marginBottom: 12,
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
  },
  iconContainer: {
    width: 56,
    height: 56,
    borderRadius: 28,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 16,
  },
  meatInfo: {
    flex: 1,
  },
  meatName: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333',
  },
  meatHint: {
    fontSize: 12,
    color: '#999',
    marginTop: 4,
  },
});
