import { Component, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { ApiService } from '../../services/api.service';

// MATERIAL
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'app-forgot-password',
  standalone: true,
  imports: [
    FormsModule,
    RouterModule,

    // Material
    MatFormFieldModule,
    MatInputModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule
  ],
  templateUrl: './forgot-password-form.html',
  styleUrl: './forgot-password-form.scss'
})
export class ForgotPasswordForm {

  success = signal(false);
  error = signal(false);

  constructor(public api: ApiService) {}

  requestReset(data: any) {

    this.success.set(false);
    this.error.set(false);

    let requestSent = false;

    // Request via Mail
    if (data.username && data.mail) {
      requestSent = true;
      this.api.post('/api/pwmanage/lost_password_mail/', "", {
        username: data.username,
        mail: data.mail
      }).subscribe(res => this.success.set(true));
    }

    // Request via Fediverse
    if (data.username && data.fediverse_id) {
      requestSent = true;
      this.api.post('/api/pwmanage/lost_password_fediverse/', "", {
        username: data.username,
        fediverse_id: data.fediverse_id
      }).subscribe(res => this.success.set(true));
    }

    if (!requestSent) {
      this.error.set(true);
    }
  }
}
