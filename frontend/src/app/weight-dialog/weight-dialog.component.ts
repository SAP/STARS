import { MAT_DIALOG_DATA, MatDialogActions, MatDialogContent, MatDialogRef } from "@angular/material/dialog";

import { Component, Inject, OnInit } from '@angular/core';
import { HttpClient, HttpHeaders } from "@angular/common/http";

import { environment } from '../../environments/environment';
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
  currentWeights: { [attack: string]: number } = {};
  attackNames: string[] = [];
  apiKey: string;
  constructor(
    private http: HttpClient,
    public dialogRef: MatDialogRef<WeightDialogComponent>,
    private snackBar: MatSnackBar,
    @Inject(MAT_DIALOG_DATA) public data: any
  ) {
    this.apiKey = localStorage.getItem('key') || '';
  }

  ngOnInit(): void {
    this.currentWeights = this.data.weights || {};
    this.attackNames = this.data.attackNames || [];
  }

  onSave() {
  const headers = new HttpHeaders({
      'X-API-Key': this.apiKey  // ← make sure this.apiKey is correctly defined
    });

  this.http.put(`${environment.api_url}/api/attacks`, this.currentWeights, { headers })
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
          console.error('Error updating weights, verify your input and try again later.');
        }
      });
  }
}
