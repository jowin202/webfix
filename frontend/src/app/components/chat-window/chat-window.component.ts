import { CommonModule } from '@angular/common';
import { Component, ElementRef, OnDestroy, OnInit, ViewChild } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';
import { Observable } from 'rxjs';
import { AuthService } from '../../services/auth.service';
import { UserMenuComponent } from "../user-menu/user-menu.component";


interface ChatMessage {
  cat: string;
  username: string;
  message: string;
}

interface OnlineUsers {
  username: string;
  username_html: string;
}

interface Channels {
  id: number;
  name: string;
}


@Component({
  selector: 'app-chat-window',
  imports: [CommonModule, FormsModule, UserMenuComponent],
  templateUrl: './chat-window.component.html',
  styleUrl: './chat-window.component.scss'
})
export class ChatWindowComponent implements OnInit, OnDestroy {
  constructor(public api: ApiService, public auth: AuthService) { }

  @ViewChild('messagesContainer') private messagesContainer!: ElementRef;

  channels: Channels[] = [];
  onlineUsers: OnlineUsers[] = [];
  messages: ChatMessage[] = [];

  showMenu: Boolean = false;

  ngOnInit() {
    this.connect_websocket();
    this.update_online_list();
    this.update_channel_list();
  }


  connect_websocket() {
    this.api.connect_stream("/ws2", this.auth.token).subscribe(result => {
      if ("username" in result && "message" in result) {
        result['cat'] = "default"
        this.messages.push(result);
      }
      else if ("cat" in result && result['cat'] == "statusmsg" && "msg" in result) {
        this.messages.push({ cat: "statusmsg", username: "ChatBot", "message": "<i>" + result['msg'] + "</i>" })
      }
      //whisper
      else if ("cat" in result && result['cat'] == "whisper" && "username" in result && "msg" in result) {
        this.messages.push({ cat: "whisper", username: result['username'], "message": result['msg'] });
      }
      // login and logout message from db
      else if ("cat" in result && result['cat'] == "userlogin" && "username" in result && "msg" in result) {
        this.messages.push({ cat: "statusmsg", username: "ChatBot", "message": result['username'] + " " + result['msg'] })
        this.update_online_list();
      }
      else if ("cat" in result && result['cat'] == "userlogout" && "username" in result && "msg" in result) {
        this.messages.push({ cat: "statusmsg", username: "ChatBot", "message": result['username'] + " " + result['msg'] })
        this.update_online_list();
      }
      // channel switch (TODO)
      else if ("cat" in result && result['cat'] == "userleft" && "username" in result) {
        this.messages.push({ cat: "statusmsg", username: "ChatBot", "message": "<i>" + result['username'] + " left the channel</i>" })
        this.update_online_list();
      }
      else if ("cat" in result && result['cat'] == "userenters" && "username" in result) {
        this.messages.push({ cat: "statusmsg", username: "ChatBot", "message": "<i>" + result['username'] + " enters the channel</i>" })
        this.update_online_list();
      }
      // announcement
      else if ("cat" in result && result['cat'] == "announcement" && "msg" in result) {
        this.messages.push({ cat: "announcement", username: "", "message": "<i>" + result['msg'] + "</i>" })
      }
      else if ("error_code" in result) {
        this.messages.push({ cat: "statusmsg", username: "ChatBot", message: result['error_string'] })
        //this.connect_websocket()
      }
    }
    );
  }

  update_online_list() {
    this.api.get("/api/data/online/", this.auth.token)
      .subscribe(result => {
        if (!("error_code" in result)) {
          this.onlineUsers = result
        }
      });
  }



  update_channel_list() {
    this.api.get("/api/data/channels/", this.auth.token)
      .subscribe(result => {
        if (!("error_code" in result)) {
          this.channels = result
        }
      });
  }
  switchChannel(data: any) {
    this.api.post("/api/input/goto/" + data + "/", this.auth.token, {})
      .subscribe(result => {
        console.log(result);
      });
  }


  sendMessage(message: string) {
    if (message == "") {
      return;
    }
    else if (message == "/exit") {
      this.auth.do_logout();
      return;
    }
    else if (message == "/clear") {
      this.messages = []
      return;
    }

    this.api.post(`/api/input/`, this.auth.token, { "message": message })
      .subscribe(result => {
        //console.log('Server response:', result);
      });
  }


  @ViewChild('inputField') inputField!: ElementRef<HTMLInputElement>;
  addName(name: string) {
    this.inputField.nativeElement.value += name;
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
