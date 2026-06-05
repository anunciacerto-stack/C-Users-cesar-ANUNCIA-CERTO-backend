import { Injectable } from '@nestjs/common';
import { NfcCoreService, NfcRegisterInput, NfcUpdateInput } from './nfc-core.service';

@Injectable()
export class NfcService {
  constructor(private readonly nfcCore: NfcCoreService) {}

  async register(body: NfcRegisterInput) {
    return this.nfcCore.register(body);
  }

  async update(body: NfcUpdateInput) {
    return this.nfcCore.update(body);
  }

  async getStatus(objectId: string) {
    const status = await this.nfcCore.getStatus(objectId);
    return { message: status };
  }

  async getAll(limit?: number) {
    return this.nfcCore.history(limit);
  }

  async registerScan(tagId: string, userAgent?: string, ipAddress?: string) {
    return this.nfcCore.registerScan(tagId, userAgent, ipAddress);
  }

  async getAnalytics(tagId: string) {
    return this.nfcCore.getAnalytics(tagId);
  }

  async resolveTag(tagId: string) {
    return this.nfcCore.resolveTag(tagId);
  }
}
