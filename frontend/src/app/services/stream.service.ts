import { Injectable, Output, signal } from '@angular/core';
import { ApiService } from './api.service';
import { AuthService } from './auth.service';
import { EventEmitter } from 'stream';



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



  connect_websocket() {
    this.api.connect_stream("/ws2", this.auth.token).subscribe(result => {


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
        });
      }

      // user channel switch 
      else if ("cat" in result && (result.cat === "userleft" || result.cat === "userenters") && "username" in result) {
        this.messages.push({
          cat: "statusmsg",
          message: result.cat === "userleft" ? `${this.html_users[result.username] || result.username} left the channel` : `${this.html_users[result.username] || result.username} joined the channel`,
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

