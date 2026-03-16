import { inject, Injectable, PLATFORM_ID, signal } from '@angular/core';
import { ApiService } from './api.service';
import { AuthService } from './auth.service';
import { Observable } from 'rxjs';
import { PrivateMessage, PrivateMessagesByUser, PublicMessage } from './models';

import { isPlatformBrowser } from '@angular/common';


@Injectable({ providedIn: 'root' })
export class StreamService {
    constructor(private api: ApiService, private auth: AuthService) { }
    private platformId = inject(PLATFORM_ID);

    private socket: WebSocket | null = null;
    private socketToken: string | null = null;
    private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    private pendingCommands: string[] = [];
    private desiredChannelSubscriptions = new Set<number>();

    /* ───────────── Signals (State) ───────────── */

    readonly messages = signal<PublicMessage[]>([]);
    readonly privateMessages = signal<PrivateMessagesByUser>({});
    readonly userChanged = signal(0);
    readonly channelChanged = signal(0);

    readonly htmlUsers = signal<Record<string, string>>({});

    /* ───────────── Public API ───────────── */


    connect_stream(url: string, token?: string): Observable<unknown> {
        return new Observable(observer => {
            const separator = url.includes('?') ? '&' : '?';
            const connectToken = token ?? '';
            const ws = new WebSocket(
                token ? `${url}${separator}token=${encodeURIComponent(token)}` : url
            );

            ws.onopen = () => {
                this.socket = ws;
                this.socketToken = connectToken;
                this.clearReconnectTimer();
                this.flushPendingCommands();
                this.syncChannelSubscriptions();
            };
            ws.onmessage = e => {
                try {
                    observer.next(JSON.parse(e.data));
                } catch {
                    // Ignore malformed payloads instead of crashing runtime handling.
                }
            };
            ws.onerror = e => observer.error(e);
            ws.onclose = () => {
                if (this.socket === ws) {
                    this.socket = null;
                    this.socketToken = null;
                }
                if (this.auth.logged_in() && this.auth.token() && this.auth.token() === connectToken) {
                    this.scheduleReconnect();
                }
                observer.complete();
            };

            return () => {
                if (this.socket === ws) this.socket = null;
                if (this.socketToken === connectToken) this.socketToken = null;
                ws.close(1000, 'unsubscribe');
            };
        });
    }

    connect() {
        if (!isPlatformBrowser(this.platformId)) return;
        const token = this.auth.token();
        if (!token) return;

        if (this.socket && this.socket.readyState === WebSocket.OPEN && this.socketToken === token) {
            return;
        }

        if (this.socket && this.socketToken !== token) {
            this.socket.close(1000, 'token-changed');
            this.socket = null;
            this.socketToken = null;
        }

        if (this.socket && this.socket.readyState === WebSocket.CONNECTING) {
            return;
        }

        this.connect_stream('/api/stream/ws3?manual_subscribe=1', token)
            .subscribe(event => this.handleEvent(event));
    }

    subscribeChannel(channelId: number) {
        this.desiredChannelSubscriptions.add(channelId);
        this.sendCommand({ action: 'subscribe', channel: channelId });
    }

    unsubscribeChannel(channelId: number) {
        this.desiredChannelSubscriptions.delete(channelId);
        this.sendCommand({ action: 'unsubscribe', channel: channelId });
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
        if (!event || typeof event !== 'object') return;

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
            if (event.reload_channels === true) {
                this.channelChanged.update(v => v + 1);
            }
            return;
        }

        if (event.cat === 'announcement') {
            this.pushMessage({ cat: 'announcement', message: event.msg });
            return;
        }

        if (event.cat === 'channel_access_added') {
            this.pushMessage({
                cat: 'statusmsg',
                channel: Number(event.channel ?? 1),
                message: `Channel ${event.channel} available`,
            });
            this.channelChanged.update(v => v + 1);
            return;
        }

        if (event.cat === 'channel_access_removed') {
            this.pushMessage({
                cat: 'statusmsg',
                channel: Number(event.channel ?? 1),
                message: `Channel ${event.channel} removed`,
            });
            this.channelChanged.update(v => v + 1);
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

    private sendCommand(command: { action: 'subscribe' | 'unsubscribe'; channel: number }) {
        const payload = JSON.stringify(command);
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(payload);
            return;
        }
        this.pendingCommands.push(payload);
    }

    private flushPendingCommands() {
        if (!this.socket || this.socket.readyState !== WebSocket.OPEN) return;
        for (const payload of this.pendingCommands) {
            this.socket.send(payload);
        }
        this.pendingCommands = [];
    }

    private syncChannelSubscriptions() {
        if (!this.socket || this.socket.readyState !== WebSocket.OPEN) return;
        for (const channelId of this.desiredChannelSubscriptions) {
            this.socket.send(JSON.stringify({ action: 'subscribe', channel: channelId }));
        }
    }

    private scheduleReconnect() {
        if (this.reconnectTimer) return;
        this.reconnectTimer = setTimeout(() => {
            this.reconnectTimer = null;
            this.connect();
        }, 750);
    }

    private clearReconnectTimer() {
        if (!this.reconnectTimer) return;
        clearTimeout(this.reconnectTimer);
        this.reconnectTimer = null;
    }
}
