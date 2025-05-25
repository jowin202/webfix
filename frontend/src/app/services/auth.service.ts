import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, map } from 'rxjs/operators';

@Injectable({
  providedIn: 'root'
})
export class AuthService {


  token: any = "";
  username: string = "";
  channel_id: number = -1;
  admin_level: number = 0;
  logged_in: boolean = false;

  password_error : boolean = false;
  guest_error : boolean = false;

  constructor(private http: HttpClient, private router: Router) {
    this.token_from_browser();
  }


  do_login(username: string, password: string, remember: boolean): void {
    const headers = new HttpHeaders({
      'accept': 'application/json',
      'Content-Type': 'application/x-www-form-urlencoded'
    });

    //no json
    const body = new HttpParams().set("username", username).set("password", password);

    this.http.post("/api/login/", body, { headers: headers }).pipe(
      map((response: any) => {
        if (this.isJson(response)) {
          return response;
        } else {
          throw new Error('Response is not a valid JSON.');
        }
      }),
      catchError((error: any) => {
        if (error.status === 400) {
          this.password_error = true;
          console.error('Unauthorized access. Please login.');
          return []
        }
        return [];
      })

    ).subscribe((response) => {
      if ("access_token" in response && "admin" in response) {
        this.admin_level = response['admin'];
        this.token = response['access_token'];
        this.channel_id = response["channel_id"];
        this.username = username;
        this.logged_in = true;
        this.router.navigate(['/chat']);

        if (typeof localStorage !== "undefined" && localStorage !== null) {
          if (remember)
            localStorage.setItem("token", response['access_token']);
          else
            localStorage.setItem("token", "");
        }

        if (typeof sessionStorage !== "undefined" && sessionStorage !== null) {
          sessionStorage.setItem("token", response['access_token']);
        }

      }
    });
  }


  do_guest_login(username: string, remember: boolean): void {
    const headers = new HttpHeaders({
      'accept': 'application/json',
    });

    this.http.post(`/api/login/guest_login/?username=${encodeURIComponent(username)}`, {}, { headers: headers }).pipe(
      map((response: any) => {
        if (this.isJson(response)) {
          return response;
        } else {
          throw new Error('Response is not a valid JSON.');
        }
      }),
      catchError((error: any) => {
        if (error.status === 400) {
          this.guest_error = true;
          console.error('Unauthorized access. Please login.');
          return []
        }
        return [];
      })

    ).subscribe((response) => {
      if ("access_token" in response) {
        this.admin_level = 0; //response['admin']; //guest is never admin
        this.token = response['access_token'];
        this.username = username;
        this.channel_id = response["channel_id"];
        this.logged_in = true;
        this.router.navigate(['/chat']);

        console.log("hahaha")
        if (typeof localStorage !== "undefined" && localStorage !== null) {
          if (remember)
            localStorage.setItem("token", response['access_token']);
          else
            localStorage.setItem("token", "");
        }

        if (typeof sessionStorage !== "undefined" && sessionStorage !== null) {
          sessionStorage.setItem("token", response['access_token']);
        }

      }
    });
  }





  do_login_from_token(token: string): void {
    const headers = new HttpHeaders({
      'Content-Type': 'application/json',
      'Authorization': 'Bearer ' + token //assuming token is known
    });

    this.http.get("/api/login/from_token/" + token + "/", { headers: headers }).pipe(
      map((response: any) => {
        if (this.isJson(response)) {
          return response;
        } else {
          throw new Error('Response is not a valid JSON.');
        }
      }),
      catchError((error: any) => {
        if (error.status === 404) {
          console.error('Login failed.');
          return []
        }
        return [];
      })

    ).subscribe((response) => {
      if ("username" in response && "admin" in response && "channel_id" in response) {
        this.token = token
        this.username = response["username"];
        this.admin_level = response["admin"];
        this.channel_id = response["channel_id"];
        this.logged_in = true;
      }
    });
  }


  token_from_browser() {
    let token: string = "";
    if (typeof sessionStorage !== "undefined" && sessionStorage !== null) {
      token = sessionStorage.getItem("token") ?? "";
    }

    if (token == "" && typeof localStorage !== "undefined" && localStorage !== null) {
      token = localStorage.getItem("token") ?? "";
    }

    if (token != "") {
      this.do_login_from_token(token);
    }
  }


  do_logout() {

    this.http.get("/api/login/logout_token/" + this.token + "/").subscribe((response) => {
      //not interested what happens here, 
    });

    if (typeof sessionStorage !== "undefined" && sessionStorage !== null) {
      sessionStorage.setItem("token", "");
    }

    if (typeof localStorage !== "undefined" && localStorage !== null) {
      localStorage.setItem("token", "");
    }
    this.password_error = false; //login page without error
    this.guest_error = false;
    this.logged_in = false;
  }




  private isJson(json: any) {
    try {
      JSON.parse(JSON.stringify(json));
      return true;
    } catch (e) {
      return false;
    }
  }

  
}
