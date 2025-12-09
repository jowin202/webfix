import { Routes } from '@angular/router';
import { LoginForm } from './components/login-form/login-form';
import { ChatWindow } from './components/chat-window/chat-window';
import { RegisterForm } from './components/register-form/register-form';
import { ResetPasswordForm } from './components/reset-password-form/reset-password-form';
import { ForgotPasswordForm } from './components/forgot-password-form/forgot-password-form';

export const routes: Routes = [
  { path: 'login', component: LoginForm },
  { path: 'register', component: RegisterForm },
  { path: 'recovery/:token', component: ResetPasswordForm },
  { path: 'forgot-password', component: ForgotPasswordForm},
  { path: '**', component: ChatWindow}
];
