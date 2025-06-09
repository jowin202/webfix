import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { AuthService } from '../../services/auth.service';
import { RouterModule } from '@angular/router';
import { ApiService } from '../../services/api.service';

@Component({
  selector: 'app-login-window',
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './login-window.component.html',
  styleUrl: './login-window.component.scss'
})
export class LoginWindowComponent {

  constructor (public auth : AuthService, public api : ApiService){}

  do_page_login(value : any){
    this.auth.do_login(value.username, value.password, value.remember);
  }

  do_guest_login(value : any){
    this.auth.do_guest_login(value.guestName, false);
  }
}
