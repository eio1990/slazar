import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
} from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useRouter, useLocalSearchParams } from 'expo-router';

type Grade = {
  id: string;
  name: string;
  description: string;
};

const grades: Grade[] = [
  { id: 'premium', name: 'Вищий ґатунок', description: 'Найкраща якість' },
  { id: 'first', name: 'Перший ґатунок', description: 'Хороша якість' },
  { id: 'second', name: 'Другий ґатунок', description: 'Стандартна якість' },
  { id: 'carcass', name: 'Туша', description: 'Ціла туша' },
];

export default function SelectGradeScreen() {
  const router = useRouter();
  const { meatType } = useLocalSearchParams();

  const handleSelect = (grade: Grade) => {
    router.push(`/butchery/input-weight?meatType=${meatType}&grade=${grade.id}` as any);
  };

  const getMeatTypeName = () => {
    switch (meatType) {
      case 'beef': return 'Яловичина';
      case 'horse': return 'Конина';
      default: return 'М\'ясо';
    }
  };

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.push('/(tabs)/butchery' as any)} style={styles.backButton}>
          <MaterialCommunityIcons name="arrow-left" size={24} color="#007AFF" />
        </TouchableOpacity>
        <View>
          <Text style={styles.headerTitle}>Оберіть ґатунок</Text>
          <Text style={styles.headerSubtitle}>{getMeatTypeName()}</Text>
        </View>
      </View>

      <ScrollView style={styles.content}>
        <Text style={styles.subtitle}>Крок 2 з 3</Text>
        
        {grades.map((grade) => (
          <TouchableOpacity
            key={grade.id}
            style={styles.gradeCard}
            onPress={() => handleSelect(grade)}
          >
            <View style={styles.gradeInfo}>
              <Text style={styles.gradeName}>{grade.name}</Text>
              <Text style={styles.gradeDescription}>{grade.description}</Text>
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
  headerSubtitle: {
    fontSize: 14,
    color: '#666',
    marginTop: 2,
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
  gradeCard: {
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
  gradeInfo: {
    flex: 1,
  },
  gradeName: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333',
  },
  gradeDescription: {
    fontSize: 14,
    color: '#666',
    marginTop: 4,
  },
});
