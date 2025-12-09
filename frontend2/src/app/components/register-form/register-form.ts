import { Component, signal } from '@angular/core';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { ApiService } from '../../services/api.service';
import { MatIconModule } from '@angular/material/icon';
import { MatFormFieldControl, MatFormFieldModule } from '@angular/material/form-field';
import { MatCardModule } from '@angular/material/card';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';

@Component({
  selector: 'app-register-window',
  standalone: true,
  imports: [FormsModule, RouterModule, MatIconModule, MatFormFieldModule, MatInputModule, MatButtonModule, MatCardModule,ReactiveFormsModule],
  templateUrl: './register-form.html',
  styleUrl: './register-form.scss'
})
export class RegisterForm {

  constructor(private api: ApiService) {}

  // SIGNALS statt normaler Variablen
  error = signal(false);
  success = signal(false);

  pass = '';
  confPass = '';

  do_register(content: any) {

    this.success.set(false);
    this.error.set(false);

    this.api.post("/api/register/register/", "", {
      "username": content.username,
      "name": content.name,
      "tel": content.tel,
      "mail": content.email,
      "fediverse_id": content.fediverse,
      "password": content.password,
      "verify_mail": true,
      "verify_fediverse": true
    })
    .subscribe(result => {

      if ("error_code" in result) {
        this.error.set(true);
      } else {
        this.error.set(false);
        this.success.set(true);
        this.pass = "";
        this.confPass = "";
      }

    });
  }
}
