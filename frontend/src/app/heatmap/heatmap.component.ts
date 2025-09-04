import { AfterViewInit, Component, ElementRef, OnInit, inject } from '@angular/core';
import { capitalizeFirstLetter, splitModelName } from '../utils/utils';

import ApexCharts from 'apexcharts';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatDialog } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatSelectModule } from '@angular/material/select';
import { ScoreResponse } from './../types/API';
import { WeightDialogComponent } from '../weight-dialog/weight-dialog.component';
import { environment } from '../../environments/environment';

@Component({
  selector: 'app-heatmap',
  templateUrl: './heatmap.component.html',
  styleUrls: ['./heatmap.component.css'],
  standalone: true,
  imports: [CommonModule, MatFormFieldModule, MatSelectModule, FormsModule, MatCardModule, MatButtonModule, MatIconModule],
})
export class HeatmapComponent implements AfterViewInit, OnInit {
  private http = inject(HttpClient);
  private el = inject(ElementRef);
  private dialog = inject(MatDialog);

  private latestData: ScoreResponse | null = null;
  private attackNames: string[] = [];
  private attackWeights: { [attackName: string]: number } = {};

  ngAfterViewInit() {
    this.createHeatmap({
      attacks: [],
      models: [],
    }); // Initialize empty heatmap to avoid errors before data is loaded
  }

  ngOnInit() {
    this.loadHeatmapData();
  }

  // Load the heatmap data from the server
  loadHeatmapData() {
    let url = '';
    url = `${environment.api_url}/api/heatmap`;
    this.http.get<ScoreResponse>(url).subscribe({
      next: scoresData => {
        this.processDataAfterScan(scoresData);
      },
      error: error => console.error('❌ Erreur API:', error),
    });
  }

  // Construct the heatmap data from the API response
  processDataAfterScan(data: ScoreResponse) {
    this.latestData = data;
    let modelNames: string[] = [];
    modelNames = data.models.map(model => model.name);
    this.attackNames = data.attacks.map(attack => attack.name);
    this.attackWeights = Object.fromEntries(
      data.attacks.map(attack => [attack.name, attack.weight ?? 1])
    );
    this.createHeatmap(data, modelNames, this.attackNames);
  }

  // Create the heatmap chart with the processed data
  createHeatmap(data: ScoreResponse, modelNames: string[] = [], attackNames: string[] = []) {
    const cellSize = 100;
    const chartWidth = (attackNames.length + 1) * cellSize + 200; // +1 to add exposure column +200 to allow some space for translated labels
    const chartHeight = data.models.length <= 3 ? data.models.length * cellSize + 300 : data.models.length * cellSize;

    const xaxisCategories = [...attackNames, 'Exposure score'];
    const allAttackWeights = Object.fromEntries(
      data.attacks.map(attack => [attack.name, attack.weight ?? 1])
    );
    const seriesData: any[] = [];
    // Process each model's scores and calculate the exposure score
    data.models.forEach(model => {
      let weightedSum = 0;
      let totalWeight = 0;

      attackNames.forEach(attack => {
        const weight = allAttackWeights[attack] ?? 1;
        const score = model.scores[attack];

        if (score !== undefined && score !== null) {
          weightedSum += score * weight;
          totalWeight += weight;
        }
      });

      const exposureScore = totalWeight > 0 ? Math.round(weightedSum / totalWeight) : 0;
      seriesData.push({
        name: model.name,
        data: [
          ...attackNames.map(name => ({
            x: name,
            y: model.scores.hasOwnProperty(name) ? model.scores[name] : -1,
          })),
          {
            x: 'Exposure score',
            y: exposureScore,
          },
        ],
      });
    });
    // Create the heatmap chart with the processed data and parameters
    const options = {
      chart: {
        type: 'heatmap',
        height: chartHeight,
        width: chartWidth,
        toolbar: {show: false},
      },
      series: seriesData,
      plotOptions: {
        heatmap: {
          shadeIntensity: 0.5,
          colorScale: {
            ranges: [
              {from: -10, to: 0, color: '#cccccc', name: 'N/A'}, // Color for unscanned cells = '-'
              {from: 0, to: 40, color: '#00A100', name: '0% - 40%'},
              // {from: 21, to: 40, color: '#128FD9'},
              {from: 41, to: 80, color: '#FF7300', name: '41% - 80%'},
              // {from: 61, to: 80, color: '#FFB200'},
              {from: 81, to: 100, color: '#FF0000', name: '81% - 100%'},
            ],
          },
        },
      },
      grid: {
        // Add padding to the top so we can space the x-axis title
        padding: {top: 30, right: 0, bottom: 0, left: 0},
      },
      dataLabels: {
        // Format the data labels visualized in the heatmap cells
        formatter: function (val: number | null) {
          return (val === null || val < 0) ? '-' : `${val}%`;
        },
        style: {
          // Size of the numbers in the cells
          fontSize: '14px'
        },
      },
      legend: {
        // Shows the colors legend of the heatmap
        show: true,
      },
      xaxis: {
        categories: xaxisCategories.map(capitalizeFirstLetter),
        title: { 
          text: 'Attacks',
          offsetY: -20,
        },
        labels: {
          rotate: -45,
          style:
          {
            fontSize: '12px'
          }
        },
        position: 'top',
        tooltip: {
          enabled: false  // Disable tooltip buble above the x-axis
        },
      },
      yaxis: {
        categories: modelNames,
        title: {
          text: 'Models',
          offsetX: -75,
        },
        labels: {
          formatter: function (modelName: string) {
            if (typeof modelName !== 'string') {
              return modelName; // Return as is when it's a number
            }
              const splitName = splitModelName(modelName);
              return splitName;
          },
          style: {
            fontSize: '12px',
            whiteSpace: 'pre-line',
          },
          offsetY: -10,
        },
        reversed: true,
      },
      tooltip: {
        enabled: true,
        custom: function({
          series,
          seriesIndex,
          dataPointIndex,
          w
        }: {
          series: any[];
          seriesIndex: number;
          dataPointIndex: number;
          w: any;
        }) {
          // Handle the case where the score is -1 (unscanned) and display 'N/A' in the tooltip
          const value = series[seriesIndex][dataPointIndex] === -1 ? 'N/A' : series[seriesIndex][dataPointIndex] + '%';
          const yLabel = capitalizeFirstLetter(w.globals.initialSeries[seriesIndex].name);
          const xLabel = capitalizeFirstLetter(w.globals.labels[dataPointIndex]);
          // Html format the tooltip content with title = model name and body = attack name and score
          return `
            <div style="
              background: white; 
              color: black; 
              padding: 6px 10px; 
              border-radius: 4px; 
              box-shadow: 0 2px 6px rgba(0,0,0,0.15);
              font-size: 12px;
            ">
              <div style="font-weight: bold; margin-bottom: 4px;">${yLabel}</div>
              <hr style="border: none; border-top: 1px solid #ccc; margin: 4px 0;">
              <div>${xLabel}: ${value}</div>
            </div>
          `;        
        },
      },
    };
    const chartElement = this.el.nativeElement.querySelector('#heatmapChart');
    if (chartElement) {
      chartElement.innerHTML = '';
      const chart = new ApexCharts(chartElement, options);
      chart.render();
    }
  }

  closeAndReturn() {
    window.close(); // Closes the tab and go back to the previous page = the agent
  }

  openWeightDialog() {
    if (!this.latestData) return;

    const dialogRef = this.dialog.open(WeightDialogComponent, {
      width: '500px',
      data: {
        title: 'Update weights',
        weights: this.attackWeights,
        attackNames: this.attackNames,
      }
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result === true) {
        // Reload the heatmap data after weights successfully updated
        this.loadHeatmapData();
      }
    });
  }
}
