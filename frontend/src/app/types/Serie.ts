interface HeatmapPoint {
  x: string;
  y: number;
}

export interface HeatmapSeries {
  name: string;
  data: HeatmapPoint[];
}