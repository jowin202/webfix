import { Component, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';
import { ActivatedRoute, RouterModule } from '@angular/router';

// Material
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'app-recover-password',
  standalone: true,
  imports: [
    FormsModule,
    RouterModule,

    // MATERIAL
    MatFormFieldModule,
    MatInputModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule
  ],
  templateUrl: './reset-password-form.html',
  styleUrl: './reset-password-form.scss'
})
export class ResetPasswordForm {

  // SIGNALS
  error = signal(false);
  success = signal(false);

  token: string = "";

  pass = "";
  confPass = "";

  constructor(
    public api: ApiService,
    private route: ActivatedRoute
  ) {
    this.token = this.route.snapshot.paramMap.get("token") || "";
  }

  resetPassword(data: any) {

    this.error.set(false);
    this.success.set(false);

    this.api.post("/api/pwmanage/recover_password/", "", {
      lost_pass_token: this.token,
      new_pass: data.newPassword
    })
    .subscribe(result => {
      if ("error_code" in result) {
        this.error.set(true);
      } else {
        this.success.set(true);
        this.pass = "";
        this.confPass = "";
      }
    });
  }
}
