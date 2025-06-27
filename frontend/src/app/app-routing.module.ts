import {RouterModule, Routes} from '@angular/router';

import {ChatzoneComponent} from './chatzone/chatzone.component';
import {HeatmapComponent} from './heatmap/heatmap.component';
import {NgModule} from '@angular/core';

const routes: Routes = [
  {path: '', component: ChatzoneComponent},
  {path: 'heatmap', component: HeatmapComponent},
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule],
})
export class AppRoutingModule {}
