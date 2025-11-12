import axios from 'axios';
import Constants from 'expo-constants';
import NetInfo from '@react-native-community/netinfo';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Platform } from 'react-native';

// Configure API URL from environment
const getApiUrl = () => {
  // For Expo Go, use the preview URL
  if (Constants.expoConfig?.extra?.EXPO_PUBLIC_BACKEND_URL) {
    return Constants.expoConfig.extra.EXPO_PUBLIC_BACKEND_URL;
  }
  
  // For local development
  if (__DEV__) {
    if (Platform.OS === 'android') {
      return 'http://10.0.2.2:8001'; // Android emulator
    }
    return 'http://localhost:8001';
  }
  
  return 'http://localhost:8001';
};

const API_URL = getApiUrl();

console.log('[API Service] Configured API URL:', API_URL);

// Storage adapter for cross-platform compatibility
export const storage = {
  getString: async (key: string): Promise<string | undefined> => {
    try {
      const value = await AsyncStorage.getItem(key);
      return value || undefined;
    } catch (e) {
      return undefined;
    }
  },
  set: async (key: string, value: string): Promise<void> => {
    await AsyncStorage.setItem(key, value);
  },
  delete: async (key: string): Promise<void> => {
    await AsyncStorage.removeItem(key);
  },
};

// Axios instance
export const api = axios.create({
  baseURL: `${API_URL}/api`,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Check network connectivity
export async function checkNetworkConnectivity(): Promise<boolean> {
  const state = await NetInfo.fetch();
  return state.isConnected === true && state.isInternetReachable === true;
}

// Generate unique idempotency key
export function generateIdempotencyKey(): string {
  return `${Date.now()}-${Math.random().toString(36).substring(2, 15)}`;
}

// Types
export interface Nomenclature {
  id: number;
  name: string;
  category: string;
  unit: string;
  precision_digits: number;
  created_at: string;
  updated_at: string;
}

export interface StockBalance {
  nomenclature_id: number;
  nomenclature_name: string;
  category: string;
  unit: string;
  quantity: number;
  last_updated: string;
}

export interface StockMovement {
  id: number;
  nomenclature_id: number;
  operation_type: string;
  quantity: number;
  balance_after: number;
  idempotency_key: string;
  metadata: string | null;
  operation_date: string;
  created_at: string;
}

export interface StockOperation {
  nomenclature_id: number;
  quantity: number;
  idempotency_key: string;
  metadata?: Record<string, any>;
}

export interface InventorySession {
  id: number;
  session_type: string;
  status: string;
  started_at: string;
  completed_at: string | null;
  idempotency_key: string;
  metadata: string | null;
}

export interface InventoryItem {
  nomenclature_id: number;
  actual_quantity: number;
}

// Offline queue management
const QUEUE_KEY = 'offline_queue';

export interface QueuedOperation {
  id: string;
  type: 'receipt' | 'withdrawal' | 'inventory';
  data: any;
  timestamp: string;
}

export async function getOfflineQueue(): Promise<QueuedOperation[]> {
  const queueStr = await storage.getString(QUEUE_KEY);
  return queueStr ? JSON.parse(queueStr) : [];
}

export async function addToOfflineQueue(operation: Omit<QueuedOperation, 'id' | 'timestamp'>) {
  const queue = await getOfflineQueue();
  const newOp: QueuedOperation = {
    ...operation,
    id: generateIdempotencyKey(),
    timestamp: new Date().toISOString(),
  };
  queue.push(newOp);
  await storage.set(QUEUE_KEY, JSON.stringify(queue));
  return newOp;
}

export async function removeFromOfflineQueue(id: string) {
  const queue = await getOfflineQueue();
  const filtered = queue.filter(op => op.id !== id);
  await storage.set(QUEUE_KEY, JSON.stringify(filtered));
}

export async function clearOfflineQueue() {
  await storage.delete(QUEUE_KEY);
}

// API Functions
export const apiService = {
  // Nomenclature
  async getNomenclature(): Promise<Nomenclature[]> {
    const response = await api.get('/nomenclature');
    return response.data;
  },

  // Stock balances
  async getBalances(category?: string): Promise<StockBalance[]> {
    const response = await api.get('/stock/balances', {
      params: category ? { category } : {},
    });
    return response.data;
  },

  // Stock movements
  async getMovements(params?: {
    nomenclature_id?: number;
    start_date?: string;
    end_date?: string;
    limit?: number;
  }): Promise<StockMovement[]> {
    const response = await api.get('/stock/movements', { params });
    return response.data;
  },

  // Stock operations
  async receipt(operation: StockOperation) {
    const response = await api.post('/stock/receipt', operation);
    return response.data;
  },

  async withdrawal(operation: StockOperation) {
    const response = await api.post('/stock/withdrawal', operation);
    return response.data;
  },

  // Inventory
  async startInventory(sessionType: 'full' | 'partial', metadata?: any): Promise<InventorySession> {
    const response = await api.post('/stock/inventory/start', {
      session_type: sessionType,
      idempotency_key: generateIdempotencyKey(),
      metadata,
    });
    return response.data;
  },

  async completeInventory(sessionId: number, items: InventoryItem[]) {
    const response = await api.post('/stock/inventory/complete', {
      session_id: sessionId,
      items,
      idempotency_key: generateIdempotencyKey(),
    });
    return response.data;
  },

  // Sync offline operations
  async syncOperations(operations: QueuedOperation[]) {
    const syncData = {
      operations: operations.map(op => ({
        operation_type: op.type,
        data: op.data,
        idempotency_key: op.data.idempotency_key || op.id,
        timestamp: op.timestamp,
      })),
    };
    const response = await api.post('/sync/operations', syncData);
    return response.data;
  },
};
