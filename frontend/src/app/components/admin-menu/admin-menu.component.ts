import { Component, EventEmitter, Output } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-admin-menu',
  imports: [FormsModule],
  templateUrl: './admin-menu.component.html',
  styleUrl: './admin-menu.component.scss'
})
export class AdminMenuComponent {
  @Output() closeEvent = new EventEmitter<string>();

  constructor(public auth: AuthService, public api: ApiService) { }
  error : boolean = false;
  menu_values : any = {
  };

  users: any[] = [];
  user_action_error: boolean = false;
  action_duration: number = 300;
  action_silent: boolean = false;


  ngOnInit(): void {
    this.api.post("/api/admin/settings/get_settings/", this.auth.token,[
      'allow_guest_login',
      'activate_timeout',
      'mandatory_user_verification',
      'user_verification_mail',
      'user_verification_fediverse',
      'announcement_general',
      'announcement_guests',
      'announcement_registered_users',
      'announcement_team',
      'timeout_time',
      'pw_recovery_token_valid_time',
      'fido2_challenge_valid_time',
      'pw_min_len'
    ])
      .subscribe(result => {
        this.menu_values = result
      });

    this.load_users();
  }

  load_users() {
    this.api.get("/api/admin/userdb/get_all_users/", this.auth.token)
      .subscribe(result => {
        if (!("error_code" in result)) {
          this.users = result;
        }
      });
  }

  formatTime(timestamp: any): string {
    if (!timestamp) {
      return '-';
    }
    const date = new Date(timestamp);
    if (date.getFullYear() > 9000) {
      return 'permanent';
    }
    if (date.getTime() <= Date.now()) {
      return '-';
    }
    return date.toLocaleString();
  }

  kick_user(user: any, time: number, silent: boolean) {
    this.user_action_error = false;
    this.api.post("/api/admin/kick_user/", this.auth.token, { user_id: user.id, time, silent })
      .subscribe(result => {
        if (result === false) {
          this.user_action_error = true;
        }
        this.load_users();
      });
  }

  mute_user(user: any, time: number, silent: boolean) {
    this.user_action_error = false;
    this.api.post("/api/admin/mute_user/", this.auth.token, { user_id: user.id, time, silent })
      .subscribe(result => {
        if (result === false) {
          this.user_action_error = true;
        }
        this.load_users();
      });
  }

  do_changes(value : any)
  {
    this.api.post("/api/admin/settings/set_settings/", this.auth.token,{
      'allow_guest_login': value.allow_guest_login,
      'activate_timeout': value.activate_timeout,
      'mandatory_user_verification': value.mandatory_user_verification,
      'user_verification_mail': value.user_verification_mail,
      'user_verification_fediverse': value.user_verification_fediverse,
      'announcement_general': value.announcement_general,
      'announcement_guests': value.announcement_guests,
      'announcement_registered_users': value.announcement_registered_users,
      'announcement_team': value.announcement_team,
      'timeout_time': value.timeout_time as number,
      'pw_recovery_token_valid_time': value.pw_recovery_token_valid_time as number,
      'fido2_challenge_valid_time': value.fido2_challenge_valid_time as number,
      'pw_min_len': value.pw_min_len as number
  })
      .subscribe(result => {
        console.log(result);
      });

  }

}
