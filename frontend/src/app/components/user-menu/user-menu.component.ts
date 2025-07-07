import { CommonModule } from '@angular/common';
import { Component, EventEmitter, OnInit, Output } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-user-menu',
  imports: [CommonModule, FormsModule],
  templateUrl: './user-menu.component.html',
  styleUrl: './user-menu.component.scss'
})
export class UserMenuComponent implements OnInit {

  constructor(public auth: AuthService, public api: ApiService) { }
  @Output() closeEvent = new EventEmitter<string>();

  change_pw: Boolean = false;
  error_at_html_user: Boolean = false;

  global_error: Boolean = false;

  ngOnInit(): void {
    //TODO: error handling in API
    this.api.get("/api/data/get_user_info/", this.auth.token)
      .subscribe(result => {
        this.userinfo = result
        console.log(this.userinfo)
      });
  }
  userinfo: any = [];


  formatSeconds(secondsInput: number) {
    const secondsInMinute = 60;
    const secondsInHour = 60 * secondsInMinute;
    const secondsInDay = 24 * secondsInHour;
    const secondsInWeek = 7 * secondsInDay;
    const secondsInYear = 365 * secondsInDay;

    let seconds = secondsInput;

    const years = Math.floor(seconds / secondsInYear);
    seconds %= secondsInYear;

    const weeks = Math.floor(seconds / secondsInWeek);
    seconds %= secondsInWeek;

    const days = Math.floor(seconds / secondsInDay);
    seconds %= secondsInDay;

    const hours = Math.floor(seconds / secondsInHour);
    seconds %= secondsInHour;

    const minutes = Math.floor(seconds / secondsInMinute);
    seconds %= secondsInMinute;

    const timeParts: string[] = [];

    if (years) timeParts.push(`${years} year(s)`);
    if (weeks) timeParts.push(`${weeks} week(s)`);
    if (days) timeParts.push(`${days} day(s)`);
    if (hours) timeParts.push(`${hours} hour(s)`);
    if (minutes) timeParts.push(`${minutes} min(s)`);
    if (seconds) timeParts.push(`${Math.floor(seconds)} sec(s)`);

    return timeParts.join(' ');
  }


  formatTime(timestamp: number) {
    const date = new Date(timestamp);
    return date.toLocaleString(); // Local date/time string
  }



  do_changes(value: any) {
    this.change_pw = false;
    this.error_at_html_user = false;
    let body: any = {
      "username_html": value.username_html,
      "name": value.name,
      "tel": value.tel,
      "mail": value.mail,
      "fediverse_id": value.fediverse_id,
      "login_msg": value.login_msg,
      "logout_msg": value.logout_msg
    };
    if (value.password != "") {
      body['password'] = value.password;
    }
    this.api.post("/api/data/set_user_info/", this.auth.token, body).subscribe(result => {
      this.change_pw = result['change_pw'];
      this.error_at_html_user = result['error_at_html_user'];
    });
  }



}