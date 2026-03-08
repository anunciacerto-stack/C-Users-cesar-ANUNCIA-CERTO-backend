import { Injectable } from '@nestjs/common';
import { NfcCoreService, NfcRegisterInput, NfcUpdateInput } from './nfc-core.service';

@Injectable()
export class NfcService {
  constructor(private readonly nfcCore: NfcCoreService) {}

  register(body: NfcRegisterInput) {
    return this.nfcCore.register(body);
  }

  update(body: NfcUpdateInput) {
    return this.nfcCore.update(body);
  }

  getStatus(objectId: string) {
    return { message: this.nfcCore.getStatus(objectId) };
  }

  getAll() {
    return this.nfcCore.history();
  }
}
