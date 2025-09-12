export interface User {
  id: number;
  email: string;
  is_active: boolean;
  created_at: string;
}

export interface Property {
  id: number;
  name: string;
  address: string;
  property_type?: string;
  user_id: number;
  created_at: string;
  updated_at?: string;
}

export interface DataSource {
  id: number;
  user_id: number;
  source_type: string;
  is_active: boolean;
  last_sync?: string;
  created_at: string;
  updated_at?: string;
}

export interface ChatSession {
  id: number;
  user_id: number;
  session_name?: string;
  created_at: string;
  updated_at?: string;
  messages: ChatMessage[];
}

export interface ChatMessage {
  id: number;
  session_id: number;
  role: 'user' | 'assistant';
  content: string;
  metadata?: any;
  created_at: string;
}

export interface ChatQuery {
  message: string;
  session_id?: number;
}

export interface ChatResponse {
  response: string;
  sources?: any[];
  confidence?: number;
}

export interface LoginCredentials {
  username: string;
  password: string;
}

export interface RegisterData {
  email: string;
  password: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
}
