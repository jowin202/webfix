import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { Injectable, signal } from '@angular/core';
import { catchError, map, of } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class AuthService {

  // STATE SIGNALS
  logged_in = signal(false);
  password_error = signal(false);
  guest_error = signal(false);

  token = signal<string>('');
  username = signal<string>('');
  admin_level = signal<number>(0);
  channel_id = signal<number>(-1);

  // Wird true sobald Auth vollständig geladen wurde
  ready = signal(false);

  constructor(private http: HttpClient) {
    this.restore_token_from_browser();
  }

  /* ------------------------------------------------------
     NORMAL LOGIN
  ------------------------------------------------------ */
  do_login(username: string, password: string, remember: boolean): void {
    this.password_error.set(false);


    const headers = new HttpHeaders({
      'accept': 'application/json',
      'Content-Type': 'application/x-www-form-urlencoded'
    });

    const body = new HttpParams()
      .set("username", username)
      .set("password", password);

    this.http.post("/api/login/", body, { headers })
      .pipe(
        map((response: any) => {
          if (!this.isJson(response)) throw new Error("Invalid JSON");
          return response;
        }),
        catchError(error => {
          if (error.status === 400) this.password_error.set(true);
          return of(null);
        })
      )
      .subscribe(response => {

        if (!response) return;

        this.token.set(response["access_token"]);
        this.username.set(username);
        this.admin_level.set(response["admin"]);
        this.channel_id.set(Number(response["channel_id"] ?? this.channel_id() ?? 1));
        this.logged_in.set(true);
        this.ready.set(true);

        if (remember) localStorage.setItem("token", response["access_token"]);
        else localStorage.removeItem("token");

        sessionStorage.setItem("token", response["access_token"]);
      });
  }

  /* ------------------------------------------------------
     GUEST LOGIN
  ------------------------------------------------------ */
  do_guest_login(username: string, remember: boolean): void {
    this.guest_error.set(false);


    this.http.post(
      `/api/login/guest_login/?username=${encodeURIComponent(username)}`,
      {},
      { headers: new HttpHeaders({ 'accept': 'application/json' }) }
    )
      .pipe(
        map((response: any) => {
          if (!this.isJson(response)) throw new Error("Invalid JSON");
          return response;
        }),
        catchError(error => {
          if (error.status === 400) this.guest_error.set(true);
          return of(null);
        })
      )
      .subscribe(response => {
        if (!response) return;

        this.token.set(response["access_token"]);
        this.username.set(username);
        this.admin_level.set(0);
        this.channel_id.set(Number(response["channel_id"] ?? 1));
        this.logged_in.set(true);
        this.ready.set(true);

        if (remember) localStorage.setItem("token", response["access_token"]);
        else localStorage.removeItem("token");

        sessionStorage.setItem("token", response["access_token"]);
      });
  }

  /* ------------------------------------------------------
     LOGIN FROM TOKEN (AUTO-LOGIN)
  ------------------------------------------------------ */
  do_login_from_token(token: string): void {


    const headers = new HttpHeaders({
      'Content-Type': 'application/json',
      'Authorization': 'Bearer ' + token
    });

    this.http.get<{ username: string; admin: number }>(
      `/api/login/from_token/${token}/`,
      { headers }
    )
      .pipe(
        catchError(err => {
          return of(null);
        })
      )
      .subscribe(response => {

        if (response && response.username) {
          this.username.set(response.username);
          this.admin_level.set(response.admin);
          this.channel_id.set(Number((response as any).channel_id ?? this.channel_id() ?? 1));
          this.token.set(token);
          this.logged_in.set(true);
        } else {
          this.logged_in.set(false);
        }

        this.ready.set(true);
      });
  }

  /* ------------------------------------------------------
     TOKEN RESTORE (SSR SAFE)
  ------------------------------------------------------ */
  private restore_token_from_browser(): void {


    // SSR block
    if (typeof window === 'undefined') {
      this.ready.set(true);
      return;
    }

    let token = sessionStorage.getItem("token");

    if (!token) {
      token = localStorage.getItem("token") ?? '';
    }

    if (token) {
      this.do_login_from_token(token);  // ready is set later
    } else {
      this.ready.set(true);
    }
  }

  /* ------------------------------------------------------
     LOGOUT
  ------------------------------------------------------ */
  do_logout(): void {

    const currentToken = this.token();

    if (currentToken) {
      this.http.get("/api/login/logout_token/" + currentToken + "/").subscribe();
    }

    sessionStorage.removeItem("token");
    localStorage.removeItem("token");

    this.token.set('');
    this.username.set('');
    this.admin_level.set(0);
    this.channel_id.set(-1);
    this.logged_in.set(false);

    // ready bleibt true (Auth ist geladen)
  }

  /* ------------------------------------------------------
     JSON CHECK
  ------------------------------------------------------ */
  private isJson(json: any): boolean {
    try {
      JSON.parse(JSON.stringify(json));
      return true;
    } catch {
      return false;
    }
  }
}
