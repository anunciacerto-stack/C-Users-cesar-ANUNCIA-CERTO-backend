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
  observation?: string;
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
    
    let targetType = input.targetType ?? 'general';
    if (objectIdInput.startsWith('veiculo:')) {
      targetType = 'veiculo';
    } else if (objectIdInput.startsWith('proprietario:')) {
      targetType = 'proprietario';
    } else if (objectIdInput.startsWith('wifi:')) {
      targetType = 'wifi';
    } else if (objectIdInput.startsWith('url:')) {
      targetType = 'url';
    } else if (objectIdInput.startsWith('text:')) {
      targetType = 'text';
    }

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
          ownerId: this.resolveOwnerId(userId) ?? existingTag.ownerId,
          observation: input.observation ?? existingTag.observation,
        },
      });
    }

    return this.prisma.nfcTag.create({
      data: {
        tagId,
        targetId: objectIdInput,
        targetType,
        ownerId: this.resolveOwnerId(userId),
        observation: input.observation,
      },
    });
  }

  async update(input: NfcUpdateInput) {
    const tagId = this.normalizeId(input.tagId ?? input.tag_id);
    const objectIdInput = this.normalizeId(input.objectId ?? input.object_id);
    const userId = this.normalizeUser(input.userId ?? input.user_id);
    const status = (input.status ?? '').trim();

    let targetType = input.targetType ?? 'general';
    if (objectIdInput.startsWith('veiculo:')) {
      targetType = 'veiculo';
    } else if (objectIdInput.startsWith('proprietario:')) {
      targetType = 'proprietario';
    } else if (objectIdInput.startsWith('wifi:')) {
      targetType = 'wifi';
    } else if (objectIdInput.startsWith('url:')) {
      targetType = 'url';
    } else if (objectIdInput.startsWith('text:')) {
      targetType = 'text';
    }

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
        targetType: targetType !== 'general' ? targetType : existingTag.targetType,
        ownerId: this.resolveOwnerId(userId) ?? existingTag.ownerId,
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

  /**
   * Valida se a string é um UUID v4 válido para uso como FK.
   * Strings como "usuario:anonimo" ou "system" não são UUIDs válidos.
   */
  private isValidUuid(value: string): boolean {
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    return uuidRegex.test(value);
  }

  /**
   * Resolve o ownerId para FK: retorna null se o userId não for UUID ou for 'system'.
   * Evita erro de FK no PostgreSQL com strings inválidas.
   */
  private resolveOwnerId(userId: string): string | null {
    if (userId === 'system' || !this.isValidUuid(userId)) {
      return null;
    }
    return userId;
  }

  async resolveTag(tagId: string) {
    const normalizedTagId = this.normalizeId(tagId);
    if (!normalizedTagId) {
      throw new BadRequestException('tagId is required');
    }

    let targetId = normalizedTagId;
    let targetType = 'unknown';

    // 1. Tenta buscar a tag pelo hardware tagId no banco
    const tag = await this.prisma.nfcTag.findUnique({ where: { tagId: normalizedTagId } });
    if (tag) {
      targetId = tag.targetId || '';
      targetType = (tag.targetType || 'unknown').toLowerCase().trim();
    } else {
      // Se não encontrou, talvez a própria string consultada seja o payload
      if (normalizedTagId.startsWith('veiculo:')) {
        targetType = 'veiculo';
      } else if (normalizedTagId.startsWith('proprietario:')) {
        targetType = 'proprietario';
      } else if (normalizedTagId.startsWith('wifi:')) {
        targetType = 'wifi';
      } else if (normalizedTagId.startsWith('url:')) {
        targetType = 'url';
      } else if (normalizedTagId.startsWith('text:')) {
        targetType = 'text';
      }
    }

    if (!targetId) {
      return { category: targetType, data: null };
    }

    // 2. Se o targetId começar com os prefixos estruturados, realiza o parsing inteligente
    if (targetId.startsWith('veiculo:')) {
      const content = targetId.substring(8); // remove 'veiculo:'
      const parts = content.split('|');
      const plate = parts[0] || 'Desconhecida';
      const model = parts[1] || 'Veículo';
      const color = parts[2] || 'Não informada';
      return {
        category: 'veiculo',
        data: {
          titulo: model,
          title: model,
          preco: null,
          price: null,
          categoria: 'Veículo',
          cidade: 'Placa: ' + plate,
          estado: 'Cor: ' + color,
          descricao: `Placa: ${plate}\nCor: ${color}`,
        }
      };
    }

    if (targetId.startsWith('proprietario:')) {
      const content = targetId.substring(13); // remove 'proprietario:'
      const parts = content.split('|');
      const name = parts[0] || 'Desconhecido';
      const email = parts[1] || 'Não informado';
      const phone = parts[2] || 'Não informado';
      return {
        category: 'proprietario',
        data: {
          nome: name,
          email: email,
          telefone: phone,
        }
      };
    }

    if (targetId.startsWith('wifi:')) {
      const content = targetId.substring(5); // remove 'wifi:'
      const parts = content.split(':');
      const ssid = parts[0] || 'Rede Sem Nome';
      const password = parts[1] || '';
      return {
        category: 'wifi',
        data: {
          rede: ssid,
          senha: password,
        }
      };
    }

    if (targetId.startsWith('url:')) {
      const url = targetId.substring(4);
      return {
        category: 'url',
        data: {
          link: url, observation: tag?.observation,
        }
      };
    }

    if (targetId.startsWith('text:')) {
      const text = targetId.substring(5);
      return {
        category: 'text',
        data: {
          conteudo: text, observation: tag?.observation,
        }
      };
    }

    // ─── Prefixos da Plataforma ANUNCIA CERTO NFC ──────────────────────────

    if (targetId.startsWith('imovel:') || targetId.startsWith('lotes:')) {
      const prefix = targetId.startsWith('imovel:') ? 'imovel:' : 'lotes:';
      const content = targetId.substring(prefix.length);
      const parts = content.split('|');
      const id = parts[0]?.trim() || 'ID';
      const detalhe1 = parts[1]?.trim() || '';
      const detalhe2 = parts[2]?.trim() || '';
      return {
        category: prefix === 'lotes:' ? 'lotes' : 'imovel',
        data: {
          titulo: `${id}${detalhe1 ? ' — ' + detalhe1 : ''}`,
          id_nfc: id,
          detalhe1,
          detalhe2,
          status: 'REGISTRADO',
        }
      };
    }

    if (targetId.startsWith('servico:')) {
      const content = targetId.substring(8);
      const parts = content.split('|');
      const id = parts[0]?.trim() || 'ID';
      const nome = parts[1]?.trim() || '';
      const descricao = parts[2]?.trim() || '';
      return {
        category: 'servico',
        data: {
          titulo: `${id}${nome ? ' — ' + nome : ''}`,
          id_nfc: id,
          descricao,
          status: 'REGISTRADO',
        }
      };
    }

    if (targetId.startsWith('empresa:')) {
      const content = targetId.substring(8);
      const parts = content.split('|');
      const id = parts[0]?.trim() || 'ID';
      const nome = parts[1]?.trim() || '';
      const cidade = parts[2]?.trim() || '';
      return {
        category: 'empresa',
        data: {
          titulo: `${id}${nome ? ' — ' + nome : ''}`,
          id_nfc: id,
          cidade,
          status: 'REGISTRADO',
        }
      };
    }

    if (targetId.startsWith('animal:') || targetId.startsWith('pet:')) {
      const prefix = targetId.startsWith('animal:') ? 'animal:' : 'pet:';
      const content = targetId.substring(prefix.length);
      const parts = content.split('|');
      const id = parts[0]?.trim() || 'ID';
      const nome = parts[1]?.trim() || '';
      const tipo = parts[2]?.trim() || '';
      return {
        category: 'pet',
        data: {
          titulo: `${id}${nome ? ' — ' + nome : ''}`,
          id_nfc: id,
          animalType: tipo,
          status: 'REGISTRADO',
        }
      };
    }

    if (targetId.startsWith('objetos:')) {
      const content = targetId.substring(8);
      const parts = content.split('|');
      const id = parts[0]?.trim() || 'ID';
      const descricao = parts[1]?.trim() || '';
      return {
        category: 'objetos',
        data: {
          titulo: `${id}${descricao ? ' — ' + descricao : ''}`,
          id_nfc: id,
          descricao,
          status: 'REGISTRADO',
        }
      };
    }

    if (targetId.startsWith('owner:') || targetId.startsWith('saude:')) {
      const prefix = targetId.startsWith('owner:') ? 'owner:' : 'saude:';
      const content = targetId.substring(prefix.length);
      const parts = content.split('|');
      const id = parts[0]?.trim() || 'ID';
      const modelo = parts[1]?.trim() || '';
      const cor = parts[2]?.trim() || '';
      return {
        category: 'veiculo',
        data: {
          titulo: `${id}${modelo ? ' — ' + modelo : ''}`,
          id_nfc: id,
          veiculo: modelo,
          cor,
          status: 'REGISTRADO',
        }
      };
    }


    // 3. Fallback para busca convencional de IDs no banco de dados para classificados, animais ou imóveis
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
      // Ignora erro de banco
    }

    return {
      category: targetType || 'unknown',
      data
    };
  }
}
