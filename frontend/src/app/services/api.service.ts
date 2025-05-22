import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { catchError, map, Observable, Observer } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class ApiService {

  
  constructor(private http: HttpClient) { }



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
            return [{ "error_code": -1, "error_string": "no valid json"}]
          }
        }),
        catchError((error: any) => {
          //if (error.status === 401) {
          //  return []
          //}
          return [{ "error_code": error.status, "error_string": "Exception"}]
        })
      );
  }


  pic_dict: { [key: string]: any } = {};
  download_pic(url: string,auth_token: string, forceDownload : boolean = false) {
    var headers = new HttpHeaders({
    });
    if (auth_token) {
      headers = headers.set('Authorization', 'Bearer ' + auth_token);
    }

    if (forceDownload || !this.pic_dict.hasOwnProperty(url))
      this.http.get(url, {headers: headers, responseType: 'blob'}).subscribe((result)=>{
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
            return [{ "error_code": -1, "error_string": "no valid json"}]
          }
        }),
        catchError((error: any) => {
          //if (error.status === 401) {
          //  return []
          //}
          return [{ "error_code": error.status, "error_string": "Exception"}]
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
            return [{ "error_code": -1, "error_string": "no valid json"}]
          }
        }),
        catchError((error: any) => {
          //if (error.status === 401) {
          //  return []
          //}
          return [{ "error_code": error.status, "error_string": "Exception"}]
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
            return [{ "error_code": -1, "error_string": "no valid json"}]
          }
        }),
        catchError((error: any) => {
          //if (error.status === 401) {
          //  return []
          //}
          return [{ "error_code": error.status, "error_string": "Exception"}]
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
            return [{ "error_code": -1, "error_string": "no valid json"}]
          }
        }),
        catchError((error: any) => {
          //if (error.status === 401) {
          //  return []
          //}
          return [{ "error_code": error.status, "error_string": "Exception"}]
        })
      );
  }



  connect_stream(url: string, auth_token?: string): Observable<any> {
    return new Observable((observer: Observer<any>) => {
      // Authentifizierung über Query-Parameter (alternativ: Header über Server-seitige Lösung)
      const wsUrl = auth_token ? `${url}?token=${auth_token}` : url;
      
      const socket = new WebSocket(wsUrl);

      socket.onopen = () => {
        //console.log('WebSocket connection opened');
      };

      socket.onmessage = (event) => {
        const data = event.data;
        if (this.isJson(data)) {
          observer.next(JSON.parse(data));
        } else {
          observer.next([{ error_code: -1, error_string: 'no valid json' }]);
        }
      };

      socket.onerror = (error) => {
        observer.next([{ error_code: -2, error_string: 'WebSocket error' }]);
      };

      socket.onclose = (event) => {
        if (!event.wasClean) {
          observer.next([{ error_code: event.code, error_string: 'WebSocket closed unexpectedly' }]);
        }
        observer.complete();
      };

      // Teardown logic
      return () => {
        socket.close();
      };
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
