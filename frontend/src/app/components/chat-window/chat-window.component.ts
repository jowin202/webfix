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

interface UserStatus {
  username: string;
  username_html: string;
  status: number;
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
  allUsers: UserStatus[] = [];
  messages: ChatMessage[] = [];

  showMenu: Boolean = false;
  showAdminMenu: Boolean = false;

  ngOnInit() {
    if (!this.auth.channel_id || this.auth.channel_id < 1) {
      this.auth.channel_id = 1;
    }
    this.stream.connect_websocket();
    this.update_online_list();
    this.update_channel_list();
  }



  update_online_list() {
    const channelId = Number(this.auth.channel_id || 1);
    this.api.get("/api/data/users_by_channel_id/" + channelId + "/", this.auth.token)
      .subscribe(result => {
        if (!("error_code" in result)) {
          this.onlineUsers = result
          this.stream.add_usernames(result);
        }
      });
  }



  load_all_users() {
    this.api.get("/api/data/users/", this.auth.token)
      .subscribe(result => {
        if (!("error_code" in result)) {
          this.allUsers = result;
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
    const to_channel_id = Number(data || 1);
    const from_channel_id = this.auth.channel_id;
    if (to_channel_id === from_channel_id) {
      return;
    }

    // The old connection is told which channel we're heading to (so it can
    // announce "left the channel (to Y)"), and the new one is told where we
    // came from (so it can announce "joined the channel (from X)") -- one
    // message per side, no separate "switched" notice needed.
    this.auth.channel_id = to_channel_id;
    this.stream.connect_websocket(to_channel_id, false, from_channel_id);

    this.api.post(`/api/channels/switch/`, this.auth.token, { from_channel_id, to_channel_id })
      .subscribe();

    this.update_online_list();
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

    if (this.whisperTarget) {
      const params = new URLSearchParams({ to_username: this.whisperTarget, message }).toString();
      this.api.post(`/api/input/wh?${params}`, this.auth.token, {})
        .subscribe();
      this.whisperTarget = null;
      return;
    }

    this.api.post(`/api/input/`, this.auth.token, { "message": message, "channel_id": this.auth.channel_id })
      .subscribe(result => {
        //console.log('Server response:', result);
      });
  }


  @ViewChild('inputField') inputField!: ElementRef<HTMLInputElement>;

  whisperTarget: string | null = null;
  setWhisperTarget(name: string) {
    this.whisperTarget = name;
    this.inputField?.nativeElement?.focus();
  }
  clearWhisperTarget() {
    this.whisperTarget = null;
    this.inputField?.nativeElement?.focus();
  }

  showWhisperEntry: boolean = false;
  whisperSuggestions: UserStatus[] = [];
  whisperEntryError: string | null = null;

  @ViewChild('whisperNameField') whisperNameField?: ElementRef<HTMLInputElement>;
  @ViewChild('whisperEntryContainer') whisperEntryContainer?: ElementRef<HTMLDivElement>;

  toggleWhisperEntry() {
    this.showWhisperEntry = !this.showWhisperEntry;
    this.whisperSuggestions = [];
    this.whisperEntryError = null;
    if (this.showWhisperEntry) {
      this.load_all_users();
      // The [hidden] binding below only flips once Angular's own change
      // detection runs, which is too late for focus() -- browsers refuse to
      // focus an element that is still hidden at call time. Unhide the
      // container natively first, synchronously, in this same click handler.
      const container = this.whisperEntryContainer?.nativeElement;
      if (container) {
        container.hidden = false;
      }
      this.whisperNameField?.nativeElement?.focus();
    } else {
      this.inputField?.nativeElement?.focus();
    }
  }

  onWhisperInput(value: string) {
    this.whisperEntryError = null;
    const query = value.trim().toLowerCase();
    if (!query) {
      this.whisperSuggestions = [];
      return;
    }
    this.whisperSuggestions = this.allUsers
      .filter(user => user.username.toLowerCase().includes(query))
      .slice(0, 8);
  }

  selectWhisperSuggestion(user: UserStatus) {
    this.whisperToUsername(user.username);
  }

  // Only ever hands off to setWhisperTarget for a username that is actually
  // known to exist -- an unknown name is rejected here, before a whisper
  // target (and thus a doomed /wh request) is ever set.
  whisperToUsername(name: string) {
    const trimmed = name.trim();
    if (!trimmed) {
      this.showWhisperEntry = false;
      this.whisperSuggestions = [];
      this.whisperEntryError = null;
      return;
    }

    const match = this.allUsers.find(user => user.username.toLowerCase() === trimmed.toLowerCase());
    if (!match) {
      this.whisperEntryError = `User "${trimmed}" not found.`;
      this.whisperSuggestions = [];
      return;
    }

    this.setWhisperTarget(match.username);
    this.showWhisperEntry = false;
    this.whisperSuggestions = [];
    this.whisperEntryError = null;
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
