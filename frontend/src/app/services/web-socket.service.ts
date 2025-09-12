import { Injectable, inject } from '@angular/core';
import { retry } from 'rxjs';
import { webSocket, WebSocketSubject } from 'rxjs/webSocket';
import { ConfigService } from './config.service';

@Injectable({
  providedIn: 'root',
})
export class WebSocketService {
  private config = inject(ConfigService);

  get URL(): string {
    return this.config.backendUrlWs;
  }

  connected: boolean = false;
  private webSocketSubject?: WebSocketSubject<any>;  // eslint-disable-line @typescript-eslint/no-explicit-any

  private initializeWebSocket() {
    if (!this.webSocketSubject && this.config.isConfigLoaded) {
      this.webSocketSubject = webSocket<any>({  // eslint-disable-line @typescript-eslint/no-explicit-any
        url: this.URL,
        openObserver: {
          next: () => {
            this.connected = true;
          }
        },
        closeObserver: {
          next: () => {
            this.connected = false;
          }
        }
      });
    }
  }

  get webSocket$() {
    this.initializeWebSocket();
    return this.webSocketSubject!.pipe(retry());
  }

  postMessage(message: string, key: string | null): void {
    this.initializeWebSocket();
    if (this.webSocketSubject) {
      const data = { type: "message", data: message, key };
      this.webSocketSubject.next(data);
    }
  }
}
