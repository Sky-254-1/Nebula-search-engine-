/**
 * Nebula Search Engine - Health API
 * 
 * Health check endpoints for frontend health monitoring
 * Provides liveness, readiness, and detailed health status
 */

import { useState, useEffect } from 'react';
import apiClient from './client';

// ============================================
// Types
// ============================================

export interface DependencyStatus {
  status: 'healthy' | 'unhealthy' | 'degraded' | 'unknown';
  response_time_ms?: number;
  message?: string;
  [key: string]: any;
}

export interface Dependencies {
  database: DependencyStatus;
  redis: DependencyStatus;
  storage: DependencyStatus;
  vector_worker?: DependencyStatus;
  indexing_worker?: DependencyStatus;
  ai_providers?: DependencyStatus;
  disk?: DependencyStatus;
  [key: string]: DependencyStatus;
}

export interface HealthResponse {
  status: 'healthy' | 'degraded' | 'unhealthy' | 'alive' | 'ready' | 'not_ready';
  service: string;
  timestamp: string;
  version?: string;
  uptime?: string;
  environment?: string;
  dependencies?: Dependencies;
  metadata?: {
    uptime_seconds?: number;
    database_type?: string;
    cache_type?: string;
  };
}

export interface LivenessResponse {
  status: 'alive';
  service: string;
  timestamp: string;
}

export interface ReadinessResponse {
  status: 'ready' | 'not_ready';
  service: string;
  timestamp: string;
  dependencies: Dependencies;
}

// ============================================
// API Functions
// ============================================

/**
 * Check if the application is alive (liveness probe)
 * Returns 200 if the service is running
 */
export const checkLive = async (): Promise<LivenessResponse> => {
  const response = await apiClient.get<HealthResponse>('/health/live');
  return {
    status: response.status,
    service: response.service,
    timestamp: response.timestamp,
  };
};

/**
 * Check if the application is ready (readiness probe)
 * Verifies all dependencies are healthy
 */
export const checkReady = async (): Promise<ReadinessResponse> => {
  const response = await apiClient.get<HealthResponse>('/health/ready');
  return {
    status: response.status as 'ready' | 'not_ready',
    service: response.service,
    timestamp: response.timestamp,
    dependencies: response.dependencies || {},
  };
};

/**
 * Get detailed health information
 * Includes version, uptime, and all dependency statuses
 */
export const checkDetailed = async (): Promise<HealthResponse> => {
  return await apiClient.get<HealthResponse>('/health/detailed');
};

/**
 * Check all health endpoints and return summary
 */
export const checkAll = async (): Promise<{
  live: LivenessResponse;
  ready: ReadinessResponse;
  detailed: HealthResponse;
}> => {
  const [live, ready, detailed] = await Promise.all([
    checkLive(),
    checkReady(),
    checkDetailed(),
  ]);
  return { live, ready, detailed };
};

/**
 * Check if all dependencies are healthy
 */
export const areDependenciesHealthy = (dependencies: Dependencies): boolean => {
  const criticalDependencies = ['database', 'redis', 'storage'];
  
  for (const dep of criticalDependencies) {
    if (!dependencies[dep]) {
      return false;
    }
    if (dependencies[dep].status === 'unhealthy' || dependencies[dep].status === 'unknown') {
      return false;
    }
  }
  
  return true;
};

/**
 * Get the most critical dependency status
 */
export const getCriticalDependencyStatus = (dependencies: Dependencies): DependencyStatus | null => {
  const criticalDependencies = ['database', 'redis', 'storage'];
  
  for (const dep of criticalDependencies) {
    const status = dependencies[dep];
    if (status && (status.status === 'unhealthy' || status.status === 'unknown')) {
      return status;
    }
  }
  
  return null;
};

// ============================================
// Utility Functions
// ============================================

/**
 * Convert uptime string to seconds
 */
export const uptimeToSeconds = (uptime: string): number => {
  if (!uptime) return 0;
  
  let totalSeconds = 0;
  
  // Parse days
  const daysMatch = uptime.match(/(\d+)d/);
  if (daysMatch) {
    totalSeconds += parseInt(daysMatch[1]) * 86400;
  }
  
  // Parse hours
  const hoursMatch = uptime.match(/(\d+)h/);
  if (hoursMatch) {
    totalSeconds += parseInt(hoursMatch[1]) * 3600;
  }
  
  // Parse minutes
  const minutesMatch = uptime.match(/(\d+)m/);
  if (minutesMatch) {
    totalSeconds += parseInt(minutesMatch[1]) * 60;
  }
  
  // Parse seconds
  const secondsMatch = uptime.match(/(\d+)s/);
  if (secondsMatch) {
    totalSeconds += parseInt(secondsMatch[1]);
  }
  
  return totalSeconds;
};

/**
 * Format seconds to human readable uptime
 */
export const formatUptime = (seconds: number): string => {
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);
  
  const parts = [];
  if (days) parts.push(`${days}d`);
  if (hours) parts.push(`${hours}h`);
  if (minutes) parts.push(`${minutes}m`);
  parts.push(`${secs}s`);
  
  return parts.join(' ');
};

// ============================================
// Health Status Monitoring Hook
// ============================================

/**
 * Hook to monitor health status with automatic updates
 */
export const useHealthMonitor = () => {
  const [status, setStatus] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    let mounted = true;
    
    const checkHealth = async () => {
      try {
        setLoading(true);
        const health = await checkDetailed();
        if (mounted) {
          setStatus(health);
          setError(null);
        }
      } catch (err) {
        if (mounted) {
          setError(err as Error);
          // Get partial status if available
          try {
            const live = await checkLive();
            if (mounted) {
              setStatus({
                status: live.status,
                service: live.service,
                timestamp: live.timestamp,
              });
            }
          } catch {
            // Ignore
          }
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    };
    
    // Initial check
    checkHealth();
    
    // Poll every 30 seconds
    const interval = setInterval(checkHealth, 30000);
    
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  return { status, loading, error };
};
