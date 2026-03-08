import { BadRequestException, Injectable } from '@nestjs/common';
import { NfcCoreService } from '../nfc/nfc-core.service';

export interface SherifCheckBody {
  objectId?: string;
  object_id?: string;
  userId?: string;
  user_id?: string;
  status?: string;
}

interface SherifRecord {
  id: string;
  object_id: string;
  user_id: string;
  status: string;
  nfc_status: string;
  message: string;
  created_at: string;
}

@Injectable()
export class SherifService {
  private readonly checks: SherifRecord[] = [];

  constructor(private readonly nfcCore: NfcCoreService) {}

  check(body: SherifCheckBody) {
    const objectId = (body.objectId ?? body.object_id ?? '').trim();
    const userId = (body.userId ?? body.user_id ?? 'system').trim() || 'system';
    const status = (body.status ?? 'checked').trim() || 'checked';

    if (!objectId) {
      throw new BadRequestException('objectId is required');
    }

    const nfcStatus = this.nfcCore.getStatus(objectId);
    const now = new Date().toISOString();
    const record: SherifRecord = {
      id: `sh_${Date.now()}`,
      object_id: objectId,
      user_id: userId,
      status,
      nfc_status: nfcStatus,
      message:
        nfcStatus === 'UNKNOWN'
          ? 'Verificacao registrada sem vinculacao NFC'
          : 'Verificacao registrada com vinculacao NFC',
      created_at: now,
    };

    this.checks.unshift(record);
    return record;
  }

  history() {
    return this.checks;
  }
}
