import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { catchError, tap } from 'rxjs/operators';

@Injectable({
  providedIn: 'root'
})
export class ConfigService {

  private config: any;  // eslint-disable-line @typescript-eslint/no-explicit-any

  constructor(private http: HttpClient) { }

  loadConfig(): Observable<any> {   // eslint-disable-line @typescript-eslint/no-explicit-any
    return this.http.get('/assets/configs/config.json').pipe(
      tap(config => this.config = config),
      catchError(async () => alert('Could not access config.json. Make sure that assets/configs/config.json is accessible.'))
    );
  }

  get backendUrl(): string {
    return this.config?.backendUrl;
  }
}
