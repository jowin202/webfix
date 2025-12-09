import { CanActivateFn, Router } from '@angular/router';
import { inject, PLATFORM_ID } from '@angular/core';
import { AuthService } from './services/auth.service';
import { toObservable } from '@angular/core/rxjs-interop';
import { filter, map, take } from 'rxjs';
import { isPlatformBrowser } from '@angular/common';

export const authGuard: CanActivateFn = () => {

  const platformId = inject(PLATFORM_ID);

  if (!isPlatformBrowser(platformId)) {
    return true;
  }

  const auth = inject(AuthService);
  const router = inject(Router);

  // Guard wartet *echt* bis ready = true
  return toObservable(auth.ready.asReadonly()).pipe(
    filter(ready => ready === true),
    take(1),
    map(() => {
      if (auth.logged_in()) {
        return true;
      }
      return router.createUrlTree(['/login']);
    })
  );
};





export const authGuardAdmin: CanActivateFn = () => {

  const platformId = inject(PLATFORM_ID);

  if (!isPlatformBrowser(platformId)) {
    return true;
  }

  const auth = inject(AuthService);
  const router = inject(Router);

  return toObservable(auth.ready.asReadonly()).pipe(
    filter(ready => ready === true),
    take(1),

    map(() => {
      const logged = auth.logged_in();
      const admin = auth.admin_level();
      if (logged && admin > 0) {
        return true;
      }

      return router.createUrlTree(['/login']);
    })
  );
};




export const rootRedirectGuard: CanActivateFn = () => {
  const platformId = inject(PLATFORM_ID);
  const auth = inject(AuthService);
  const router = inject(Router);

  // SSR: keine Entscheidung → Browser soll entscheiden
  if (!isPlatformBrowser(platformId)) {
    return true;
  }

  // Browser wartet auf auth.ready
  return toObservable(auth.ready.asReadonly()).pipe(
    filter(r => r === true),
    take(1),
    map(() => {
      if (auth.logged_in()) {
        console.log("[ROOT] logged in → redirect to /chat");
        return router.createUrlTree(['/chat']);
      } else {
        console.log("[ROOT] NOT logged in → redirect to /login");
        return router.createUrlTree(['/login']);
      }
    })
  );
};

