import { Injectable, Output } from '@angular/core';
import { ApiService } from './api.service';
import { AuthService } from './auth.service';
import { EventEmitter } from 'stream';


export type PublicMessageCategory =
  | "default"
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
  to: string; 
  message: string;
  timestamp?: Date;
}

export interface PrivateMessagesByUser {
  [username: string]: PrivateMessage[];
}



@Injectable({
  providedIn: 'root'
})
export class StreamService {

  constructor(public api : ApiService, public auth : AuthService) { }


  messages: PublicMessage[] = [];
  privateMessages: PrivateMessagesByUser = {};

  
  connect_websocket() {
    this.api.connect_stream("/ws2", this.auth.token).subscribe(result => {
      
      if ("username" in result && "message" in result && !("toUser" in result)) {
        this.messages.push({
          cat: "default",
          username: result.username,
          message: result.message,
        });
      }
      
      else if ("cat" in result && result.cat === "privatemsg" && "username" in result && "msg" in result && "toUser" in result) {
        const from = result.username;
        const to = result.toUser;
        const msg: PrivateMessage = {
          from,
          to,
          message: result.msg,
          timestamp: new Date(),
        };

        // Zielbenutzer ermitteln (damit beide Seiten den Chat sehen)
        const chatKey = from === this.auth.username ? to : from;

        if (!this.privateMessages[chatKey]) {
          this.privateMessages[chatKey] = [];
        }
        this.privateMessages[chatKey].push(msg);
      }

      // statusmsg
      else if ("cat" in result && result.cat === "statusmsg" && "msg" in result) {
        this.messages.push({
          cat: "statusmsg",
          username: "ChatBot",
          message: `<i>${result.msg}</i>`,
        });
      }

      // user channel switch 
      else if ("cat" in result && (result.cat === "userleft" || result.cat === "userenters") && "username" in result) {
        this.messages.push({
          cat: "statusmsg",
          username: "ChatBot",
          message: result.cat === "userleft" ? `<i>${result.username} left the channel</i>` : `<i>${result.username} joined the channel</i>`,
        });
      }


      // user login / logout
      else if ("cat" in result && (result.cat === "userlogin" || result.cat === "userlogout") && "username" in result && "msg" in result) {
        this.messages.push({
          cat: "statusmsg",
          username: "ChatBot",
          message: `<i>${result.username} ${result.msg}</i>`,
        });
      }


      // announcements 
      else if ("cat" in result && result.cat === "announcement" && "msg" in result) {
        this.messages.push({
          cat: "announcement",
          message: `<i>${result.msg}</i>`,
        });
      }



        console.log(result);


      // ... (weitere Fälle wie in deinem Originalcode)
    });
  }


}

