import {AfterViewInit, ChangeDetectorRef, Component, ElementRef, OnInit} from '@angular/core';
import {Observable, map} from 'rxjs';
import {capitalizeFirstLetter, generateModelName, splitModelName} from '../utils/utils';

import ApexCharts from 'apexcharts';
import {CommonModule} from '@angular/common';
import {FormsModule} from '@angular/forms';
import {HttpClient} from '@angular/common/http';
import {MatButtonModule} from '@angular/material/button';
import {MatCardModule} from '@angular/material/card';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatSelectModule} from '@angular/material/select';
import {environment} from '../../environments/environment';

@Component({
  selector: 'app-heatmap',
  templateUrl: './heatmap.component.html',
  styleUrls: ['./heatmap.component.css'],
  standalone: true,
  imports: [CommonModule, MatFormFieldModule, MatSelectModule, FormsModule, MatCardModule, MatButtonModule],
})
export class HeatmapComponent implements AfterViewInit, OnInit {
  public heatmapData: number[][] = [];
  // for UI dropdown menu of vendors
  public vendorsNames: string[] = [];
  public selectedVendor: string = '';
  public weightedAttacks: {attackName: string; weight: string}[] = [];

  constructor(private http: HttpClient, private el: ElementRef, private changeDetector: ChangeDetectorRef) {}

  ngAfterViewInit() {
    this.createHeatmap([]); // Initialisation avec des données vides
  }

  ngOnInit() {
    // this.loadHeatmapData('amazon');
    this.loadVendorsData();
    this.loadHeatmapData('');
  }

  onFileSelected(event: any) {
    // const file = event.target.files[0];
    // if (!file) return;
    // const formData = new FormData();
    // formData.append('file', file);
    // this.http.post<any[]>('http://localhost:3000/upload', formData).subscribe({
    //   next: data => {
    //     console.log('📊 Données reçues via upload:', data);
    //     this.processData(data);
    //   },
    //   error: error => console.error('❌ Erreur upload:', error),
    // });
  }

  //load a dropdown menu from the loadModelsData result
  loadVendorsData() {
    // this.http.get<string[]>(`http://127.0.0.1:8080/api/vendors`).subscribe({
    this.http.get<string[]>(`${environment.api_url}/api/vendors`).subscribe({
      next: data => {
        console.log('📡 Données brutes reçues du serveur:', data);
        this.processVendors(data.map(vendor => vendor));
      },
      error: error => console.error('❌ Erreur API:', error),
    });
  }

  //load the heatmap data from the server with a name in params
  loadHeatmapData(vendor: string) {
    let url = '';
    if (!vendor) {
      url = `${environment.api_url}/api/heatmap`;
    } else {
      url = `${environment.api_url}/api/heatmap/${vendor}`;
    }
    this.http.get<string[]>(url).subscribe({
      // this.http.get<any[]>(`${environment.api_url}/api/${vendor}`).subscribe({
      next: scoresData => {
        this.processData(scoresData, vendor);
      },
      error: error => console.error('❌ Erreur API:', error),
    });
  }

  // handle models name recieved from the server to a list used in frontend for a dropdown menu
  processVendors(vendorsNames: string[]) {
    this.vendorsNames = vendorsNames.map(capitalizeFirstLetter);
  }

  processData(data: any[], vendor: string = '') {
    const modelNames = generateModelName(data, vendor);
    this.getWeightedAttacks().subscribe({
      next: weightedAttacks => {
        this.heatmapData = data.map(row => {
          const rowData = weightedAttacks.map(attack => {
            const value = Number(row[attack.attackName]?.trim());
            return isNaN(value) ? 0 : value * 10;
          });
          let totalWeights = 0;
          // Add an extra column at the end with a custom calculation (modify as needed)
          const weightedSumColumn = weightedAttacks.reduce((sum, {attackName, weight}) => {
            const value = Number(row[attackName]?.trim());
            const weightedValue = isNaN(value) ? 0 : value * Number(weight);
            totalWeights = totalWeights + Number(weight);
            return sum + weightedValue;
          }, 0);
          // Append the calculated weighted sum column to the row as the last column "as an attack" even if it's a custom calculated value
          return [...rowData, (weightedSumColumn / totalWeights) * 10];
        });
        const attackNames = weightedAttacks.map(attack => attack.attackName);
        this.createHeatmap(this.heatmapData, modelNames, [...attackNames.map(capitalizeFirstLetter), 'Exposure score'], vendor !== '');
      },
      error: error => console.error('❌ Erreur API:', error),
    });
  }

  createHeatmap(data: number[][], modelNames: Record<string, string[]> = {}, attackNames: string[] = [], oneVendorDisplayed: boolean = false) {
    const cellSize = 100;
    const chartWidth = attackNames.length * cellSize + 150; // +100 to allow some space for translated labels
    const chartHeight = data.length <= 3 ? data.length * cellSize + 100 : data.length * cellSize;
    // const series = Object.entries(modelNames).flatMap(([vendor, models]) =>
    //   models.map((model, modelIndex) => ({
    //     name: splitModelName(vendor, model),
    //     data: data[modelIndex].map((value, colIndex) => ({
    //       x: attackNames[colIndex],
    //       y: value,
    //     })),
    //   }))
    // );

    // // group by vendors
    // let globalIndex = 0;
    // const series = Object.entries(modelNames).flatMap(([vendor, models]) =>
    //   models.map(model => {
    //     const seriesData = {
    //       name: splitModelName(vendor, model),
    //       data: data[globalIndex].map((value, colIndex) => ({
    //         x: attackNames[colIndex],
    //         y: value,
    //       })),
    //     };
    //     globalIndex++; // Increment global index for next model
    //     return seriesData;
    //   })
    // );

    // does not group by vendor
    // Flatten all models but keep vendor info
    const allModels = Object.entries(modelNames).flatMap(([vendor, models]) => models.map(model => ({vendor, model})));

    let globalIndex = 0;

    const series = allModels.map(({vendor, model}) => {
      const seriesData = {
        name: splitModelName(vendor, model), // Display vendor and model together
        data: data[globalIndex].map((value, colIndex) => ({
          x: attackNames[colIndex],
          y: value,
        })),
      };
      globalIndex++; // Move to next row in data
      return seriesData;
    });

    const options = {
      chart: {
        type: 'heatmap',
        height: chartHeight,
        width: chartWidth,
        toolbar: {show: false},
        events: {
          legendClick: function () {
            console.log('CLICKED');
          },
        },
      },
      series: series,
      plotOptions: {
        heatmap: {
          shadeIntensity: 0.5,
          // useFillColorAsStroke: true, // Améliore le rendu des cases
          colorScale: {
            ranges: [
              // {from: 0, to: 20, color: '#5aa812'}, // Light green for 0-20
              // {from: 21, to: 40, color: '#00A100'}, // Darker green for 21-40
              // {from: 41, to: 60, color: '#FFB200'}, // Light orange for 41-60
              // {from: 61, to: 80, color: '#FF7300'}, // Darker orange for 61-80
              // {from: 81, to: 100, color: '#FF0000'}, // Red for 81-100

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
        padding: {top: 0, right: 0, bottom: 0, left: 0},
      },
      dataLabels: {
        style: {fontSize: '14px'},
      },
      legend: {
        show: true,
        // markers: {
        //   customHTML: function () {
        //     return '<span class="custom-marker"><i class="fa-solid fa-square"></i></span>';
        //   },
        // },
        // markers: {
        //   width: 12,
        //   height: 12,
        //   // Remove customHTML if you want the default
        // },
      },
      xaxis: {
        categories: attackNames,
        title: {text: 'Attacks'},
        labels: {rotate: -45, style: {fontSize: '12px'}},
        position: 'top',
      },
      yaxis: {
        categories: modelNames,
        title: {
          text: 'Models',
          offsetX: oneVendorDisplayed ? -90 : -60,
        },
        labels: {
          style: {
            fontSize: '12px',
          },
          offsetY: -10,
        },
        reversed: true,
      },
      tooltip: {
        y: {
          formatter: undefined,
          title: {
            formatter: (seriesName: string) => seriesName.replace(',', '-'),
          },
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

  public onVendorChange(event: any) {
    this.loadHeatmapData(this.selectedVendor);
  }

  // getattacksNames() return an array of attacks names from the server from http://localhost:3000/api/attacks
  getAttacksNames(): Observable<string[]> {
    return this.http.get<any[]>(`${environment.api_url}/api/attacks`).pipe(
      // return this.http.get<any[]>(`http://127.0.0.1:8080/api/attacks`).pipe(
      map(data => data.map(row => row['attackName'])) // Extract only attack names
    );
  }

  getWeightedAttacks(): Observable<{attackName: string; weight: string}[]> {
    return this.http.get<any[]>(`${environment.api_url}/api/attacks`);
    // return this.http.get<any[]>(`http://127.0.0.1:8080/api/attacks`);
  }

  getVendors(): Observable<any[]> {
    this.changeDetector.detectChanges();
    return this.http.get<any[]>(`${environment.api_url}/api/vendors`);
    // return this.http.get<any[]>(`http://127.0.0.1:8080/api/vendors`);
  }

  uploadCSV(event: any) {
    const file = event.target.files[0];
    const formData = new FormData();
    formData.append('file', file);

    this.http.post<any>(`${environment.api_url}/api/upload-csv`, formData).subscribe({
      next: res => {
        console.log('Upload success', res);
      },
      error: err => {
        console.error('Upload failed', err);
      },
    });
  }
}
