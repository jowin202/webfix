import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { AuthService } from '../../services/auth.service';
import { RouterModule } from '@angular/router';
import { ApiService } from '../../services/api.service';
import { WebAuthnService } from '../../services/webauthn.service';

@Component({
  selector: 'app-login-window',
  imports: [FormsModule, RouterModule],
  templateUrl: './login-window.component.html',
  styleUrl: './login-window.component.scss'
})
export class LoginWindowComponent {

  constructor(public auth: AuthService, public api: ApiService, public webauthn: WebAuthnService) { }

  async do_page_login(value: any) {
    if (value.password == "") { //fido login
      var result = await this.webauthn.login(value.username);
      if ("access_token" in result){
        this.auth.do_login_from_token(result['access_token']);
      }
    }
    else { // normal login
      this.auth.do_login(value.username, value.password, value.remember);
    }
  }

  do_guest_login(value: any) {
    this.auth.do_guest_login(value.guestName, false);
  }
}
