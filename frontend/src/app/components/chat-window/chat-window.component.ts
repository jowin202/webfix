import { CommonModule } from '@angular/common';
import { Component, OnDestroy, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { WebSocketSubject } from 'rxjs/webSocket';

@Component({
  selector: 'app-chat-window',
  imports: [CommonModule, FormsModule],
  templateUrl: './chat-window.component.html',
  styleUrl: './chat-window.component.scss'
})
export class ChatWindowComponent implements OnInit, OnDestroy{
  
  private socket$!: WebSocketSubject<any>;
  messages: { sender: string; text: string }[] = [];
  onlineUsers: string[] = [];
  currentMessage = '';

  ngOnInit() {
    this.socket$ = new WebSocketSubject('ws://localhost:3000');

    this.socket$.subscribe((msg) => {
      if (msg.type === 'message') {
        this.messages.push({ sender: msg.sender, text: msg.text });
      } else if (msg.type === 'userList') {
        this.onlineUsers = msg.users;
      }
    });
  }

  sendMessage() {
    if (this.currentMessage.trim()) {
      this.socket$.next({
        type: 'message',
        text: this.currentMessage
      });
      this.currentMessage = '';
    }
  }

  ngOnDestroy() {
    this.socket$.complete();
  }
}
