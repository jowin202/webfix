import { Component, Inject, PLATFORM_ID } from '@angular/core';
import { Router } from '@angular/router';
import { isPlatformBrowser, CommonModule } from '@angular/common';
import { AuthService } from '../../services/auth.service';
import { toObservable } from '@angular/core/rxjs-interop';
import { filter, take } from 'rxjs';

import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatCardModule } from '@angular/material/card';

@Component({
  selector: 'app-root-redirect',
  standalone: true,
  imports: [
    CommonModule,
    MatProgressSpinnerModule,
    MatCardModule
  ],
  template: `
    <div class="redirect-container">
      <mat-card class="redirect-card">
        <div class="spinner-wrapper">
          <mat-progress-spinner
            mode="indeterminate"
            diameter="60"
            strokeWidth="5">
          </mat-progress-spinner>
        </div>

        <div class="redirect-text">
          Loading…
        </div>
      </mat-card>
    </div>
  `,
  styleUrls: ['./root-redirect.scss']
})
export class RootRedirect {

  constructor(
    private auth: AuthService,
    private router: Router,
    @Inject(PLATFORM_ID) private platformId: Object
  ) {

    // SSR → keine Navigation
    if (!isPlatformBrowser(this.platformId)) {
      return;
    }

    // Browser → warten bis Auth ready ist
    toObservable(this.auth.ready.asReadonly()).pipe(
      filter(r => r === true),
      take(1)
    ).subscribe(() => {

      if (this.auth.logged_in()) {
        this.router.navigateByUrl('/chat');
      } else {
        this.router.navigateByUrl('/login');
      }
    });
  }
}
