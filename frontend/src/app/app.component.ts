import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { ChatWindowComponent } from "./components/chat-window/chat-window.component";
import { LoginWindowComponent } from "./components/login-window/login-window.component";
import { AuthService } from './services/auth.service';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, CommonModule, ChatWindowComponent, LoginWindowComponent],
  templateUrl: './app.component.html',
  styleUrl: './app.component.scss'
})
export class AppComponent {
  title = 'webfix';

  constructor (public auth : AuthService){}
}
