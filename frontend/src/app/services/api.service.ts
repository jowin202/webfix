import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { catchError, map, Observable, Observer } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  constructor(private http: HttpClient) { }
  public_infos: any = [];



  upload(url: string, auth_token: string, object: any): Observable<any> {
    var headers = new HttpHeaders({
    });
    if (auth_token) {
      headers = headers.set('Authorization', 'Bearer ' + auth_token);
    }

    return this.http.post(url,
      object, // data from parameter
      { headers: headers }).pipe(

        map((response: any) => {
          if (this.isJson(response)) {
            return response;
          } else {
            return [{ "error_code": -1, "error_string": "no valid json" }]
          }
        }),
        catchError((error: any) => {
          //if (error.status === 401) {
          //  return []
          //}
          return [{ "error_code": error.status, "error_string": "Exception" }]
        })
      );
  }


  pic_dict: { [key: string]: any } = {};
  download_pic(url: string, auth_token: string, forceDownload: boolean = false) {
    var headers = new HttpHeaders({
    });
    if (auth_token) {
      headers = headers.set('Authorization', 'Bearer ' + auth_token);
    }

    if (forceDownload || !this.pic_dict.hasOwnProperty(url))
      this.http.get(url, { headers: headers, responseType: 'blob' }).subscribe((result) => {
        this.pic_dict[url] = URL.createObjectURL(result);
      });
  }






  post(url: string, auth_token: string, object: any): Observable<any> {
    var headers = new HttpHeaders({
      'Content-Type': "application/json",
    });
    if (auth_token) {
      headers = headers.set('Authorization', 'Bearer ' + auth_token);
    }

    return this.http.post(url,
      object, // data from parameter
      { headers: headers }).pipe(

        map((response: any) => {
          if (this.isJson(response)) {
            return response;
          } else {
            return [{ "error_code": -1, "error_string": "no valid json" }]
          }
        }),
        catchError((error: any) => {
          //if (error.status === 401) {
          //  return []
          //}
          return [{ "error_code": error.status, "error_string": "Exception" }]
        })
      );
  }

  get(url: string, auth_token: string): Observable<any> {
    var headers = new HttpHeaders({
      'Content-Type': 'application/json',
    });
    if (auth_token) {
      headers = headers.set('Authorization', 'Bearer ' + auth_token);
    }

    return this.http.get(url,
      { headers: headers }).pipe(

        map((response: any) => {
          if (this.isJson(response)) {
            return response;
          } else {
            return [{ "error_code": -1, "error_string": "no valid json" }]
          }
        }),
        catchError((error: any) => {
          //if (error.status === 401) {
          //  return []
          //}
          return [{ "error_code": error.status, "error_string": "Exception" }]
        })
      );
  }




  put(url: string, auth_token: string, object: any): Observable<any> {
    var headers = new HttpHeaders({
      'Content-Type': 'application/json',
    });
    if (auth_token) {
      headers = headers.set('Authorization', 'Bearer ' + auth_token);
    }

    return this.http.put(url,
      object, // data from parameter
      { headers: headers }).pipe(

        map((response: any) => {
          if (this.isJson(response)) {
            return response;
          } else {
            return [{ "error_code": -1, "error_string": "no valid json" }]
          }
        }),
        catchError((error: any) => {
          //if (error.status === 401) {
          //  return []
          //}
          return [{ "error_code": error.status, "error_string": "Exception" }]
        })
      );
  }



  delete(url: string, auth_token: string): Observable<any> {
    var headers = new HttpHeaders({
      'Content-Type': 'application/json',
    });
    if (auth_token) {
      headers = headers.set('Authorization', 'Bearer ' + auth_token);
    }

    return this.http.delete(url,
      { headers: headers }).pipe(

        map((response: any) => {
          if (this.isJson(response)) {
            return response;
          } else {
            return [{ "error_code": -1, "error_string": "no valid json" }]
          }
        }),
        catchError((error: any) => {
          //if (error.status === 401) {
          //  return []
          //}
          return [{ "error_code": error.status, "error_string": "Exception" }]
        })
      );
  }



connect_stream(
  url: string,
  auth_token?: string,
  retryInterval: number = 5000 // 5 seconds
): Observable<any> {
  return new Observable((observer: Observer<any>) => {
    let manuallyClosed = false;
    let socket: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

    const shouldReconnect = (event: CloseEvent) => {
      // Only treat as unexpected if not clean OR close code not normal/going-away
      const normalCodes = new Set([1000, 1001]);
      return !event.wasClean || !normalCodes.has(event.code);
    };

    const clearReconnectTimer = () => {
      if (reconnectTimer) {
        clearTimeout(reconnectTimer);
        reconnectTimer = null;
      }
    };

    const scheduleReconnect = () => {
      clearReconnectTimer();
      reconnectTimer = setTimeout(() => {
        if (!manuallyClosed) {
          connect();
        }
      }, retryInterval);
    };

    const connect = () => {
      const wsUrl = auth_token ? `${url}?token=${auth_token}` : url;
      socket = new WebSocket(wsUrl);

      socket.onopen = () => {
        // reset any pending retry
        clearReconnectTimer();
      };

      socket.onmessage = (event) => {
        const data = event.data;
        if (this.isJson(data)) {
          observer.next(JSON.parse(data));
        } else {
          observer.next({ error_code: -1, error_string: 'no valid json' });
        }
      };

      socket.onerror = () => {
        observer.next({ error_code: -2, error_string: 'WebSocket error' });
      };

      socket.onclose = (event) => {
        // Decide reconnect strictly based on unexpected closure
        if (!manuallyClosed && shouldReconnect(event)) {
          observer.next({
            error_code: -3,
            server_error_code: event.code,
            error_string: 'WebSocket closed unexpectedly; retrying in 5s'
          });
          scheduleReconnect();
        } else {
          // Normal/manual closure → complete and do NOT retry
          observer.complete();
        }
      };
    };

    // kick off
    connect();

    // Cleanup on unsubscribe
    return () => {
      manuallyClosed = true;
      clearReconnectTimer();

      if (socket) {
        // Remove handlers to avoid firing after manual teardown
        socket.onopen = null;
        socket.onmessage = null;
        socket.onerror = null;
        socket.onclose = null;

        // Close whether OPEN or CONNECTING to ensure teardown
        if (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING) {
          try { socket.close(1000, 'Client unsubscribe'); } catch {}
        }
        socket = null;
      }
    };
  });
}






  update_public_infos() {
    this.get("/api/register/public_infos/", "")
      .subscribe(result => {
        this.public_infos = result
      });

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
