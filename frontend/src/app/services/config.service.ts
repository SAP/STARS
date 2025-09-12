import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { catchError, tap } from 'rxjs/operators';

export interface AppConfig {
  backend_url: string;      // HTTP URL for API calls (e.g., https://backend.com/process)
  backend_url_ws: string;   // WebSocket URL (e.g., wss://backend.com/agent)
  api_url: string;          // Base API URL (e.g., https://backend.com)
}

@Injectable({
  providedIn: 'root'
})
export class ConfigService {

  private config: AppConfig | null = null;

  constructor(private http: HttpClient) { }

  loadConfig(): Observable<AppConfig> {
    return this.http.get<AppConfig>('/assets/configs/config.json').pipe(
      tap(config => {
        this.config = config;
        console.log('Runtime configuration loaded:', config);
      }),
      catchError(async () => {
        const errorMsg = 'Could not load runtime configuration. Make sure config.json is accessible and contains valid configuration.';
        console.error(errorMsg);
        alert(errorMsg);
        throw new Error(errorMsg);
      })
    );
  }

  // HTTP URL for API calls (e.g., POST requests)
  get backendUrl(): string {
    return this.config?.backend_url || '';
  }

  // WebSocket URL for real-time communication
  get backendUrlWs(): string {
    return this.config?.backend_url_ws || '';
  }

  // Base API URL for general API calls
  get apiUrl(): string {
    return this.config?.api_url || '';
  }

  // Get the full configuration object
  get configuration(): AppConfig | null {
    return this.config;
  }

  // Check if configuration is loaded
  get isConfigLoaded(): boolean {
    return this.config !== null;
  }
}
