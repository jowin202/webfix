import { CommonModule } from '@angular/common';
import { Component, OnDestroy, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';
import { Observable } from 'rxjs';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-chat-window',
  imports: [CommonModule, FormsModule],
  templateUrl: './chat-window.component.html',
  styleUrl: './chat-window.component.scss'
})
export class ChatWindowComponent implements OnInit, OnDestroy{
  constructor (public api : ApiService, public auth : AuthService){}

  onlineUsers = ["Johannes", "Matthias"]
  messages = [{"sender": "Hugo", "text": "Hallo, wie gehts?"}]

  ngOnInit() {
    this.api.connect_stream("/ws2", this.auth.token).subscribe(result => {
      console.log(result);
    });
  }

  sendMessage(message : string) {
    this.api.post(`/api/input/?message=${encodeURIComponent(message)}`, this.auth.token, {})
        .subscribe(result => {
          //console.log('Server response:', result);
        });
  }

  ngOnDestroy() {

  }
}
