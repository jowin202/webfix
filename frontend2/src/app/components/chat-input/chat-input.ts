// src/app/chat-input/chat-input.component.ts
import { Component, input, output } from '@angular/core';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { FormsModule } from '@angular/forms';
import { CdkTextareaAutosize } from '@angular/cdk/text-field';

@Component({
  selector: 'app-chat-input',
  standalone: true,
  imports: [
    MatFormFieldModule, MatInputModule, MatIconModule, MatButtonModule, FormsModule, CdkTextareaAutosize
  ],
  templateUrl: './chat-input.html', // Korrigiert den Dateinamen auf .component.html
  styleUrl: './chat-input.scss'
})
export class ChatInput { // Name auf Konvention angepasst

  currentMessage = input.required<string>(); 
  currentMessageChange = output<string>();
  sendMessage = output<void>();

  /**
   * Wird ausgelöst, wenn sich der ngModel-Wert im Template ändert.
   * Emittiert den neuen Wert an die Parent-Komponente.
   */
  updateMessage(value: string): void {
      this.currentMessageChange.emit(value);
  }
  
  /**
   * Tastatureingabe für das Senden via Enter.
   * @param event Das KeyboardEvent.
   */
  onKeydown(event: KeyboardEvent): void {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      this.sendMessage.emit();
    }
  }
}