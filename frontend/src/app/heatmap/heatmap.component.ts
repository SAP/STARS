import { AfterViewInit, ChangeDetectorRef, Component, ElementRef, OnInit } from '@angular/core';
import { capitalizeFirstLetter, splitModelName } from '../utils/utils';

import ApexCharts from 'apexcharts';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { ScoreResponse } from './../types/API';
import { environment } from '../../environments/environment';

@Component({
  selector: 'app-heatmap',
  templateUrl: './heatmap.component.html',
  styleUrls: ['./heatmap.component.css'],
  standalone: true,
  imports: [CommonModule, MatFormFieldModule, MatSelectModule, FormsModule, MatCardModule, MatButtonModule],
})
export class HeatmapComponent implements AfterViewInit, OnInit {
  constructor(private http: HttpClient, private el: ElementRef, private changeDetector: ChangeDetectorRef) {}

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
    let modelNames: string[] = [];
    let attackNames: string[] = [];
    modelNames = data.models.map(model => model.name);
    attackNames = data.attacks.map(attack => attack.name);
    this.createHeatmap(data, modelNames, attackNames);
  }

  // Create the heatmap chart with the processed data
  createHeatmap(data: ScoreResponse, modelNames: string[] = [], attackNames: string[] = []) {
    const cellSize = 100;
    const chartWidth = (attackNames.length + 1) * cellSize + 200; // +1 to add exposure column +200 to allow some space for translated labels
    const chartHeight = data.models.length <= 3 ? data.models.length * cellSize + 300 : data.models.length * cellSize;
    let allModels: any[] = []; // Initialize an empty array to hold all results
    const xaxisCategories = [...attackNames, 'Exposure score'];

    // Build a lookup for attack weights
    const attackWeights: Record<string, number> = {};
    data.attacks.forEach(attack => {
      attackWeights[attack.name] = attack.weight ?? 1; // default weight to 1 if undefined
    });
    
    data.models.forEach(model => {
      // Copy scores to avoid mutating the original object
      const standalone_scores = structuredClone(model.scores);

      // Get PromptMap scores to be computed together
      const pm_scores = (model.scores['promptmap-SPL'] ?? 0) + (model.scores['promptmap-PI'] ?? 0);
      // Clean up PromptMap scores to avoid double counting them
      delete standalone_scores['promptmap-SPL'];
      delete standalone_scores['promptmap-PI'];

      // Get PromptMap weights to be computed together
      const pm_weight = (attackWeights['promptmap-SPL'] ?? 0) + (attackWeights['promptmap-PI'] ?? 0);

      // Get attack names and scores
      const weights = attackNames.map(name => attackWeights[name] ?? 0);
      const scores = attackNames.map(name => standalone_scores[name] ?? 0);

      // Calculate exposure score
      const exposureScore = (() => {
        const totalWeight = weights.reduce((a, b) => a + b, 0);
        if (totalWeight === 0) return 0;
        const weightedSum =
          pm_scores * pm_weight +
          scores.reduce((sum, score, i) => sum + score * weights[i], 0);

        return Math.round(weightedSum / totalWeight);
      })();

      // Prepare the series data for the heatmap mapping attacks to models and their scores
      const seriesData = {
        name: model.name,
        data: [
          ...attackNames.map(name => ({
            x: name,
            y: model.scores[name] ?? 0,
          })),
          // Add exposure score manually as the last column
          {
            x: 'Exposure score',
            y: exposureScore,
          },
        ],
      };
      allModels.push(seriesData);
    });
    // Create the heatmap chart with the processed data and parameters
    const options = {
      chart: {
        type: 'heatmap',
        height: chartHeight,
        width: chartWidth,
        toolbar: {show: false},
      },
      series: allModels,
      plotOptions: {
        heatmap: {
          shadeIntensity: 0.5,
          colorScale: {
            ranges: [
              {from: 0, to: 40, color: '#00A100'},
              // {from: 21, to: 40, color: '#128FD9'},
              {from: 41, to: 80, color: '#FF7300'},
              // {from: 61, to: 80, color: '#FFB200'},
              {from: 81, to: 100, color: '#FF0000'},
            ],
          },
        },
      },
      grid: {
        // Add padding to the top so we can space the x-axis title
        padding: {top: 30, right: 0, bottom: 0, left: 0},
      },
      dataLabels: {
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
            return splitName
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
          const value = series[seriesIndex][dataPointIndex];
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
}
