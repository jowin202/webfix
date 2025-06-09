import { Router, Routes } from '@angular/router';
import { LoginWindowComponent } from './components/login-window/login-window.component';
import { RegisterWindowComponent } from './components/register-window/register-window.component';
import { ChatWindowComponent } from './components/chat-window/chat-window.component';
import { AuthService } from './services/auth.service';
import { inject } from '@angular/core';
import { RecoverPasswordComponent } from './components/recover-password/recover-password.component';
import { ForgotPasswordComponent } from './components/forgot-password/forgot-password.component';
import { UserMenuComponent } from './components/user-menu/user-menu.component';



const canActivateChat = () => {
  const auth = inject(AuthService);
  const router = inject(Router);

  if (auth.logged_in) {
    return true;
  } else {
    router.navigate(['/login']);
    return false;
  }
};


export const routes: Routes = [
  { path: '', component: LoginWindowComponent },
  { path: 'login', component: LoginWindowComponent },
  { path: 'register', component: RegisterWindowComponent },
  { path: 'chat', component: ChatWindowComponent, canActivate: [canActivateChat] },
  { path: 'recovery/:token', component: RecoverPasswordComponent },
  { path: 'forgot-password', component: ForgotPasswordComponent},
  { path: 'menu', component: UserMenuComponent },
  { path: '**', component: LoginWindowComponent },
];