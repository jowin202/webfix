import { inject, Injectable, PLATFORM_ID, signal } from '@angular/core';
import { ApiService } from './api.service';
import { AuthService } from './auth.service';
import { Observable } from 'rxjs';
import { PrivateMessage, PrivateMessagesByUser, PublicMessage } from './models';

import { isPlatformBrowser } from '@angular/common';


@Injectable({ providedIn: 'root' })
export class StreamService {
    constructor(private api: ApiService, private auth: AuthService) { }

    /* ───────────── Signals (State) ───────────── */

    readonly messages = signal<PublicMessage[]>([]);
    readonly privateMessages = signal<PrivateMessagesByUser>({});
    readonly userChanged = signal(0);

    readonly htmlUsers = signal<Record<string, string>>({});

    /* ───────────── Public API ───────────── */


    connect_stream(url: string, token?: string): Observable<unknown> {
        return new Observable(observer => {
            const ws = new WebSocket(
                token ? `${url}?token=${token}` : url
            );

            ws.onmessage = e => observer.next(JSON.parse(e.data));
            ws.onerror = e => observer.error(e);
            ws.onclose = () => observer.complete();

            return () => ws.close(1000, 'unsubscribe');
        });
    }

    connect() {
        if (!isPlatformBrowser(inject(PLATFORM_ID))) return; // ✅ wichtig
        this.connect_stream('/api/stream/ws3', this.auth.token())
            .subscribe(event => this.handleEvent(event));
    }

    addUsernames(entries: { username: string; username_html: string }[]) {
        this.htmlUsers.update(users => {
            const copy = { ...users };
            for (const e of entries) copy[e.username] = e.username_html;
            return copy;
        });
    }

    /* ───────────── Event Router ───────────── */

    private handleEvent(event: any) {
        console.log(event)
        if ('error_code' in event) {
            this.handleError(event);
            return;
        }

        if (event.cat === 'whisper') {
            this.handleWhisper(event);
            return;
        }

        if (event.cat === 'statusmsg') {
            this.pushMessage({ cat: 'statusmsg', message: event.msg });
            return;
        }

        if (event.cat === 'announcement') {
            this.pushMessage({ cat: 'announcement', message: event.msg });
            return;
        }

        if (event.cat === 'userleft' || event.cat === 'userenters') {
            this.handleUserPresence(event);
            return;
        }

        if (event.cat === 'userlogin' || event.cat === 'userlogout') {
            this.handleUserLogin(event);
            return;
        }

        // default public message
        if (event.username && event.message) {
            this.pushMessage({
                cat: 'default',
                username: this.resolveUsername(event.username),
                message: event.message,
                channel: Number(event.channel ?? 1),
            });
        }
    }

    /* ───────────── Handlers ───────────── */

    private handleError(event: any) {
        if (event.error_code === -3) {
            this.pushMessage({
                cat: 'announcement',
                message: `<font color="red">Stream closed, reconnect...</font>`,
            });
        }
    }

    private handleWhisper(event: any) {
        const msg: PrivateMessage = {
            from: event.username,
            message: event.msg,
            timestamp: Date.now(),
        };

        this.privateMessages.update(map => ({
            ...map,
            [msg.from]: [...(map[msg.from] ?? []), msg],
        }));

        this.pushMessage({
            cat: 'private',
            username: event.username,
            message: event.msg,
        });
    }

    private handleUserPresence(event: any) {
        const name = this.resolveUsername(event.username);
        this.pushMessage({
            cat: 'statusmsg',
            message:
                event.cat === 'userleft'
                    ? `${name} left the channel`
                    : `${name} joined the channel`,
            channel: Number(event.channel ?? 1),
        });

        this.userChanged.update(v => v + 1);
    }

    private handleUserLogin(event: any) {
        const name = this.resolveUsername(event.username);
        this.pushMessage({
            cat: 'statusmsg',
            message: `${name} ${event.msg}`,
        });

        this.userChanged.update(v => v + 1);
    }

    /* ───────────── Helpers ───────────── */

    private pushMessage(msg: PublicMessage) {
        this.messages.update(list => [...list, msg]);
    }

    private resolveUsername(username: string): string {
        return this.htmlUsers()[username] ?? username;
    }
}
