import { AppComponent } from './app.component';
import { AppRoutingModule } from './app-routing.module';
import { BrowserAnimationsModule } from '@angular/platform-browser/animations';
import { BrowserModule } from '@angular/platform-browser';
import { ChatzoneComponent } from './chatzone/chatzone.component';
import { FormsModule } from '@angular/forms';
import { HttpClientModule } from '@angular/common/http';
import { MaterialModule } from './material.module';
import { NgModule } from '@angular/core';
import { MarkdownModule } from 'ngx-markdown';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { APP_INITIALIZER } from '@angular/core';
import { ConfigService } from './services/config.service';
import { lastValueFrom } from 'rxjs';

export function initializeApp(configService: ConfigService) {
  return () => lastValueFrom(configService.loadConfig());
}

@NgModule({
  declarations: [
    AppComponent,
    ChatzoneComponent
  ],
  imports: [
    BrowserModule,
    AppRoutingModule,
    FormsModule,
    HttpClientModule,
    BrowserAnimationsModule,
    MaterialModule,
    MarkdownModule.forRoot(),
    MatProgressBarModule,
  ],
  providers: [{
    provide: APP_INITIALIZER,
    useFactory: initializeApp,
    deps: [ConfigService],
    multi: true
  }],
  bootstrap: [AppComponent]
})
export class AppModule { }
