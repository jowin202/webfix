import { Component, input, output, signal, computed, WritableSignal } from '@angular/core';
import { MatListModule } from '@angular/material/list';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatDividerModule } from '@angular/material/divider';
import { MatFormFieldModule } from '@angular/material/form-field'; 
import { MatInputModule } from '@angular/material/input';         
import { FormsModule } from '@angular/forms';                       

import { User, Channel } from '../../models';

interface ChatThread { id: string; type: 'channel' | 'private'; name: string; messages: any[]; } 

@Component({
  selector: 'app-chat-sidebar',
  standalone: true, // Hinzugefügt
  imports: [
    MatListModule, MatIconModule, MatButtonModule, MatDividerModule, 
    MatFormFieldModule, MatInputModule, FormsModule 
  ],
  templateUrl: './chat-sidebar.html',
  styleUrl: './chat-sidebar.scss',
})
export class ChatSidebar {
  
  // 📥 INKOMMENDE DATEN (Original, ungefiltert)
  channels = input.required<Channel[]>();
  users = input.required<User[]>();
  activeSidebarTab = input.required<'channels' | 'users'>();
  currentThread = input<ChatThread | null>(null); 

  // 🔎 INTERNER ZUSTAND: Der Suchbegriff wird in der Sidebar verwaltet
  searchTerm: WritableSignal<string> = signal('');

  // 🟢 COMPUTED: Filtert die Channels, wenn sich searchTerm ändert
  filteredChannels = computed(() => {
    const term = this.searchTerm().toLowerCase();
    const allChannels = this.channels(); // Nutzt den Input als Signal
    if (!term) {
        return allChannels;
    }
    return allChannels.filter(channel => 
        channel.name.toLowerCase().includes(term)
    );
  });

  // 🟢 COMPUTED: Filtert die User, wenn sich searchTerm ändert
  filteredUsers = computed(() => {
    const term = this.searchTerm().toLowerCase();
    const allUsers = this.users(); // Nutzt den Input als Signal
    if (!term) {
        return allUsers;
    }
    return allUsers.filter(user => 
        user.username.toLowerCase().includes(term)
    );
  });

  // 🟡 OUTPUTS (Unverändert)
  selectChannel = output<Channel>();
  openPrivateChat = output<User>();
  setActiveTab = output<'channels' | 'users'>();
  addChatter = output<void>();
  createChannel = output<{ name: string; password?: string; invite_only: boolean }>();

  newChannelName = '';
  newChannelPassword = '';
  newChannelInviteOnly = false;

  // --- METHODEN FÜR DIE SUCHE ---

  /**
   * Wird bei ngModelChange ausgelöst und setzt das interne Signal.
   */
  updateSearchTerm(value: string): void {
      this.searchTerm.set(value);
  }

  /**
   * Setzt das Suchsignal zurück.
   */
  clearSearch(): void {
      this.searchTerm.set('');
  }

  onCreateChannel() {
    const name = this.newChannelName.trim();
    if (!name) return;
    this.createChannel.emit({
      name,
      password: this.newChannelPassword.trim() || undefined,
      invite_only: this.newChannelInviteOnly
    });
    this.newChannelName = '';
    this.newChannelPassword = '';
    this.newChannelInviteOnly = false;
  }
}
