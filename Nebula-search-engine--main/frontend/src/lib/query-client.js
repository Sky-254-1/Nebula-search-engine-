import { QueryClient } from '@tanstack/react-query';

const STALE = 1000 * 60 * 2;
const CACHE = 1000 * 60 * 10;

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: STALE,
      gcTime: CACHE,
      retry: 1,
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: 0,
    },
  },
});
