import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';
import { ActivatedRoute } from '@angular/router';

@Component({
  selector: 'app-recover-password',
  imports: [CommonModule, FormsModule],
  templateUrl: './recover-password.component.html',
  styleUrl: './recover-password.component.scss'
})
export class RecoverPasswordComponent {
  error : Boolean = false;
  success : Boolean = false;
  token : string;

  constructor(public api : ApiService, private route: ActivatedRoute){
    this.token = this.route.snapshot.paramMap.get('token') || '';
  }



  resetPassword(data : any) {
    this.api.post('/api/pwmanage/recover_password/', "", {
      "lost_pass_token": this.token,
      "new_pass": data.newPassword
    }).subscribe(result => {
      console.log(result);
    });
  }

}
