import { Component, effect, inject, PLATFORM_ID, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { AuthService } from '../../services/auth.service';
import { ApiService } from '../../services/api.service';
import { WebAuthnService } from '../../services/webauthn.service';
import { Router, RouterModule } from '@angular/router';

// Material Imports
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatDividerModule } from '@angular/material/divider';
import { isPlatformBrowser } from '@angular/common';



export interface PublicInfos {
  online_names: string[];
  allow_guest_login: boolean;
  user_verification_mail: boolean;
  user_verification_fediverse: boolean;
  display_online: boolean;
  num_users: number;
  show_rooms: boolean;
  channels: string[];
}



@Component({
  selector: 'app-login-window',
  standalone: true,
  imports: [
    FormsModule,
    RouterModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatIconModule,
    MatDividerModule
  ],
  templateUrl: './login-form.html',
  styleUrl: './login-form.scss'
})
export class LoginForm {

  // Hier wird public_infos gespeichert – NICHT mehr in ApiService!
  public_infos = signal<PublicInfos | null>(null);

  private router = inject(Router);
  private platformId = inject(PLATFORM_ID);

  constructor(
    public auth: AuthService,
    public api: ApiService,
    public webauthn: WebAuthnService
  ) {
    this.load_public_infos();

    // AUTOMATISCHE WEITERLEITUNG NACH ERFOLGREICHEM LOGIN
    effect(() => {

      // SSR → NIE navigieren
      if (!isPlatformBrowser(this.platformId)) return;

      if (this.auth.ready() && this.auth.logged_in()) {
        this.router.navigateByUrl('/chat');
      }
    });
  }


// ------------------------------------------------------------
// PUBLIC INFOS LADEN (aus API)
// ------------------------------------------------------------
load_public_infos() {
  this.api.get("/api/register/public_infos/", "")
    .subscribe(result => {
      this.public_infos.set(result);
    });
}

  // ------------------------------------------------------------
  // Getter für Template
  // ------------------------------------------------------------
  get passwordError() { return this.auth.password_error; }
  get guestError() { return this.auth.guest_error; }

allowGuestLogin() {
  return this.public_infos()?.allow_guest_login ?? false;
}

numUsersOnline() {
  return this.public_infos()?.num_users ?? 0;
}

  // ------------------------------------------------------------
  // LOGIN
  // ------------------------------------------------------------
  async do_page_login(value: any) {
  if (!value.username) return;

  // FIDO2 Login
  if (value.password === "") {
    const result = await this.webauthn.login(value.username);
    if ("access_token" in result) {
      this.auth.do_login_from_token(result["access_token"]);
    }
    return;
  }

  // Normal Login
  this.auth.do_login(
    value.username,
    value.password ?? "",
    value.remember ?? false
  );
}

// ------------------------------------------------------------
// GUEST LOGIN
// ------------------------------------------------------------
do_guest_login(value: any) {
  if (!value.guestName) return;
  this.auth.do_guest_login(value.guestName, false);
}
}
