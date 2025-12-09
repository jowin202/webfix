import { Routes } from '@angular/router';
import { LoginForm } from './components/login-form/login-form';
import { ChatWindow } from './components/chat-window/chat-window';
import { RegisterForm } from './components/register-form/register-form';
import { ResetPasswordForm } from './components/reset-password-form/reset-password-form';
import { ForgotPasswordForm } from './components/forgot-password-form/forgot-password-form';

import { authGuard, authGuardAdmin, rootRedirectGuard } from './auth.guard';  // <-- wichtig
import { RootRedirect } from './components/root-redirect/root-redirect';



export const routes: Routes = [

  // -------------------------------------------------------------
  // ROOT ROUTE "/"
  // entscheidet dynamisch je nach Login-Status
  // → eingeloggt  → /chat
  // → nicht eingeloggt → /login
  // -------------------------------------------------------------
  {
    path: '',
    component: RootRedirect,
    pathMatch: 'full'
  },

  // -------------------------------------------------------------
  // AUTH Seiten
  // -------------------------------------------------------------
  { path: 'login', component: LoginForm },
  { path: 'register', component: RegisterForm },
  { path: 'recovery/:token', component: ResetPasswordForm },
  { path: 'forgot-password', component: ForgotPasswordForm },

  // -------------------------------------------------------------
  // CHAT – nur verfügbar wenn eingeloggt
  // -------------------------------------------------------------
  {
    path: 'chat',
    component: ChatWindow,
    canActivate: [authGuard]
  },

  // -------------------------------------------------------------
  // Fallback: alles → root → loader entscheidet
  // -------------------------------------------------------------
  { path: '**', redirectTo: '' }
];
