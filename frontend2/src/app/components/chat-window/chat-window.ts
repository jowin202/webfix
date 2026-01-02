import { Component, ElementRef, computed, signal, ViewChild, WritableSignal } from '@angular/core';
import { MatSidenav, MatSidenavModule } from '@angular/material/sidenav';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
// Import der neuen Komponenten
import { ChatSidebar } from '../chat-sidebar/chat-sidebar';
import { ChatTabs } from '../chat-tabs/chat-tabs';
import { ChatMessageStream } from '../chat-message-stream/chat-message-stream';
import { ChatInput } from '../chat-input/chat-input';
// Import der Interfaces
import { Message, Channel, User, ChatThread } from '../../models';
import { AuthService } from '../../services/auth.service';
import { ApiService } from '../../services/api.service';
import { StreamService } from '../../services/stream.service';
import { UserMenu } from "../user-menu/user-menu";

// ------------------

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    MatSidenavModule,
    MatToolbarModule,
    MatIconModule,
    MatButtonModule,
    ChatSidebar,
    ChatTabs,
    ChatMessageStream,
    ChatInput,
    UserMenu
],
  templateUrl: './chat-window.html',
  styleUrl: './chat-window.scss'
})
export class ChatWindow {

  @ViewChild('rightSidenav') rightSidenav!: MatSidenav;
  @ViewChild('messageContainer') messageContainer!: ElementRef; // Behält Scroll-Kontrolle

  currentThread: WritableSignal<ChatThread | null> = signal(null);
  currentMessage: string = '';

  activeSidebarTab: WritableSignal<'channels' | 'users'> = signal('channels');

  activeThreads: WritableSignal<ChatThread[]> = signal([]);

  currentTabIndex = computed(() => {
    const current = this.currentThread();
    if (!current) {
      return -1;
    }
    return this.activeThreads().findIndex(t => t.id === current.id);
  });

  
  channels: WritableSignal<Channel[]> = signal([  ]);
  get_channels() {
    this.api.get("/api/data/channels/", this.auth.token())
      .subscribe(result => {
        if (!("error_code" in result)) {
          this.channels.set(result);
        }
      });
  }
  

  users: WritableSignal<User[]> = signal([]);
  get_online_users() {
    this.api.get("/api/data/users/", this.auth.token())
      .subscribe(result => {
        if (!("error_code" in result)) {
          this.users.set(result);
        }
      });
  }


  initialMessages: Message[] = [
    { id: 1, user: 'System', text: 'Willkommen im #DevTeam Channel. Bitte beachte die Code-Konventionen.', time: '10:00' },
    { id: 2, user: 'Anna', text: 'Guten Morgen! Ich habe einen PR für das neue Zoneless-Feature eröffnet. Könntet ihr es bitte reviewen?', time: '10:05' },
    { id: 3, user: 'Ben', text: 'Mache ich gleich. Musstest du die Performance-Hooks verwenden, um das DOM zu aktualisieren?', time: '10:07' },
    { id: 4, user: 'Anna', text: 'Ja, ich verwende `injector.runInContext` für alle asynchronen Aktionen außerhalb von Material-Events.', time: '10:09' },
    { id: 5, user: 'Chris', text: 'Super, das ist der richtige Weg für zoneless. Ich habe die neuen Material Icons für die Einstellungen hinzugefügt.', time: '10:15' },
    { id: 6, user: 'Doris', text: 'Ich brauche die aktuellste API-URL für das Deployment, hat jemand die Dokumentation griffbereit?', time: '10:20' },
    { id: 7, user: 'Anna', text: 'Hier ist der Link: [API-Doku]', time: '10:21' },
    { id: 8, user: 'System', text: 'Chris ist dem Channel beigetreten.', time: '10:30' },
  ];

  private nextUserId = 31;

  constructor(public stream: StreamService, public api: ApiService, public auth: AuthService) {
    const generalThread: ChatThread = {
      id: 'channel-1',
      type: 'channel',
      name: '#general',
      messages: this.initialMessages
    };
    this.activeThreads.set([generalThread]);
    this.currentThread.set(generalThread);

    this.get_online_users();
    this.get_channels();

    this.stream.connect();
  }

  // --- METHODEN (Die State-Änderungslogik bleibt hier) ---

  setActiveTab(tab: 'channels' | 'users'): void {
    this.activeSidebarTab.set(tab);
  }

  openSettings(): void {
    this.rightSidenav.toggle();
  }

  private scrollToBottom(): void {
    if (this.messageContainer) {
      const element = this.messageContainer.nativeElement;
      element.scrollTop = element.scrollHeight;
    }
  }

  // Wird von ChatInputComponent aufgerufen
  handleSendMessage(): void {
    const current = this.currentThread();
    if (this.currentMessage.trim() && current) {
      const newMessage: Message = {
        id: current.messages.length + 1,
        user: 'Ich',
        text: this.currentMessage.trim(),
        time: new Date().toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' })
      };

      this.activeThreads.update(threads => {
        const threadIndex = threads.findIndex(t => t.id === current.id);
        if (threadIndex !== -1) {
          threads[threadIndex].messages = [...threads[threadIndex].messages, newMessage];
        }
        return [...threads];
      });
      this.currentMessage = ''; // Reset input

      setTimeout(() => {
        this.scrollToBottom();
      }, 0);
    }
  }

  // Wird von ChatTabsComponent und ChatSidebarComponent aufgerufen
  selectThread(thread: ChatThread): void {
    const existingThread = this.activeThreads().find(t => t.id === thread.id);

    if (!existingThread) {
      this.activeThreads.update(threads => [...threads, thread]);
      this.currentThread.set(thread);
    } else {
      this.currentThread.set(existingThread);
    }
    setTimeout(() => this.scrollToBottom(), 0); 
  }

  selectChannel(channel: Channel): void {
    const channelThread: ChatThread = {
      id: `channel-${channel.id}`,
      type: 'channel',
      name: channel.name,
      messages: (channel.id === 1) ? this.initialMessages : [
        { id: 1, user: 'System', text: `Willkommen im ${channel.name} Channel.`, time: '10:00' }
      ]
    };
    this.selectThread(channelThread);
  }

  openPrivateChat(user: User): void { 
    const privateThread: ChatThread = {
      id: `user-${user.id}`,
      type: 'private',
      name: user.username,
      messages: [
        { id: 1, user: 'System', text: `Privater Chat mit ${user.username} gestartet.`, time: '10:00' }
      ]
    };
    this.selectThread(privateThread);
  }

  // Wird von ChatTabsComponent aufgerufen
  closeThread(data: { thread: ChatThread, event: Event }): void {
    // Event-Propagation wurde bereits in der Unterkomponente gestoppt, aber zur Sicherheit hier nochmal
    data.event.stopPropagation(); 

    this.activeThreads.update(threads => threads.filter(t => t.id !== data.thread.id));

    if (this.currentThread()?.id === data.thread.id) {
      const remainingThreads = this.activeThreads();
      this.currentThread.set(remainingThreads.length > 0 ? remainingThreads[0] : null); 
    }
  }


  /*
  addChatter(): void {
    const newUser: User = {
      id: this.nextUserId++,
      username: `Neuer Chatter ${this.nextUserId}`
    };
    this.users.update(currentUsers => [...currentUsers, newUser]);
    
    const generalThread = this.activeThreads().find(t => t.id === 'channel-1');
    if(generalThread) {
         generalThread.messages = [...generalThread.messages, {
            id: generalThread.messages.length + 1,
            user: 'System',
            text: `${newUser.name} ist dem Channel beigetreten.`,
            time: new Date().toLocaleTimeString('de-DE')
        }];
        this.activeThreads.update(threads => [...threads]);
    }
  }
*/
}