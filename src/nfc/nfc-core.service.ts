import { BadRequestException, Injectable } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';

export interface NfcRegisterInput {
  tagId?: string;
  tag_id?: string;
  objectId?: string;
  object_id?: string;
  targetType?: string;
  userId?: string;
  user_id?: string;
}

export interface NfcUpdateInput extends NfcRegisterInput {
  status?: string;
}

@Injectable()
export class NfcCoreService {
  constructor(private readonly prisma: PrismaService) {}

  async register(input: NfcRegisterInput) {
    const tagId = this.normalizeId(input.tagId ?? input.tag_id);
    const objectIdInput = this.normalizeId(input.objectId ?? input.object_id);
    const userId = this.normalizeUser(input.userId ?? input.user_id);
    const targetType = input.targetType ?? 'general';

    if (!tagId) {
      throw new BadRequestException('tagId is required');
    }

    const existingTag = await this.prisma.nfcTag.findUnique({ where: { tagId } });

    if (existingTag) {
      return this.prisma.nfcTag.update({
        where: { tagId },
        data: {
          targetId: objectIdInput || existingTag.targetId,
          targetType,
          ownerId: userId !== 'system' ? userId : existingTag.ownerId,
        },
      });
    }

    return this.prisma.nfcTag.create({
      data: {
        tagId,
        targetId: objectIdInput,
        targetType,
        ownerId: userId !== 'system' ? userId : null,
      },
    });
  }

  async update(input: NfcUpdateInput) {
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

    const existingTag = await this.prisma.nfcTag.findUnique({ where: { tagId } });

    if (!existingTag) {
      throw new BadRequestException('NFC tag not found');
    }

    return this.prisma.nfcTag.update({
      where: { tagId },
      data: {
        status,
        targetId: objectIdInput || existingTag.targetId,
        ownerId: userId !== 'system' ? userId : existingTag.ownerId,
      },
    });
  }

  async getStatus(objectId: string) {
    const normalizedObjectId = this.normalizeId(objectId);
    if (!normalizedObjectId) {
      return 'UNKNOWN';
    }
    const tag = await this.prisma.nfcTag.findFirst({
      where: { targetId: normalizedObjectId },
    });
    return tag?.status ?? 'UNKNOWN';
  }

  async history(limit = 100) {
    return this.prisma.nfcTag.findMany({
      take: Math.max(1, limit),
      orderBy: { updatedAt: 'desc' },
      include: {
        owner: { select: { name: true, email: true } }
      }
    });
  }

  async registerScan(tagId: string, userAgent?: string, ipAddress?: string) {
    const tag = await this.prisma.nfcTag.findUnique({ where: { tagId } });
    if (!tag) {
      throw new BadRequestException('NFC tag not found');
    }
    return this.prisma.nfcScan.create({
      data: {
        tagId,
        userAgent,
        ipAddress,
      },
    });
  }

  async getAnalytics(tagId: string) {
    const tag = await this.prisma.nfcTag.findUnique({ where: { tagId } });
    if (!tag) {
      throw new BadRequestException('NFC tag not found');
    }

    const totalScans = await this.prisma.nfcScan.count({ where: { tagId } });
    
    const recentScans = await this.prisma.nfcScan.findMany({
      where: { tagId },
      orderBy: { scannedAt: 'desc' },
      take: 100,
    });

    return {
      tagId: tag.tagId,
      targetId: tag.targetId,
      status: tag.status,
      totalScans,
      recentScans,
    };
  }

  private normalizeId(value?: string): string {
    return (value ?? '').trim();
  }

  private normalizeUser(value?: string): string {
    const userId = (value ?? '').trim();
    return userId || 'system';
  }

  async resolveTag(tagId: string) {
    const normalizedTagId = this.normalizeId(tagId);
    if (!normalizedTagId) {
      throw new BadRequestException('tagId is required');
    }

    const tag = await this.prisma.nfcTag.findUnique({ where: { tagId: normalizedTagId } });
    if (!tag) {
      return { category: 'unknown', data: null };
    }

    const targetId = tag.targetId;
    const targetType = (tag.targetType ?? '').toLowerCase().trim();

    if (!targetId) {
      return { category: targetType || 'unknown', data: null };
    }

    let data: any = null;

    try {
      if (targetType === 'veiculo' || targetType === 'classified' || targetType === 'veiculos') {
        const numericId = parseInt(targetId, 10);
        if (!isNaN(numericId)) {
          data = await this.prisma.classified.findUnique({ where: { id: numericId } });
        }
      } else if (targetType === 'pet' || targetType === 'animal' || targetType === 'pets') {
        data = await this.prisma.animalListing.findUnique({ where: { id: targetId } });
      } else if (targetType === 'imovel' || targetType === 'property' || targetType === 'imoveis') {
        data = await this.prisma.propertyListing.findUnique({ where: { id: targetId } });
      } else {
        const numericId = parseInt(targetId, 10);
        if (!isNaN(numericId)) {
          data = await this.prisma.classified.findUnique({ where: { id: numericId } });
          if (data) return { category: 'veiculo', data };
        }
        data = await this.prisma.animalListing.findUnique({ where: { id: targetId } });
        if (data) return { category: 'pet', data };

        data = await this.prisma.propertyListing.findUnique({ where: { id: targetId } });
        if (data) return { category: 'imovel', data };
      }
    } catch (e) {
      // Ignora erro
    }

    return {
      category: targetType || 'unknown',
      data
    };
  }
}
