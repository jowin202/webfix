import { CommonModule } from '@angular/common';
import { Component, OnDestroy, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';
import { Observable } from 'rxjs';
import { AuthService } from '../../services/auth.service';


interface ChatMessage {
  username: string;
  message: string;
}


@Component({
  selector: 'app-chat-window',
  imports: [CommonModule, FormsModule],
  templateUrl: './chat-window.component.html',
  styleUrl: './chat-window.component.scss'
})
export class ChatWindowComponent implements OnInit, OnDestroy{
  constructor (public api : ApiService, public auth : AuthService){}

  onlineUsers = ["Johannes", "Matthias"]

  
  messages : ChatMessage[] = []

  ngOnInit() {
    this.api.connect_stream("/ws2", this.auth.token).subscribe(result => {
      if ("username" in result && "message" in result){
        this.messages.push(result);
      }
    });
  }

  sendMessage(message : string) {
    if (message == "")
    {
      return;
    }
    else if (message == "/exit")
    {
      this.auth.do_logout();
    }

    this.api.post(`/api/input/?message=${encodeURIComponent(message)}`, this.auth.token, {})
        .subscribe(result => {
          //console.log('Server response:', result);
        });
  }

  ngOnDestroy() {

  }
}
