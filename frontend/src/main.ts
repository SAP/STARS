import { importProvidersFrom, inject, provideAppInitializer } from '@angular/core';

import  { AppComponent } from './app/app.component';
import { AppRoutingModule } from './app/app-routing.module';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { ConfigService } from './app/services/config.service';
import { FormsModule } from '@angular/forms';
import { HttpClientModule } from '@angular/common/http';
import { MarkdownModule } from 'ngx-markdown';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MaterialModule } from './app/material.module';
import { bootstrapApplication } from '@angular/platform-browser';

bootstrapApplication(AppComponent, {
  providers: [
    importProvidersFrom(AppRoutingModule, BrowserAnimationsModule, FormsModule, HttpClientModule, MaterialModule, MarkdownModule.forRoot(), MatProgressBarModule),
    ConfigService,
    provideAppInitializer(() => {
      const configService = inject(ConfigService);
      // Return a Promise or Observable for async initialization
      return configService.loadConfig();
    }),
  ],
}).catch(err => console.error(err));
