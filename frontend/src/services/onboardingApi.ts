import api from './api';

export interface Property {
  id?: string;
  name: string;
  street: string;
  city: string;
  state: string;
  country: string;
  property_type?: string;
}

export interface OnboardingPropertiesRequest {
  properties: Omit<Property, 'id'>[];
}

export interface OnboardingServicesRequest {
  selected_services: string[];
  gmail_sync_option?: string;
  drive_selected_items?: string[];
}

export interface OnboardingSyncRequest {
  properties: Omit<Property, 'id'>[];
  selected_services: string[];
  gmail_sync_option?: string;
  drive_selected_items?: string[];
}

export interface SyncStatus {
  source_type: string;
  status: string;
  progress: number;
  last_sync?: string;
  error_message?: string;
}

export interface SyncStatusResponse {
  services: SyncStatus[];
  overall_status: string;
  overall_progress: number;
}

export const onboardingApi = {
  // Save user properties
  saveProperties: async (request: OnboardingPropertiesRequest): Promise<Property[]> => {
    const response = await api.post('/api/onboarding/properties', request);
    return response.data;
  },

  // Configure services
  configureServices: async (request: OnboardingServicesRequest) => {
    const response = await api.post('/api/onboarding/services', request);
    return response.data;
  },

  // Start onboarding sync
  startSync: async (request: OnboardingSyncRequest) => {
    const response = await api.post('/api/onboarding/sync', request);
    return response.data;
  },

  // Get sync status
  getSyncStatus: async (): Promise<SyncStatusResponse> => {
    const response = await api.get('/api/onboarding/sync/status');
    return response.data;
  },

  // Get user properties
  getProperties: async (): Promise<Property[]> => {
    const response = await api.get('/api/onboarding/properties');
    return response.data;
  }
};
