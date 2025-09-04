import { APIResponse, ReportItem } from '../types/API';
import { AfterViewChecked, AfterViewInit, Component, ElementRef, QueryList, ViewChildren, inject } from '@angular/core';
import { ChatItem, Message, ReportCard, VulnerabilityReportCard } from '../types/ChatItem';
import { Status, Step } from '../types/Step';

import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MarkdownModule } from 'ngx-markdown';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MaterialModule } from '../material.module';
import { VulnerabilityInfoService } from '../services/vulnerability-information.service';
import { WebSocketService } from '../services/web-socket.service';

@Component({
  selector: 'app-chatzone',
  templateUrl: './chatzone.component.html',
  styleUrls: ['./chatzone.component.css'],
  imports: [MaterialModule, MarkdownModule, MatProgressBarModule, FormsModule, CommonModule],
  standalone: true,
})
export class ChatzoneComponent implements AfterViewInit, AfterViewChecked {
  private ws = inject(WebSocketService);
  private vis = inject(VulnerabilityInfoService);

  chatItems: ChatItem[];

  steps: Step[];
  errorMessage: string;
  inputValue: string;
  apiKey: string;
  progress: number | undefined;
  constructor() {
    this.inputValue = '';
    this.apiKey = localStorage.getItem('key') || '';
    this.errorMessage = '';
    this.chatItems = [];
    this.steps = [];
    this.progress = undefined;

    this.ws.webSocket$.subscribe({
      next: (value: any) => {
        this.handleWSMessage(value as APIResponse);
      },
      error: (error: any) => {
        console.log(error);
        if (error?.type != 'close') {
          // Close is already handled via the isConnected call
          this.errorMessage = error;
        }
      },
      complete: () => alert('Connection to server closed.'),
    });

    this.restoreChatItems();
  }

  // Handling of the websocket connection

  checkInput(value: string): void {
    if (value && value.trim() != '') {
      this.inputValue = '';
      this.ws.postMessage(value, this.apiKey);
      const userMessage: Message = {
        type: 'message',
        id: 'user-message',
        message: value,
        avatar: 'person',
        timestamp: Date.now(),
      };
      this.appendMessage(userMessage);
    }
  }

  handleWSMessage(input: APIResponse): void {
    if (input.type == 'message') {
      const aiMessageString = input.data;
      const aiMessage: Message = {
        type: 'message',
        id: 'ai-message',
        message: aiMessageString,
        avatar: 'computer',
        timestamp: Date.now(),
      };
      this.appendMessage(aiMessage);
    } else if (input.type == 'status') {
      const current = input.current;
      const total = input.total;
      const progress = current / total;
      this.progress = progress * 100;
      if (progress >= 1) {
        this.progress = undefined;
      }
    } else if (input.type == 'report') {
      if (input.reset) {
        this.steps = [];
        return;
      }
      const steps: Array<Step> = input.data.map(ChatzoneComponent.deserializeStep);
      for (const step of steps) {
        // If step is already known (e.g. it is a status update), don't create a new entry
        const existingStep = this.steps.find(s => s.title == step.title);
        if (existingStep) {
          Object.assign(existingStep, step);
        } else {
          this.steps.push(step);
        }
      }
    } else if (input.type == 'intermediate') {
      const text = '### Intermediate result from attack\n' + input.data;
      const intermediateMessage: Message = {
        type: 'message',
        id: 'assistant-intermediate-message',
        message: text,
        avatar: 'computer',
        timestamp: Date.now(),
      };
      this.appendMessage(intermediateMessage);
    } else if (input.type == 'vulnerability-report') {
      const vulnerabilityCards = input.data.map(vri => {
        const vrc = vri as VulnerabilityReportCard;
        vrc.description = this.vis.getInfo(vri.vulnerability);
        return vrc;
      });
      this.chatItems.push({
        type: 'report-card',
        reports: vulnerabilityCards,
        name: input.name,
      });
      localStorage.setItem('cached-chat-items', JSON.stringify(this.chatItems));
    }
  }

  isConnected() {
    return this.ws.connected;
  }

  getIconForStepStatus(step: Step): string {
    switch (step.status) {
      case Status.COMPLETED:
        return 'check_circle';
      case Status.FAILED:
        return 'error';
      case Status.SKIPPED:
        return 'skip_next';
      case Status.RUNNING:
        return 'play_circle';
      case Status.PENDING:
        return 'pending';
    }
  }

  appendMessage(message: Message) {
    this.chatItems.push(message);
    localStorage.setItem('cached-chat-items', JSON.stringify(this.chatItems));
  }

  restoreChatItems() {
    const storedMessages = localStorage.getItem('cached-chat-items');
    if (storedMessages) {
      this.chatItems = JSON.parse(storedMessages);
    }
  }

  clearChatHistory() {
    this.chatItems = [];
    localStorage.setItem('cached-chat-items', '[]');
  }

  static deserializeStep(obj: ReportItem): Step {
    let status = Status.RUNNING;
    switch (obj.status) {
      case 'COMPLETED':
        status = Status.COMPLETED;
        break;
      case 'FAILED':
        status = Status.FAILED;
        break;
      case 'SKIPPED':
        status = Status.SKIPPED;
        break;
      case 'PENDING':
        status = Status.PENDING;
        break;
    }
    return {
      title: obj.title,
      description: obj.description,
      status: status,
      progress: obj.progress,
    };
  }

  async downloadVulnReport(reportCard: ReportCard) {
    const reportName = reportCard.name;
    const reportFormat = 'pdf';

    const apiHost = new URL(this.ws.URL).host;

    // Construct the URL with query parameters
    const url = `http://${apiHost}/download_report?name=${encodeURIComponent(reportName)}&format=${encodeURIComponent(reportFormat)}`;

    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'X-API-Key': this.apiKey,
      },
    });

    if (!response.ok) {
      console.log('Failed to download response');
    }
    const file = await response.blob();

    // Create a temporary download link
    const downloadUrl = window.URL.createObjectURL(file);
    const a = document.createElement('a');
    a.href = downloadUrl;
    a.download = `${reportName}.${reportFormat}`; // Set the filename
    document.body.appendChild(a);
    a.click(); // Programmatically click the link to trigger the download
    document.body.removeChild(a); // Remove the link element
    window.URL.revokeObjectURL(downloadUrl); // Clean up the URL object
  }

  // Scrolling to have new messages visible

  @ViewChildren('chatItem') chatItemElements!: QueryList<ElementRef>;

  ngAfterViewInit() {
    this.scrollToBottom();
  }

  prevChatItemsLength: number = 0;

  ngAfterViewChecked() {
    if (this.chatItems.length != this.prevChatItemsLength) {
      this.prevChatItemsLength = this.chatItems.length;
      this.scrollToBottom();
    }
  }

  private scrollToBottom(): void {
    if (this.chatItemElements && this.chatItemElements.last) {
      const lastMessage: Element = this.chatItemElements.last.nativeElement;
      /**
       * There seems to be a race condition here. Without using the timeout,
       * the scroll is not done properly (the top of the element will be shown,
       * but not the whole element), this seems to be because the rendering is
       * not yet complete at this time. Set the timeout to 5ms, because it is
       * not really noticeable and seems to work.
       */
      setTimeout(() => lastMessage.scrollIntoView(), 5);
    }
  }

  // Export message history

  private exportChat(): string {
    let markdown = '# STARS Chat History\n';
    this.chatItems.forEach(cI => {
      if ('message' in cI) {
        const msg = cI;
        const date = new Date(msg.timestamp);
        // Format timestamp as YYYY-MM-DD HH:MM:SS
        const timestampStr = date.toISOString().replace('T', ' ').substr(0, 19);

        // Add message metadata
        markdown += `## ${msg.id}\n`;
        markdown += `**Timestamp:** ${timestampStr}\n\n`;

        // Add message content
        markdown += `${msg.message}\n\n`;
      } else {
        // TODO: Include vuln reports in export.
      }
    });

    return markdown;
  }

  downloadChatHistory(): void {
    const markdownContent = this.exportChat();
    const blob = new Blob([markdownContent], {type: 'text/markdown'});

    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = 'STARS_chat_' + new Date().toISOString() + '.md';

    // Append the link to the body
    document.body.appendChild(link);

    // Programmatically click the link to trigger the download
    link.click();

    // Clean up
    document.body.removeChild(link);
  }

  // Setting API Key

  promptForAPIKey(): void {
    this.apiKey = prompt('Set API Key', this.apiKey) || this.apiKey;
    localStorage.setItem('key', this.apiKey);
  }

  // openDashboard() that loads a new page with the dashboard at the route /heatmap
  openDashboard(): void {
    window.open('/heatmap', '_blank');
  }
}
