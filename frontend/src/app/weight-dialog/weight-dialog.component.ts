import { MAT_DIALOG_DATA, MatDialogActions, MatDialogRef } from "@angular/material/dialog";

import { Component, OnInit, inject } from '@angular/core';
import { HttpClient, HttpHeaders } from "@angular/common/http";

import { ConfigService } from '../services/config.service';
import { MatFormFieldModule, MatLabel } from "@angular/material/form-field";
import { CommonModule } from "@angular/common";
import { FormsModule } from "@angular/forms";
import { MatInputModule } from "@angular/material/input";
import { MatIconModule } from "@angular/material/icon";
import { MatButtonModule } from "@angular/material/button";
import { MatSnackBar } from "@angular/material/snack-bar";

@Component({
  selector: 'app-weight-dialog',
  imports: [MatDialogActions, MatFormFieldModule, MatLabel, CommonModule, FormsModule, MatInputModule, MatIconModule, MatButtonModule],
  templateUrl: './weight-dialog.component.html',
  styleUrls: ['./weight-dialog.component.css']
})
export class WeightDialogComponent implements OnInit {
  private http = inject(HttpClient);
  dialogRef = inject<MatDialogRef<WeightDialogComponent>>(MatDialogRef);
  private snackBar = inject(MatSnackBar);
  private configService = inject(ConfigService);
  data = inject(MAT_DIALOG_DATA);

  currentWeights: { [attack: string]: number } = {};
  attackNames: string[] = [];
  apiKey: string;
  constructor() {
    this.apiKey = localStorage.getItem('key') || '';
  }

  ngOnInit(): void {
    this.currentWeights = this.data.weights || {};
    this.attackNames = this.data.attackNames || [];
  }

  onSave() {
    // Validate weights before sending
    const invalidWeights = Object.entries(this.currentWeights)
      .filter(([_, weight]) => weight < 0 || !Number.isInteger(weight));

    if (invalidWeights.length > 0) {
      this.snackBar.open('Please enter valid positive integers for all weights', '❌', {
        duration: 3000
      });
      return;
    }

    const headers = new HttpHeaders({
      'X-API-Key': this.apiKey
    });

    this.http.put(`${this.configService.apiUrl}/api/attacks`, this.currentWeights, { headers })
      .subscribe({
        next: () => {
          this.snackBar.open('Weights successfully updated ', '✅', {
            duration: 3000,
            horizontalPosition: 'right',
            verticalPosition: 'top',
          });
          this.dialogRef.close(true);
        },
        error: err => {
          this.snackBar.open('Error updating weights, verify your input and try again later.', '❌', {
            duration: 5000,
            horizontalPosition: 'right',
            verticalPosition: 'top',
          });
          console.error('Error updating weights, verify your input and try again later.', err);
          this.dialogRef.close(true);
        }
      });
  }
}
