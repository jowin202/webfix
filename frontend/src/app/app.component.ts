import { Component, OnInit } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { ChatWindowComponent } from "./components/chat-window/chat-window.component";
import { LoginWindowComponent } from "./components/login-window/login-window.component";
import { AuthService } from './services/auth.service';
import { CommonModule } from '@angular/common';
import { ApiService } from './services/api.service';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, CommonModule],
  templateUrl: './app.component.html',
  styleUrl: './app.component.scss'
})
export class AppComponent implements OnInit {
  title = 'webfix';

  loginData = {};

  constructor (public auth : AuthService, public api : ApiService){}

  ngOnInit(): void {
        this.api.get("/api/register/login_page/", this.auth.token) // no token needed
        .subscribe(result => {
          this.loginData = result
        });
  }

  
}
