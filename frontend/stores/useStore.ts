import { create } from 'zustand';
import { Nomenclature, StockBalance } from '../services/api';

interface AppState {
  nomenclature: Nomenclature[];
  balances: StockBalance[];
  selectedCategory: string | null;
  isOnline: boolean;
  isSyncing: boolean;
  pendingOperationsCount: number;
  
  setNomenclature: (data: Nomenclature[]) => void;
  setBalances: (data: StockBalance[]) => void;
  setSelectedCategory: (category: string | null) => void;
  setIsOnline: (online: boolean) => void;
  setIsSyncing: (syncing: boolean) => void;
  setPendingOperationsCount: (count: number) => void;
}

export const useStore = create<AppState>((set) => ({
  nomenclature: [],
  balances: [],
  selectedCategory: null,
  isOnline: true,
  isSyncing: false,
  pendingOperationsCount: 0,
  
  setNomenclature: (data) => set({ nomenclature: data }),
  setBalances: (data) => set({ balances: data }),
  setSelectedCategory: (category) => set({ selectedCategory: category }),
  setIsOnline: (online) => set({ isOnline: online }),
  setIsSyncing: (syncing) => set({ isSyncing: syncing }),
  setPendingOperationsCount: (count) => set({ pendingOperationsCount: count }),
}));
