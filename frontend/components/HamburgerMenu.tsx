import React from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Modal,
  StatusBar,
  Platform,
} from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { BlurView } from 'expo-blur';

interface HamburgerMenuProps {
  visible: boolean;
  onClose: () => void;
}

export default function HamburgerMenu({ visible, onClose }: HamburgerMenuProps) {
  const router = useRouter();

  const menuItems = [
    {
      title: 'Залишки',
      icon: 'warehouse',
      route: '/stock',
    },
    {
      title: 'Інвентаризація',
      icon: 'clipboard-check',
      route: '/(tabs)/inventory',
    },
    {
      title: 'Журнал',
      icon: 'history',
      route: '/(tabs)/history',
    },
  ];

  const handleNavigate = (route: string) => {
    onClose();
    router.push(route as any);
  };

  return (
    <Modal
      visible={visible}
      transparent
      animationType="fade"
      onRequestClose={onClose}
      statusBarTranslucent
    >
      <View style={styles.container}>
        {/* Blurred background overlay */}
        <TouchableOpacity
          style={styles.backdrop}
          activeOpacity={1}
          onPress={onClose}
        >
          <BlurView intensity={20} style={StyleSheet.absoluteFill} tint="dark" />
        </TouchableOpacity>

        {/* Menu panel */}
        <View style={styles.menuPanel}>
          <View style={styles.menuHeader}>
            <Text style={styles.menuTitle}>Меню</Text>
            <TouchableOpacity onPress={onClose} style={styles.closeButton}>
              <MaterialCommunityIcons name="close" size={24} color="#333" />
            </TouchableOpacity>
          </View>

          <View style={styles.menuItems}>
            {menuItems.map((item, index) => (
              <TouchableOpacity
                key={index}
                style={styles.menuItem}
                onPress={() => handleNavigate(item.route)}
              >
                <MaterialCommunityIcons name={item.icon as any} size={24} color="#4CAF50" />
                <Text style={styles.menuItemText}>{item.title}</Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'flex-start',
    alignItems: 'flex-end',
  },
  backdrop: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
  },
  menuPanel: {
    backgroundColor: '#fff',
    width: '75%',
    maxWidth: 320,
    height: '100%',
    paddingTop: Platform.OS === 'ios' ? 50 : StatusBar.currentHeight || 20,
    ...Platform.select({
      ios: {
        shadowColor: '#000',
        shadowOffset: { width: -2, height: 0 },
        shadowOpacity: 0.3,
        shadowRadius: 8,
      },
      android: {
        elevation: 8,
      },
    }),
  },
  menuHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  menuTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#333',
  },
  closeButton: {
    padding: 4,
  },
  menuItems: {
    paddingTop: 16,
  },
  menuItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 16,
    paddingHorizontal: 20,
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0',
  },
  menuItemText: {
    fontSize: 16,
    color: '#333',
    marginLeft: 16,
  },
});
