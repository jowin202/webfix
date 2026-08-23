import { Injectable, signal } from '@angular/core';
import { Subscription } from 'rxjs';
import { ApiService } from './api.service';
import { AuthService } from './auth.service';



export type PublicMessageCategory =
  | "default"
  | "private"
  | "statusmsg"
  | "whisper"
  | "userlogin"
  | "userlogout"
  | "userleft"
  | "userenters"
  | "announcement";


export interface PublicMessage {
  cat: PublicMessageCategory;
  username?: string;
  message: string;
  timestamp?: Date;
  channel?: number;
}

export interface PrivateMessage {
  from: string;
  message: string;
  timestamp?: Date;
}

export interface PrivateMessagesByUser {
  [username: string]: PrivateMessage[];
}

const privateMessages: PrivateMessagesByUser = {};

function addMessage(
  message: PrivateMessage
) {
  if (!privateMessages[message.from]) {
    privateMessages[message.from] = []; // Falls keine Liste existiert, anlegen
  }
  privateMessages[message.from].push(message); // Nachricht hinzufügen
}

function getMessages(username: string): PrivateMessage[] {
  return privateMessages[username] || [];
}



@Injectable({
  providedIn: 'root'
})
export class StreamService {

  constructor(public api: ApiService, public auth: AuthService) { }

  user_changed_signal = signal(0);

  messages: PublicMessage[] = [];
  privateMessages: PrivateMessagesByUser = {};


  html_users: Record<string, string> = {};
  add_usernames(entries: { username: string, username_html: string }[]) {
    for (const e of entries) {
      this.html_users[e.username] = e.username_html;
    }
  }



  private streamSubscription: Subscription | null = null;
  private send: ((message: string) => void) | null = null;

  // Opens a fresh connection bound to one channel. The backend never
  // multiplexes channels onto a connection, so switching channels means
  // tearing down the old connection and opening a new one -- there is no
  // subscribe/unsubscribe protocol for the client to get wrong.
  connect_websocket(channelId?: number, announce: boolean = true, fromChannelId?: number) {
    const targetChannel = channelId ?? this.auth.channel_id;

    // Tell the old connection which channel we're switching to, so its
    // server-side disconnect announces "left the channel (to Y)" instead of
    // a separate, unrelated plain "left the channel" message.
    if (fromChannelId !== undefined) {
      this.send?.(JSON.stringify({ action: "switch_leave", to_channel_id: targetChannel }));
    }

    this.streamSubscription?.unsubscribe();
    this.send = null;

    const fromParam = fromChannelId !== undefined ? `&from_channel_id=${fromChannelId}` : '';
    const url = `/api/stream/ws?channel_id=${targetChannel}&announce=${announce ? 1 : 0}${fromParam}`;

    this.streamSubscription = this.api.connect_stream(url, this.auth.token, 5000, (send) => {
      this.send = send;
    }).subscribe(result => {


      if ("error_code" in result && result['error_code'] == -3) {
        this.messages.push({
          cat: "announcement",
          message: "<font color='red'>Stream closed, reconnect...</font>",
        });
      }

      if ("username" in result && "message" in result && !("toUser" in result)) {
        this.messages.push({
          cat: "default",
          username: this.html_users[result.username] || result.username,
          message: result.message,
          channel: Number(result.channel ?? this.auth.channel_id),
        });
      }

      else if ("cat" in result && result.cat === "whisper" && "username" in result && "msg" in result) {
        const from = result.username;
        const msg: PrivateMessage = {
          from,
          message: result.msg,
          timestamp: new Date(),
        };


        this.messages.push({
          cat: "private",
          username: result.username,
          message: result.msg,
        });


        addMessage(msg);
      }

      // statusmsg
      else if ("cat" in result && result.cat === "statusmsg" && "msg" in result) {
        this.messages.push({
          cat: "statusmsg",
          message: `${result.msg}`,
          channel: "channel" in result ? Number(result.channel) : undefined,
        });
      }

      // user channel switch
      else if ("cat" in result && (result.cat === "userleft" || result.cat === "userenters") && "username" in result) {
        const displayName = this.html_users[result.username] || result.username;
        const otherChannel = "other_channel_name" in result && result.other_channel_name ? result.other_channel_name : undefined;
        let text: string;
        if (result.cat === "userleft") {
          text = otherChannel ? `${displayName} left the channel (to ${otherChannel})` : `${displayName} left the channel`;
        } else {
          text = otherChannel ? `${displayName} joined the channel (from ${otherChannel})` : `${displayName} joined the channel`;
        }
        this.messages.push({
          cat: "statusmsg",
          message: text,
          channel: "channel" in result ? Number(result.channel) : undefined,
        });
        this.user_changed_signal.update(v => v + 1); //change online list
      }


      // user login / logout
      else if ("cat" in result && (result.cat === "userlogin" || result.cat === "userlogout") && "username" in result && "msg" in result) {
        this.messages.push({
          cat: "statusmsg",
          message: `${this.html_users[result.username] || result.username} ${result.msg}`,
        });
        this.user_changed_signal.update(v => v + 1); //change online list
      }


      // announcements 
      else if ("cat" in result && result.cat === "announcement" && "msg" in result) {
        this.messages.push({
          cat: "announcement",
          message: `${result.msg}`,
        });
      }



      //console.log(result);


      // ... (weitere Fälle wie in deinem Originalcode)
    });
  }


}
