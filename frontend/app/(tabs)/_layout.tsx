import React, { useState } from 'react';
import { Tabs } from 'expo-router';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { Platform, TouchableOpacity } from 'react-native';
import HamburgerMenu from '../../components/HamburgerMenu';

export default function TabLayout() {
  const [menuVisible, setMenuVisible] = useState(false);

  return (
    <>
      <Tabs
        screenOptions={{
          tabBarActiveTintColor: '#4CAF50',
          tabBarInactiveTintColor: '#333',
          tabBarStyle: {
            backgroundColor: '#fff',
            borderTopWidth: 2,
            borderTopColor: '#4CAF50',
            height: Platform.OS === 'ios' ? 88 : 70,
            paddingBottom: Platform.OS === 'ios' ? 32 : 12,
            paddingTop: 10,
            elevation: 8,
            shadowColor: '#000',
            shadowOffset: { width: 0, height: -2 },
            shadowOpacity: 0.1,
            shadowRadius: 3,
          },
          tabBarLabelStyle: {
            fontSize: 13,
            fontWeight: '700',
          },
          headerStyle: {
            backgroundColor: '#4CAF50',
          },
          headerTintColor: '#fff',
          headerTitleStyle: {
            fontWeight: 'bold',
            fontSize: 18,
          },
          headerRight: () => (
            <TouchableOpacity
              onPress={() => setMenuVisible(true)}
              style={{ marginRight: 16, padding: 4 }}
            >
              <MaterialCommunityIcons name="menu" size={28} color="#fff" />
            </TouchableOpacity>
          ),
        }}
      >
        <Tabs.Screen
          name="operations"
          options={{
            title: 'Операції',
            href: '/(tabs)/operations',
            tabBarIcon: ({ color }) => (
              <MaterialCommunityIcons name="swap-horizontal" size={26} color={color} />
            ),
          }}
        />
        <Tabs.Screen
          name="butchery"
          options={{
            title: 'Обробка',
            href: '/(tabs)/butchery',
            tabBarIcon: ({ color }) => (
              <MaterialCommunityIcons name="knife" size={26} color={color} />
            ),
          }}
        />
        <Tabs.Screen
          name="production"
          options={{
            title: 'Виробництво',
            href: '/(tabs)/production',
            tabBarIcon: ({ color }) => (
              <MaterialCommunityIcons name="factory" size={26} color={color} />
            ),
          }}
        />
        <Tabs.Screen
          name="packaging"
          options={{
            title: 'Фасування',
            href: '/(tabs)/packaging',
            tabBarIcon: ({ color }) => (
              <MaterialCommunityIcons name="package-variant-closed" size={26} color={color} />
            ),
          }}
        />
        {/* Hidden tabs - no longer shown in tab bar */}
        <Tabs.Screen
          name="index"
          options={{
            href: null,
          }}
        />
        <Tabs.Screen
          name="inventory"
          options={{
            href: null,
          }}
        />
        <Tabs.Screen
          name="history"
          options={{
            href: null,
          }}
        />
      </Tabs>
      
      <HamburgerMenu visible={menuVisible} onClose={() => setMenuVisible(false)} />
    </>
  );
}
