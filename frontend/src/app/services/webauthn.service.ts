import { HttpHeaders } from '@angular/common/http';
import { Injectable } from '@angular/core';

@Injectable({
  providedIn: 'root'
})
export class WebAuthnService {
 
  
  private api = 'api/fido2'; //

  // --- base64url helpers ---
  private b64uToBuf(b64u: string): ArrayBuffer {
    const pad = '='.repeat((4 - (b64u.length % 4)) % 4);
    const b64 = (b64u + pad).replace(/-/g, '+').replace(/_/g, '/');
    const str = atob(b64);
    const bytes = new Uint8Array(str.length);
    for (let i = 0; i < str.length; i++) bytes[i] = str.charCodeAt(i);
    return bytes.buffer;
  }

  private bufToB64u(buf: ArrayBuffer): string {
    const bytes = new Uint8Array(buf);
    let str = '';
    for (let i = 0; i < bytes.length; i++) str += String.fromCharCode(bytes[i]);
    return btoa(str).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
  }

  // --- Registration ---
  async register(auth_token: string, password : string) {
    // 1) ask server for options
    const res = await fetch(`${this.api}/register/begin`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json',
      'Authorization': 'Bearer ' + auth_token },
      body: JSON.stringify({password: password})
    });
    if (res.status == 404) //no user, wrong password
    {
      return {error: res.status}
    }
    
    const { publicKey } = await res.json();

    // convert to ArrayBuffers
    publicKey.challenge = this.b64uToBuf(publicKey.challenge);
    publicKey.user.id = this.b64uToBuf(publicKey.user.id);
    if (publicKey.excludeCredentials) {
      publicKey.excludeCredentials = publicKey.excludeCredentials.map((c: any) => ({
        ...c,
        id: this.b64uToBuf(c.id)
      }));
    }

    // 2) create credential
    let cred: PublicKeyCredential;
    try {
      cred = await navigator.credentials.create({ publicKey }) as PublicKeyCredential;
      if (!cred) throw new Error('Creation cancelled');
    }
    catch (err: any) {
    if (err instanceof DOMException && err.name === "InvalidStateError") {
      return { error: 1 };
    }
    throw err; // rethrow anything else
  }

    const response = cred.response as AuthenticatorAttestationResponse;
    const payload = {
      id: cred.id,
      rawId: this.bufToB64u(cred.rawId),
      type: cred.type,
      response: {
        attestationObject: this.bufToB64u(response.attestationObject),
        clientDataJSON: this.bufToB64u(response.clientDataJSON),
      },
      clientExtensionResults: cred.getClientExtensionResults?.() ?? {},
    };

    // 3) send back to server
    const verify = await fetch(`${this.api}/register/verify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json',
      'Authorization': 'Bearer ' + auth_token
    
    },
      body: JSON.stringify({  credential: payload })
    });
    if (verify.status == 400) // no challenge
    {
      return {error : verify.status}
    }
    return verify.json();
  }

  // --- Login ---
  async login(username: string) {
    // 1) ask server for options
    const res = await fetch(`${this.api}/login/begin`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username })
    });
    if (!res.ok) throw new Error(await res.text());
    const { publicKey } = await res.json();

    // convert to ArrayBuffers
    publicKey.challenge = this.b64uToBuf(publicKey.challenge);
    if (publicKey.allowCredentials) {
      publicKey.allowCredentials = publicKey.allowCredentials.map((c: any) => ({
        ...c,
        id: this.b64uToBuf(c.id)
      }));
    }

    // 2) request assertion
    const cred = await navigator.credentials.get({ publicKey }) as PublicKeyCredential;
    if (!cred) throw new Error('Get cancelled');

    const response = cred.response as AuthenticatorAssertionResponse;
    const payload = {
      id: cred.id,
      rawId: this.bufToB64u(cred.rawId),
      type: cred.type,
      response: {
        authenticatorData: this.bufToB64u(response.authenticatorData),
        clientDataJSON: this.bufToB64u(response.clientDataJSON),
        signature: this.bufToB64u(response.signature),
        userHandle: response.userHandle ? this.bufToB64u(response.userHandle) : null,
      },
      clientExtensionResults: cred.getClientExtensionResults?.() ?? {},
    };

    // 3) send back to server
    const verify = await fetch(`${this.api}/login/verify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, credential: payload })
    });
    if (!verify.ok) throw new Error(await verify.text());
    return verify.json();
  }

}
