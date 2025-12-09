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
    ChatInput
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

  // --- MOCK DATEN ALS SIGNALS ---
  channels: WritableSignal<Channel[]> = signal([
    { id: 1, name: '#general' }, { id: 2, name: '#announcements' },
    { id: 3, name: '#dev-backend' }, { id: 4, name: '#dev-frontend-angular' },
    { id: 5, name: '#design-ui-ux' }, { id: 6, name: '#qa-testing' },
    { id: 7, name: '#helpdesk-support' }, { id: 8, name: '#product-management' },
    { id: 9, name: '#marketing-sales' }, { id: 10, name: '#finance-hr' },
    { id: 11, name: '#random-talk' }, { id: 12, name: '#berlin-office' },
    { id: 13, name: '#munich-office' }, { id: 14, name: '#cloud-infrastructure' },
    { id: 15, name: '#security-audit' }, { id: 16, name: '#onboarding-new' },
    { id: 17, name: '#data-science' }, { id: 18, name: '#mobile-apps' },
    { id: 19, name: '#api-integration' }, { id: 20, name: '#release-management' },
    { id: 21, name: '#tech-talk-tuesday' }, { id: 22, name: '#coffee-break-club' },
    { id: 23, name: '#feedback-corner' }, { id: 24, name: '#project-mercury' },
    { id: 25, name: '#project-venus' }, { id: 26, name: '#external-partners' },
    { id: 27, name: '#code-reviews' }, { id: 28, name: '#accessibility' },
    { id: 29, name: '#iot-experiments' }, { id: 30, name: '#open-source' },
  ]);

  users: WritableSignal<User[]> = signal([
    { id: 1, name: 'Alice Müller' }, { id: 2, name: 'Bob Schmidt' },
    { id: 3, name: 'Clara Weber' }, { id: 4, name: 'David Fischer' },
    { id: 5, name: 'Emilia Meyer' }, { id: 6, name: 'Felix Wagner' },
    { id: 7, name: 'Greta Becker' }, { id: 8, name: 'Hannes Schulz' },
    { id: 9, name: 'Ida Hoffmann' }, { id: 10, name: 'Jakob Schäfer' },
    { id: 11, name: 'Kim Koch' }, { id: 12, name: 'Leo Bauer' },
    { id: 13, name: 'Mia Richter' }, { id: 14, name: 'Nico Wolf' },
    { id: 15, name: 'Paula Neumann' }, { id: 16, name: 'Quentin Voss' },
    { id: 17, name: 'Romy Scholz' }, { id: 18, name: 'Simon König' },
    { id: 19, name: 'Tanja Lorenz' }, { id: 20, name: 'Ulf Schneider' },
    { id: 21, name: 'Vera Zimmermann' }, { id: 22, name: 'Walter Haas' },
    { id: 23, name: 'Xenia Lange' }, { id: 24, name: 'Yannik Keller' },
    { id: 25, name: 'Zoe Hartwig' }, { id: 26, name: 'Adrian Jung' },
    { id: 27, name: 'Bianca Schott' }, { id: 28, name: 'Chris Ebert' },
    { id: 29, name: 'Diana Seifert' }, { id: 30, name: 'Erik Brand' },
  ]);

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

  constructor() {
    const generalThread: ChatThread = {
      id: 'channel-1',
      type: 'channel',
      name: '#general',
      messages: this.initialMessages
    };
    this.activeThreads.set([generalThread]);
    this.currentThread.set(generalThread);
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
      name: user.name,
      messages: [
        { id: 1, user: 'System', text: `Privater Chat mit ${user.name} gestartet.`, time: '10:00' }
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

  addChatter(): void {
    const newUser: User = {
      id: this.nextUserId++,
      name: `Neuer Chatter ${this.nextUserId}`
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
}