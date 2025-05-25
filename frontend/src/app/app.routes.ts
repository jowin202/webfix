import { Routes } from '@angular/router';
import { LoginWindowComponent } from './components/login-window/login-window.component';
import { RegisterWindowComponent } from './components/register-window/register-window.component';

export const routes: Routes = [
  { path: '', component: LoginWindowComponent },
  { path: 'register', component: RegisterWindowComponent },
  //{ path: 'forgot-password', component: ForgotPasswordComponent },
];