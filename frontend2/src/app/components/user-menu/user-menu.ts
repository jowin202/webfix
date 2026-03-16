import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatTableModule } from '@angular/material/table';
import { MatIconModule } from '@angular/material/icon';
import { MatDividerModule } from '@angular/material/divider';
import { MatSelectModule } from '@angular/material/select';


import { Component, computed, input, output, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { AuthService } from '../../services/auth.service';
import { ApiService } from '../../services/api.service';
import { WebAuthnService } from '../../services/webauthn.service';
import { Channel, User } from '../../models';

@Component({
  selector: 'app-user-menu',
  imports: [
    FormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatCardModule,
    MatTableModule,
    MatIconModule,
    MatDividerModule,
    MatSelectModule],
  templateUrl: './user-menu.html',
  styleUrl: './user-menu.scss',
})
export class UserMenu {


  constructor(
    public auth: AuthService,
    public api: ApiService,
    public webauthn: WebAuthnService
  ) {}

  
  closeEvent = output<void>();
  channels = input<Channel[]>([]);
  users = input<User[]>([]);

  inviteChannelId: number | null = null;
  inviteUsername = '';
  inviteSuccess = signal(false);
  inviteError = signal('');

  ownedChannels = computed(() => this.channels().filter(channel => !!channel.is_owner));
  invitableUsers = computed(() =>
    this.users().filter(user => user.username.toLowerCase() !== this.auth.username().toLowerCase())
  );



  /** ================= USER INFO ================= */
  userinfo: any = {};

  change_pw_status = signal<boolean>(false);
  error_at_html_user = signal<boolean>(false);


  /** ================= COLOR GRADIENT ================= */
  color_gradient_error = signal<boolean|null> (null);

  /** ================= FIDO2 ================= */
  fido_status_successfull = signal<boolean>(false);
  double_register_error = signal<boolean>(false);
  no_challenge_error = signal<boolean>(false);
  wrong_password_error = signal<boolean>(false);

  fido_credentials = signal< {
    id: number;
    name: string;
    created_at: string;
    last_used_at: Date;
    sign_count: number;
  }[]>([]);

  displayedColumns = ['name', 'sign_count', 'last_used', 'actions'];

  /** ================= LIFECYCLE ================= */
  ngOnInit(): void {
    this.loadUserInfo();
    this.fido_credentials_reload();
  }

  /** ================= LOADERS ================= */
  loadUserInfo() {
    this.api.get('/api/data/get_user_info/', this.auth.token())
      .subscribe(result => {
        this.userinfo = result;
      });
  }

  fido_credentials_reload() {
    this.api.get('/api/fido2/credentials/', this.auth.token())
      .subscribe(result => {
        this.fido_credentials.set(result);
      });
  }

  /** ================= FORMATTERS ================= */
  formatTime(timestamp: any): string {
    return new Date(timestamp).toLocaleString();
  }

  formatSeconds(secondsInput: number): string {
    const units = [
      { label: 'year', value: 365 * 24 * 60 * 60 },
      { label: 'week', value: 7 * 24 * 60 * 60 },
      { label: 'day', value: 24 * 60 * 60 },
      { label: 'hour', value: 60 * 60 },
      { label: 'min', value: 60 },
      { label: 'sec', value: 1 }
    ];

    let seconds = secondsInput;
    const parts: string[] = [];

    for (const u of units) {
      const amount = Math.floor(seconds / u.value);
      if (amount > 0) {
        parts.push(`${amount} ${u.label}${amount > 1 ? 's' : ''}`);
        seconds %= u.value;
      }
    }

    return parts.join(' ');
  }

  /** ================= ACTIONS ================= */
  do_changes(value: any) {
    this.change_pw_status.set(false);
    this.error_at_html_user.set(false);

    const body: any = {
      username_html: value.username_html,
      name: value.name,
      tel: value.tel,
      mail: value.mail,
      fediverse_id: value.fediverse_id,
      login_msg: value.login_msg,
      logout_msg: value.logout_msg
    };

    if (value.password) {
      body.password = value.password;
    }

    this.api.post('/api/data/set_user_info/', this.auth.token(), body)
      .subscribe(result => {
        this.change_pw_status.set(result.change_pw);
        this.error_at_html_user.set(result.error_at_html_user);
      });
  }

  do_color_gradient(value: any) {
    this.color_gradient_error.set(null);

    this.api.post(
      `/api/data/change_name_color/${value.col1}/${value.col2}/`,
      this.auth.token(),
      {}
    ).subscribe(result => {
      this.color_gradient_error.set(!result.success);
    });
  }

  async do_fido_register(password: string, name: string) {
    this.resetFidoFlags();

    const result = await this.webauthn.register(
      this.auth.token(),
      password,
      name
    );

    if (result?.error === 1) {
      this.double_register_error.set(true);
    } else if (result?.error === 400) {
      this.no_challenge_error.set(true);
    } else if (result?.error === 404) {
      this.wrong_password_error.set(true);
    } else if (result?.ok === true) {
      this.fido_status_successfull.set(true);
      this.fido_credentials_reload();
    }
  }

  fido_credentials_delete(id: number) {
    this.api.delete(`/api/fido2/credentials/${id}/`, this.auth.token())
      .subscribe(() => this.fido_credentials_reload());
  }

  resetFidoFlags() {
    this.fido_status_successfull.set(false);
    this.double_register_error.set(false);
    this.no_challenge_error.set(false);
    this.wrong_password_error.set(false);
  }

  invite_to_channel() {
    this.inviteSuccess.set(false);
    this.inviteError.set('');

    const channelId = Number(this.inviteChannelId);
    const username = this.inviteUsername.trim();
    if (!channelId || !username) {
      this.inviteError.set('Bitte Channel und User auswählen.');
      return;
    }

    this.api.post('/api/channels/invite/', this.auth.token(), { channel_id: channelId, username })
      .subscribe(result => {
        if (this.hasApiError(result)) {
          this.inviteError.set('Einladung fehlgeschlagen.');
          return;
        }
        this.inviteSuccess.set(true);
      });
  }

  private hasApiError(result: any): boolean {
    if (!result) return true;
    if (Array.isArray(result) && result.length > 0 && result[0] && typeof result[0] === 'object' && 'error_code' in result[0]) return true;
    if (typeof result !== 'object') return true;
    return 'error_code' in result;
  }
}
