import { BadRequestException, Injectable } from '@nestjs/common';

export interface NfcRegisterInput {
  tagId?: string;
  tag_id?: string;
  objectId?: string;
  object_id?: string;
  userId?: string;
  user_id?: string;
}

export interface NfcUpdateInput extends NfcRegisterInput {
  status?: string;
}

export interface NfcCoreRecord {
  id: string;
  tag_id: string;
  object_id: string;
  user_id: string;
  status: string;
  message: string;
  created_at: string;
  updated_at: string;
}

@Injectable()
export class NfcCoreService {
  private readonly recordsByObjectId = new Map<string, NfcCoreRecord>();
  private readonly objectIdByTagId = new Map<string, string>();
  private readonly timeline: NfcCoreRecord[] = [];

  register(input: NfcRegisterInput): NfcCoreRecord {
    const tagId = this.normalizeId(input.tagId ?? input.tag_id);
    const objectIdInput = this.normalizeId(input.objectId ?? input.object_id);
    const userId = this.normalizeUser(input.userId ?? input.user_id);

    if (!tagId) {
      throw new BadRequestException('tagId is required');
    }

    const resolvedObjectId = objectIdInput || this.objectIdByTagId.get(tagId) || tagId;
    const now = new Date().toISOString();
    const existing = this.recordsByObjectId.get(resolvedObjectId);

    const record: NfcCoreRecord = {
      id: existing?.id ?? `nfc_${Date.now()}`,
      tag_id: tagId,
      object_id: resolvedObjectId,
      user_id: userId,
      status: existing?.status ?? 'registered',
      message: existing ? 'NFC atualizado com dados de registro' : 'NFC registrado com sucesso',
      created_at: existing?.created_at ?? now,
      updated_at: now,
    };

    this.store(record);
    return record;
  }

  update(input: NfcUpdateInput): NfcCoreRecord {
    const tagId = this.normalizeId(input.tagId ?? input.tag_id);
    const objectIdInput = this.normalizeId(input.objectId ?? input.object_id);
    const userId = this.normalizeUser(input.userId ?? input.user_id);
    const status = (input.status ?? '').trim();

    if (!tagId) {
      throw new BadRequestException('tagId is required');
    }

    if (!status) {
      throw new BadRequestException('status is required');
    }

    const resolvedObjectId = objectIdInput || this.objectIdByTagId.get(tagId) || tagId;
    const now = new Date().toISOString();
    const existing = this.recordsByObjectId.get(resolvedObjectId);

    const record: NfcCoreRecord = {
      id: existing?.id ?? `nfc_${Date.now()}`,
      tag_id: tagId,
      object_id: resolvedObjectId,
      user_id: userId,
      status,
      message: 'NFC atualizado com sucesso',
      created_at: existing?.created_at ?? now,
      updated_at: now,
    };

    this.store(record);
    return record;
  }

  getStatus(objectId: string): string {
    const normalizedObjectId = this.normalizeId(objectId);
    if (!normalizedObjectId) {
      return 'UNKNOWN';
    }
    return this.recordsByObjectId.get(normalizedObjectId)?.status ?? 'UNKNOWN';
  }

  history(limit = 100): NfcCoreRecord[] {
    return this.timeline.slice(0, Math.max(1, limit));
  }

  private store(record: NfcCoreRecord) {
    this.recordsByObjectId.set(record.object_id, record);
    this.objectIdByTagId.set(record.tag_id, record.object_id);
    this.timeline.unshift(record);
    if (this.timeline.length > 500) {
      this.timeline.pop();
    }
  }

  private normalizeId(value?: string): string {
    return (value ?? '').trim();
  }

  private normalizeUser(value?: string): string {
    const userId = (value ?? '').trim();
    return userId || 'system';
  }
}
