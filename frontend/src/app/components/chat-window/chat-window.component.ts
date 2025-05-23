import { CommonModule } from '@angular/common';
import { Component, ElementRef, OnDestroy, OnInit, ViewChild } from '@angular/core';
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

  @ViewChild('messagesContainer') private messagesContainer!: ElementRef;
  onlineUsers = ["Johannes", "Matthias"]

  
  messages : ChatMessage[] = []

  ngOnInit() {
    this.api.connect_stream("/ws2", this.auth.token).subscribe(result => {
      if ("username" in result && "message" in result){
        this.messages.push(result);
      }
      else if ("cat" in result && result['cat'] == "statusmsg" && "msg" in result)
      {
        this.messages.push({username: "ChatBot", "message" : "<i>" + result['msg'] + "</i>"})
      }
      else if ("cat" in result && result['cat'] == "announcement" && "msg" in result)
      {
        this.messages.push({username: "Announcement", "message" : "<i>" + result['msg'] + "</i>"})
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
      return;
    }

    this.api.post(`/api/input/?message=${encodeURIComponent(message)}`, this.auth.token, {})
        .subscribe(result => {
          //console.log('Server response:', result);
        });
  }

  ngOnDestroy() {

  }

  ngAfterViewChecked(): void {
    this.scrollToBottom();
  }

  private scrollToBottom(): void {
    try {
      this.messagesContainer.nativeElement.scrollTop = this.messagesContainer.nativeElement.scrollHeight;
    } catch (err) {
      console.error('Scroll error:', err);
    }
  }

}
