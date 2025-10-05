import { Component } from '@angular/core';
import { ApiService } from '../../services/api.service';
import { AuthService } from '../../services/auth.service';
import { StreamService } from '../../services/stream.service';

@Component({
  selector: 'app-stream',
  imports: [],
  templateUrl: './stream.component.html',
  styleUrl: './stream.component.scss'
})
export class StreamComponent {

  constructor(public api: ApiService, public auth: AuthService, public stream: StreamService){ }


  
}
