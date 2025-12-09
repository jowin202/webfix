// src/app/chat-message-stream/chat-message-stream.component.ts
import { Component, input } from '@angular/core';
import { ChatThread } from '../../models';

@Component({
  selector: 'app-chat-message-stream',
  standalone: true,
  imports: [],
  templateUrl: './chat-message-stream.html',
  styleUrl: './chat-message-stream.scss'
})
export class ChatMessageStream {
  currentThread = input<ChatThread | null>(null);
}