// src/app/chat-tabs/chat-tabs.component.ts
import { Component, Input, Output, EventEmitter } from '@angular/core';
import { MatTabsModule } from '@angular/material/tabs';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { ChatThread } from '../../models';

@Component({
  selector: 'app-chat-tabs',
  standalone: true,
  imports: [
    MatTabsModule, MatIconModule, MatButtonModule
  ],
  templateUrl: './chat-tabs.html',
  styleUrl: './chat-tabs.scss'
})
export class ChatTabs {
  @Input({ required: true }) activeThreads!: ChatThread[];
  @Input({ required: true }) currentTabIndex!: number; 

  @Output() selectThread = new EventEmitter<ChatThread>();
  @Output() closeThread = new EventEmitter<ChatThread>();

  // Übergibt das Thread-Objekt an den Parent
  onTabIndexChange(index: number): void {
    const thread = this.activeThreads[index];
    if (thread) {
      this.selectThread.emit(thread);
    }
  }

  onCloseThreadMouseDown(event: MouseEvent): void {
    event.preventDefault();
    event.stopPropagation();
    event.stopImmediatePropagation();
  }

  // Stoppt das Event, um den Tab-Wechsel zu verhindern und sendet den Thread zum Schließen
  onCloseThread(thread: ChatThread, event: MouseEvent): void {
    event.preventDefault();
    event.stopPropagation();
    event.stopImmediatePropagation();
    this.closeThread.emit(thread);
  }
}
