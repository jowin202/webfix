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


export enum UserStatus {
    OFFLINE = 0,
    ONLINE = 1,
    BUSY   = 2
};

export interface User {
  id: number;
  username: string;
  username_html?: string;
  status: UserStatus;
}

export interface ChatThread {
  id: string; // Eindeutige ID (z.B. 'channel-1' oder 'user-5')
  type: 'channel' | 'private';
  name: string;
  messages: Message[];
}