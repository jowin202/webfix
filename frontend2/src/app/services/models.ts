
export type PublicMessageCategory =
  | 'default'
  | 'private'        // Hinweis: öffentlich angezeigt, aber privat entstanden
  | 'statusmsg'
  | 'whisper'
  | 'userlogin'
  | 'userlogout'
  | 'userleft'
  | 'userenters'
  | 'announcement';

export interface PublicMessage {
  cat: PublicMessageCategory;
  message: string;
  username?: string;   // optional, z. B. statusmsg
  timestamp?: number;  // besser number statt Date (serialisierbar)
}


export interface PrivateMessage {
  from: string;
  message: string;
  timestamp: number;
}

export type PrivateMessagesByUser = Record<
  string,            // username
  readonly PrivateMessage[]
>;

