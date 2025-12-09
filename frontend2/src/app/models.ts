// src/app/models.ts
export interface Message {
  id: number;
  user: string;
  text: string;
  time: string;
}

export interface Channel {
  id: number;
  name: string;
}

export interface User {
  id: number;
  name: string;
}

export interface ChatThread {
  id: string; // Eindeutige ID (z.B. 'channel-1' oder 'user-5')
  type: 'channel' | 'private';
  name: string;
  messages: Message[];
}