import { Injectable } from '@angular/core';
import { retry } from 'rxjs';
import { webSocket } from 'rxjs/webSocket';
import { ConfigService } from './config.service';

@Injectable({
  providedIn: 'root',
})
export class WebSocketService {
  constructor(private config: ConfigService) { }
  readonly URL = this.config.backendUrl;
  connected: boolean = false;
  private webSocketSubject = webSocket<any>(  // eslint-disable-line @typescript-eslint/no-explicit-any
    {
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
  public webSocket$ = this.webSocketSubject.pipe(retry());

  postMessage(message: string, key: string | null): void {
    const data = { type: "message", data: message, key };
    this.webSocketSubject.next(data);
  }
}
