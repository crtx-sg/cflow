/**
 * API client with authentication interceptors.
 */

const API_BASE_URL = '/api/v1';

interface RequestConfig extends RequestInit {
  params?: Record<string, string | number | boolean | undefined>;
}

class ApiError extends Error {
  status: number;
  data: unknown;

  constructor(message: string, status: number, data?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private getAccessToken(): string | null {
    return localStorage.getItem('accessToken');
  }

  private setAccessToken(token: string): void {
    localStorage.setItem('accessToken', token);
  }

  private removeAccessToken(): void {
    localStorage.removeItem('accessToken');
  }

  private async refreshToken(): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseUrl}/auth/refresh`, {
        method: 'POST',
        credentials: 'include', // Include HTTP-only refresh token cookie
      });

      if (response.ok) {
        const data = await response.json();
        this.setAccessToken(data.access_token);
        return true;
      }
      return false;
    } catch {
      return false;
    }
  }

  private buildUrl(endpoint: string, params?: Record<string, string | number | boolean | undefined>): string {
    const url = new URL(`${this.baseUrl}${endpoint}`, window.location.origin);

    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          url.searchParams.append(key, String(value));
        }
      });
    }

    return url.toString();
  }

  async request<T>(endpoint: string, config: RequestConfig = {}): Promise<T> {
    const { params, ...fetchConfig } = config;
    const url = this.buildUrl(endpoint, params);

    const headers = new Headers(fetchConfig.headers);

    // Add auth header if we have a token
    const token = this.getAccessToken();
    if (token) {
      headers.set('Authorization', `Bearer ${token}`);
    }

    // Default content type for JSON
    if (!headers.has('Content-Type') && fetchConfig.body) {
      headers.set('Content-Type', 'application/json');
    }

    let response = await fetch(url, {
      ...fetchConfig,
      headers,
      credentials: 'include',
    });

    // Handle 401 - try to refresh token
    if (response.status === 401 && token) {
      const refreshed = await this.refreshToken();
      if (refreshed) {
        // Retry the request with new token
        headers.set('Authorization', `Bearer ${this.getAccessToken()}`);
        response = await fetch(url, {
          ...fetchConfig,
          headers,
          credentials: 'include',
        });
      } else {
        // Refresh failed, clear token and redirect to login
        this.removeAccessToken();
        window.location.href = '/login';
        throw new ApiError('Session expired', 401);
      }
    }

    // Parse response
    let data: unknown;
    const contentType = response.headers.get('content-type');
    if (contentType?.includes('application/json')) {
      data = await response.json();
    } else {
      data = await response.text();
    }

    if (!response.ok) {
      const message = typeof data === 'object' && data !== null && 'detail' in data
        ? String((data as { detail: string }).detail)
        : `Request failed with status ${response.status}`;
      throw new ApiError(message, response.status, data);
    }

    return data as T;
  }

  async get<T>(endpoint: string, params?: Record<string, string | number | boolean | undefined>): Promise<T> {
    return this.request<T>(endpoint, { method: 'GET', params });
  }

  async post<T>(endpoint: string, body?: unknown): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: body ? JSON.stringify(body) : undefined,
    });
  }

  async put<T>(endpoint: string, body?: unknown): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: body ? JSON.stringify(body) : undefined,
    });
  }

  async delete<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'DELETE' });
  }

  // Auth helpers
  async login(email: string, password: string): Promise<{ access_token: string }> {
    const response = await this.request<{ access_token: string; token_type: string }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });

    this.setAccessToken(response.access_token);
    return response;
  }

  async logout(): Promise<void> {
    try {
      await this.post('/auth/logout');
    } finally {
      this.removeAccessToken();
    }
  }

  isAuthenticated(): boolean {
    return !!this.getAccessToken();
  }
}

export const api = new ApiClient(API_BASE_URL);
export { ApiError };
