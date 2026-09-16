import { BadRequestException, Injectable } from '@nestjs/common';
import { NfcCoreService } from '../nfc/nfc-core.service';
import { PrismaService } from '../prisma/prisma.service';

export interface SherifCheckBody {
  objectId?: string;
  object_id?: string;
  userId?: string;
  user_id?: string;
  status?: string;
}

@Injectable()
export class SherifService {
  constructor(
    private readonly nfcCore: NfcCoreService,
    private readonly prisma: PrismaService
  ) {}

  async check(body: SherifCheckBody) {
    const objectId = (body.objectId ?? body.object_id ?? '').trim();
    const userId = (body.userId ?? body.user_id ?? 'system').trim() || 'system';
    const status = (body.status ?? 'checked').trim() || 'checked';

    if (!objectId) {
      throw new BadRequestException('objectId is required');
    }

    const nfcStatus = await this.nfcCore.getStatus(objectId);
    const message =
      nfcStatus === 'UNKNOWN'
        ? 'Verificacao registrada sem vinculacao NFC'
        : 'Verificacao registrada com vinculacao NFC';

    const record = await this.prisma.sherifCheck.create({
      data: {
        userId,
        tipo: 'audit',
        valor: objectId,
        resultado: status,
        detalhes: message,
      },
    });

    return {
      id: record.id,
      object_id: record.valor,
      user_id: record.userId,
      status: record.resultado,
      nfc_status: nfcStatus,
      message: record.detalhes,
      created_at: record.createdAt,
    };
  }

  async history() {
    const checks = await this.prisma.sherifCheck.findMany({
      orderBy: { createdAt: 'desc' },
    });

    return checks.map(c => ({
      id: c.id,
      objectId: c.valor,
      userId: c.userId,
      status: c.resultado,
      message: c.detalhes,
      date: new Date(c.createdAt).toLocaleString('pt-BR').substring(0, 16),
    }));
  }
}

