import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { ApiService } from '../../services/api.service';

@Component({
  selector: 'app-register-window',
  imports: [FormsModule, RouterModule],
  templateUrl: './register-window.component.html',
  styleUrl: './register-window.component.scss'
})
export class RegisterWindowComponent {

  constructor (private api : ApiService){}

  error : Boolean = false;
  success: Boolean = false;

  pass : string = "";
  confPass : string = "";

  do_register(content : any)
  {
    this.success = false;
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
        if ("error_code" in result)
          this.error = true;
        else 
        {
          this.error = false;
          this.success = true;
          this.pass = "";
          this.confPass = "";
        }
      });
    

  }
}
