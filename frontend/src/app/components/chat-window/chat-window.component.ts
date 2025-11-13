import { Component, ElementRef, OnDestroy, OnInit, ViewChild, effect } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';
import { AuthService } from '../../services/auth.service';
import { UserMenuComponent } from "../user-menu/user-menu.component";
import { AdminMenuComponent } from '../admin-menu/admin-menu.component';
import { StreamService } from '../../services/stream.service';
import { StreamComponent } from "../stream/stream.component";


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
  imports: [FormsModule, UserMenuComponent, AdminMenuComponent, StreamComponent],
  templateUrl: './chat-window.component.html',
  styleUrl: './chat-window.component.scss'
})
export class ChatWindowComponent implements OnInit, OnDestroy {
  constructor(public api: ApiService, public auth: AuthService, public stream: StreamService) {
    effect(() => {
      this.stream.user_changed_signal(); //trigger system
      this.update_online_list();
    });
  }


  channels: Channels[] = [];
  onlineUsers: OnlineUsers[] = [];
  messages: ChatMessage[] = [];

  showMenu: Boolean = false;
  showAdminMenu: Boolean = false;

  ngOnInit() {
    this.stream.connect_websocket();
    this.update_online_list();
    this.update_channel_list();
  }



  update_online_list() {
    this.api.get("/api/data/online/", this.auth.token)
      .subscribe(result => {
        if (!("error_code" in result)) {
          this.onlineUsers = result
          this.stream.add_usernames(result);
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
        //do nothing, update user list is in constructor (stream service)
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
    if (this.inputField?.nativeElement) {
      this.inputField.nativeElement.value += name;
      this.inputField.nativeElement.focus();
    }
  }

  ngOnDestroy() {

  }

  ngAfterViewChecked(): void {
    this.scrollToBottom();
  }


  @ViewChild('messagesContainer') private messagesContainer!: ElementRef;
  private scrollToBottom(): void {
    const container = this.messagesContainer?.nativeElement;
    if (container) {
      try {
        this.messagesContainer.nativeElement.scrollTop = this.messagesContainer.nativeElement.scrollHeight;
      } catch (err) {
        console.error('Scroll error:', err);
      }
    }
  }
}
