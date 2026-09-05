import { create } from 'zustand';
import type { Repository } from '../types';

interface RepositoryState {
  repositories: Repository[];
  activeRepository: Repository | null;
  isLoading: boolean;
  error: string | null;
  setRepositories: (repos: Repository[]) => void;
  setActiveRepository: (repo: Repository | null) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
}

export const useRepositoryStore = create<RepositoryState>((set) => ({
  repositories: [],
  activeRepository: null,
  isLoading: false,
  error: null,
  setRepositories: (repositories) => set({ repositories }),
  setActiveRepository: (activeRepository) => set({ activeRepository }),
  setLoading: (isLoading) => set({ isLoading }),
  setError: (error) => set({ error }),
}));
