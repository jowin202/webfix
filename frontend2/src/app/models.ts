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
  always_available?: boolean;
  invite_only?: boolean;
  has_password?: boolean;
  is_owner?: boolean;
  is_member?: boolean;
  is_invited?: boolean;
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
