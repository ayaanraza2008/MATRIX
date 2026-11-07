export type NavSection =
  | 'dashboard'
  | 'chat'
  | 'voice'
  | 'vision'
  | 'agents'
  | 'automation'
  | 'research'
  | 'files'
  | 'memory'
  | 'developer'
  | 'repositories'
  | 'system'
  | 'devices'
  | 'settings';

export type HologramState =
  | 'idle'
  | 'wake_word'
  | 'listening'
  | 'thinking'
  | 'processing'
  | 'speaking'
  | 'executing'
  | 'interrupted'
  | 'error'
  | 'offline';

export type HandsFreeMode =
  | 'continuous'
  | 'wake_word_only'
  | 'push_to_talk'
  | 'privacy_pause';

export interface HealthData {
  status: string;
  app_name: string;
  version: string;
  environment: string;
  database: {
    connected: boolean;
    type: string;
    path: string;
    latency_ms: number;
  };
  system: {
    cpu_percent: number;
    cpu_cores_physical: number;
    cpu_threads_logical: number;
    ram_total_mb: number;
    ram_available_mb: number;
    ram_used_mb: number;
    ram_percent: number;
    low_ram_mode: boolean;
  };
  storage: {
    [key: string]: {
      total_gb?: number;
      free_gb?: number;
      used_percent?: number;
      available?: boolean;
    };
  };
  models: {
    candidate_local: string;
    model_path: string;
    model_installed: boolean;
    cloud_enabled: boolean;
  };
  active_autonomy_level: number;
}

export interface SystemInfoData {
  os: {
    system: string;
    release: string;
    version: string;
    architecture: string;
    processor: string;
  };
  python: {
    version: string;
    implementation: string;
  };
  hardware: {
    cpu_name: string;
    physical_cores: number;
    logical_processors: number;
    avx2_supported: boolean;
    gpu_name: string;
    total_ram_bytes: number;
    total_ram_gb: number;
  };
  storage_layout: {
    data_root: string;
    models_root: string;
    cache_root: string;
    logs_root: string;
  };
}

export interface LiveMetricsData {
  cpu: {
    percent: number;
    frequency_mhz: number;
  };
  memory: {
    percent: number;
    used_mb: number;
    available_mb: number;
    total_mb: number;
  };
  status: string;
}

export interface CapabilityItem {
  id: number;
  capability_id: string;
  name: string;
  description: string;
  source_repo: string | null;
  integration_method: string;
  is_enabled: boolean;
  is_verified: boolean;
}

export interface SessionItem {
  id: number;
  session_id: string;
  title: string;
  active_agent: string;
  created_at: string;
  updated_at: string;
}

export interface MessageItem {
  id: number;
  session_id: string;
  role: 'user' | 'assistant' | 'system' | 'agent';
  content: string;
  agent_name?: string;
  created_at: string;
}
