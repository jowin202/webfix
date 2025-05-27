import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { ApiService } from '../../services/api.service';

@Component({
  selector: 'app-forgot-password',
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './forgot-password.component.html',
  styleUrl: './forgot-password.component.scss'
})
export class ForgotPasswordComponent {
  error : Boolean = false;
  success : Boolean = false;

  constructor(public api : ApiService){}

  requestReset(data : any)
  {
    if ("username" in data && "mail" in data && data.mail != "")
    {
      this.api.post('/api/pwmanage/lost_password_mail/', "", {
        "username": data.username,
        "mail": data.mail
      }).subscribe(result => {
        this.success = true;
      });

    }
    if ("username" in data && "fediverse_id" in data && data.fediverse_id != "")
    {
      this.api.post('/api/pwmanage/lost_password_fediverse/', "", {
        "username": data.username,
        "fediverse_id": data.fediverse_id
      }).subscribe(result => {
        this.success = true;
      });
    }
  }
}
