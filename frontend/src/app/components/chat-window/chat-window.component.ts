import { CommonModule } from '@angular/common';
import { Component, ElementRef, OnDestroy, OnInit, ViewChild } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';
import { Observable } from 'rxjs';
import { AuthService } from '../../services/auth.service';


interface ChatMessage {
  cat: string;
  username: string;
  message: string;
}

interface OnlineUsers {
  username: string;
  username_html: string;
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

  onlineUsers : OnlineUsers[] = []
  messages : ChatMessage[] = []

  ngOnInit() {
    this.api.connect_stream("/ws2", this.auth.token).subscribe(result => {
      if ("username" in result && "message" in result){
        result['cat'] = "default"
        this.messages.push(result);
      }
      else if ("cat" in result && result['cat'] == "statusmsg" && "msg" in result)
      {
        this.messages.push({cat: "statusmsg", username: "ChatBot", "message" : "<i>" + result['msg'] + "</i>"})
      }
      else if ("cat" in result && result['cat'] == "announcement" && "msg" in result)
      {
        this.messages.push({cat: "announcement", username: "", "message" : "<i>" + result['msg'] + "</i>"})
      }
    });

    this.update_online_list();
  }

  update_online_list()
  {
        this.api.get("/api/data/online_by_id/" + this.auth.channel_id + "/", this.auth.token)
        .subscribe(result => {
          this.onlineUsers = result
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
