import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';

export default function PackagingScreen() {
  return (
    <View style={styles.container}>
      <View style={styles.content}>
        <MaterialCommunityIcons name="package-variant-closed" size={80} color="#ccc" />
        <Text style={styles.title}>Фасування</Text>
        <Text style={styles.subtitle}>Функціонал у розробці</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  content: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 24,
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#333',
    marginTop: 16,
  },
  subtitle: {
    fontSize: 16,
    color: '#999',
    marginTop: 8,
  },
});
