import { Component, ElementRef, computed, effect, signal, ViewChild, WritableSignal } from '@angular/core';
import { MatSidenav, MatSidenavModule } from '@angular/material/sidenav';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { ChatSidebar } from '../chat-sidebar/chat-sidebar';
import { ChatTabs } from '../chat-tabs/chat-tabs';
import { ChatMessageStream } from '../chat-message-stream/chat-message-stream';
import { ChatInput } from '../chat-input/chat-input';
import { Message, Channel, User, ChatThread } from '../../models';
import { AuthService } from '../../services/auth.service';
import { ApiService } from '../../services/api.service';
import { StreamService } from '../../services/stream.service';
import { UserMenu } from "../user-menu/user-menu";
import { PublicMessage } from '../../services/models';


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
  @ViewChild('messageContainer') messageContainer!: ElementRef;

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

  channels: WritableSignal<Channel[]> = signal([
    { id: 1, name: 'Main Channel', always_available: true, is_member: true }
  ]);
  get_channels() {
    this.api.get("/api/channels/list/", this.auth.token())
      .subscribe(result => {
        if (this.hasApiError(result)) return;
        this.channels.set(result);
      });
  }
  

  users: WritableSignal<User[]> = signal([]);
  get_online_users() {
    this.api.get("/api/data/users/", this.auth.token())
      .subscribe(result => {
        if (this.hasApiError(result)) return;
        this.users.set(result);
        this.stream.addUsernames(result);
      });
  }

  private processedStreamMessages = 0;
  private subscribedChannelIds = new Set<number>();
  private initialized = false;

  constructor(public stream: StreamService, public api: ApiService, public auth: AuthService) {
    const generalThread: ChatThread = {
      id: 'channel-1',
      type: 'channel',
      name: 'Main Channel',
      messages: []
    };
    this.activeThreads.set([generalThread]);
    this.currentThread.set(generalThread);

    effect(() => {
      if (this.initialized) return;
      if (!this.auth.ready() || !this.auth.logged_in() || !this.auth.token()) return;
      this.initialized = true;

      this.get_online_users();
      this.get_channels();
      this.stream.connect();
      this.subscribeToChannel(1);
    });

    effect(() => {
      this.stream.userChanged();
      this.get_online_users();
    });

    effect(() => {
      this.stream.channelChanged();
      this.get_channels();
    });

    effect(() => {
      const messages = this.stream.messages();
      let newMessages = 0;
      for (let i = this.processedStreamMessages; i < messages.length; i++) {
        this.consumeStreamMessage(messages[i]);
        newMessages++;
      }
      this.processedStreamMessages = messages.length;
      if (newMessages > 0) {
        setTimeout(() => this.scrollToBottom(), 0);
      }
    });
  }

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

  private formatTime(): string {
    return new Date().toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' });
  }

  private channelThreadId(channelId: number): string {
    return `channel-${channelId}`;
  }

  private privateThreadId(username: string): string {
    return `user-${username.toLowerCase()}`;
  }

  private channelName(channelId: number): string {
    const channel = this.channels().find(c => c.id === channelId);
    return channel?.name ?? `Channel ${channelId}`;
  }

  private getChannelIdFromThreadId(threadId: string): number | null {
    if (!threadId.startsWith('channel-')) return null;
    const id = Number(threadId.slice('channel-'.length));
    return Number.isFinite(id) ? id : null;
  }

  private hasApiError(result: any): boolean {
    if (!result) return true;
    if (Array.isArray(result) && result.length > 0 && result[0] && typeof result[0] === 'object' && "error_code" in result[0]) return true;
    if (typeof result !== 'object') return true;
    return "error_code" in result;
  }

  private apiErrorCode(result: any): number | null {
    if (!result) return null;
    if (Array.isArray(result) && result.length > 0 && result[0] && typeof result[0] === 'object' && "error_code" in result[0]) {
      return Number(result[0].error_code);
    }
    if (typeof result !== 'object') return null;
    if ("error_code" in result) return Number(result.error_code);
    return null;
  }

  private subscribeToChannel(channelId: number) {
    if (this.subscribedChannelIds.has(channelId)) return;
    this.subscribedChannelIds.add(channelId);
    this.stream.subscribeChannel(channelId);
  }

  private unsubscribeFromChannel(channelId: number) {
    if (!this.subscribedChannelIds.has(channelId)) return;
    this.subscribedChannelIds.delete(channelId);
    this.stream.unsubscribeChannel(channelId);
  }

  private appendMessageToThread(threadId: string, createThread: () => ChatThread, user: string, text: string) {
    const currentId = this.currentThread()?.id;
    let updatedThreadRef: ChatThread | null = null;

    this.activeThreads.update(threads => {
      const index = threads.findIndex(t => t.id === threadId);

      if (index === -1) {
        const newThread = createThread();
        const msg: Message = { id: 1, user, text, time: this.formatTime() };
        updatedThreadRef = { ...newThread, messages: [...newThread.messages, msg] };
        return [...threads, updatedThreadRef];
      }

      const thread = threads[index];
      const msg: Message = {
        id: thread.messages.length + 1,
        user,
        text,
        time: this.formatTime(),
      };
      updatedThreadRef = { ...thread, messages: [...thread.messages, msg] };
      const copy = [...threads];
      copy[index] = updatedThreadRef;
      return copy;
    });

    if (currentId === threadId && updatedThreadRef) {
      this.currentThread.set(updatedThreadRef);
    }
  }

  private consumeStreamMessage(message: PublicMessage) {
    if (message.cat === 'default') {
      const channelId = Number(message.channel ?? 1);
      const threadId = this.channelThreadId(channelId);
      this.appendMessageToThread(
        threadId,
        () => ({
          id: threadId,
          type: 'channel',
          name: this.channelName(channelId),
          messages: []
        }),
        message.username ?? 'Unknown',
        message.message
      );
      return;
    }

    if (message.cat === 'private') {
      const targetUser = message.username ?? 'Unknown';
      const threadId = this.privateThreadId(targetUser);
      this.appendMessageToThread(
        threadId,
        () => ({
          id: threadId,
          type: 'private',
          name: targetUser,
          messages: []
        }),
        targetUser,
        message.message
      );
      return;
    }

    if (message.cat === 'statusmsg' || message.cat === 'announcement') {
      const active = this.currentThread();
      const fallbackChannelId = active?.type === 'channel'
        ? (this.getChannelIdFromThreadId(active.id) ?? 1)
        : 1;
      const channelId = Number(message.channel ?? fallbackChannelId);
      const threadId = this.channelThreadId(channelId);
      this.appendMessageToThread(
        threadId,
        () => ({
          id: threadId,
          type: 'channel',
          name: this.channelName(channelId),
          messages: []
        }),
        'System',
        message.message
      );
    }
  }

  handleSendMessage(): void {
    const text = this.currentMessage.trim();
    const current = this.currentThread();
    if (!text || !current) return;

    if (current.type === 'channel') {
      const channelId = this.getChannelIdFromThreadId(current.id) ?? 1;
      this.api.post('/api/input/', this.auth.token(), { message: text, channel_id: channelId })
        .subscribe();
    } else {
      this.api.post(
        `/api/input/wh?to_username=${encodeURIComponent(current.name)}&message=${encodeURIComponent(text)}`,
        this.auth.token(),
        {}
      ).subscribe();

      this.appendMessageToThread(
        current.id,
        () => current,
        'Ich',
        text
      );
    }

    this.currentMessage = '';
    setTimeout(() => this.scrollToBottom(), 0);
  }

  selectThread(thread: ChatThread): void {
    const existingThread = this.activeThreads().find(t => t.id === thread.id);

    if (!existingThread) {
      this.activeThreads.update(threads => [...threads, thread]);
      this.currentThread.set(thread);
    } else {
      this.currentThread.set(existingThread);
    }
    if (thread.type === 'channel') {
      const channelId = this.getChannelIdFromThreadId(thread.id);
      if (channelId) this.subscribeToChannel(channelId);
    }
    setTimeout(() => this.scrollToBottom(), 0);
  }

  selectChannel(channel: Channel): void {
    if (!channel.is_member && !channel.always_available) {
      let password = '';
      if (channel.has_password) {
        const entered = window.prompt(`Passwort für ${channel.name}:`);
        if (entered === null) return;
        password = entered;
      }
      this.api.post(`/api/channels/join/${channel.id}/`, this.auth.token(), { password })
        .subscribe(result => {
          if (this.hasApiError(result)) return;
          this.get_channels();
          this.selectChannel({ ...channel, is_member: true });
        });
      return;
    }

    const channelThread: ChatThread = {
      id: this.channelThreadId(channel.id),
      type: 'channel',
      name: channel.name,
      messages: []
    };
    this.subscribeToChannel(channel.id);
    this.selectThread(channelThread);
  }

  createChannel(data: { name: string; password?: string; invite_only: boolean }) {
    const params = new URLSearchParams({
      name: data.name,
      password: data.password ?? '',
      invite_only: String(data.invite_only),
    });

    this.api.post(`/api/channels/create_channel/?${params.toString()}`, this.auth.token(), null)
      .subscribe(result => {
        const errorCode = this.apiErrorCode(result);
        if (errorCode !== null) {
          if (errorCode === 409) {
            this.api.get("/api/channels/list/", this.auth.token()).subscribe(channels => {
              if (!Array.isArray(channels)) return;
              this.channels.set(channels);
              const existing = channels.find((channel: Channel) =>
                channel.name.trim().toLowerCase() === data.name.trim().toLowerCase()
              );
              if (existing) this.selectChannel(existing);
            });
          }
          return;
        }

        const channelId = Number(result.channel_id);
        this.get_channels();
        if (channelId) {
          this.selectChannel({
            id: channelId,
            name: data.name,
            is_member: true,
            has_password: !!data.password,
            invite_only: data.invite_only
          });
        }
      });
  }

  inviteUser(data: { channel_id: number; username: string }) {
    this.api.post('/api/channels/invite/', this.auth.token(), data)
      .subscribe(_ => this.get_channels());
  }

  openPrivateChat(user: User): void {
    const privateThread: ChatThread = {
      id: this.privateThreadId(user.username),
      type: 'private',
      name: user.username,
      messages: []
    };
    this.selectThread(privateThread);
  }

  closeThread(data: { thread: ChatThread, event: Event }): void {
    data.event.stopPropagation();

    this.activeThreads.update(threads => threads.filter(t => t.id !== data.thread.id));

    if (data.thread.type === 'channel') {
      const channelId = this.getChannelIdFromThreadId(data.thread.id);
      if (channelId) this.unsubscribeFromChannel(channelId);
    }

    if (this.currentThread()?.id === data.thread.id) {
      const remainingThreads = this.activeThreads();
      this.currentThread.set(remainingThreads.length > 0 ? remainingThreads[0] : null);
    }
  }
}
