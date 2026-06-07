import { Injectable, BadRequestException } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';
import { IsString, IsOptional, IsNumber, IsBoolean } from 'class-validator';

export class SaveConfigDto {
  @IsString()
  @IsOptional()
  userId?: string;

  @IsString()
  @IsOptional()
  binanceApiKey?: string;

  @IsString()
  @IsOptional()
  binanceApiSecret?: string;

  @IsString()
  @IsOptional()
  symbol?: string;

  @IsNumber()
  @IsOptional()
  tradeAmount?: number;

  @IsBoolean()
  @IsOptional()
  isActive?: boolean;
}

export class RegisterTradeDto {
  @IsString()
  @IsOptional()
  userId?: string;

  @IsString()
  asset: string;

  @IsString()
  type: string; // "COMPRA" ou "VENDA"

  @IsNumber()
  price: number;

  @IsNumber()
  amount: number;

  @IsNumber()
  value: number;

  @IsString()
  @IsOptional()
  profitPct?: string;
}


@Injectable()
export class BotService {
  constructor(private readonly prisma: PrismaService) {}

  // Garante que o usuário existe no banco de dados local para satisfazer chaves estrangeiras
  private async ensureUserExists(userId: string): Promise<string> {
    const id = userId.trim() || 'guest';
    const existing = await this.prisma.user.findUnique({ where: { id } });
    if (!existing) {
      await this.prisma.user.create({
        data: {
          id,
          name: id === 'guest' ? 'Visitante' : 'Usuário ' + id,
          email: `${id}@anunciacerto.local`,
          password: 'nopassword_placeholder',
        },
      });
    }
    return id;
  }

  async getConfig(rawUserId?: string) {
    const userId = await this.ensureUserExists(rawUserId || 'guest');
    let config = await this.prisma.botConfig.findUnique({
      where: { userId },
    });

    if (!config) {
      config = await this.prisma.botConfig.create({
        data: {
          userId,
          symbol: 'SOL/USDT',
          tradeAmount: 12.0,
          isActive: false,
        },
      });
    }

    return config;
  }

  async saveConfig(dto: SaveConfigDto) {
    const userId = await this.ensureUserExists(dto.userId || 'guest');

    // Se estiver tentando ativar o robô, valida a assinatura (role == 'subscriber')
    if (dto.isActive === true) {
      const user = await this.prisma.user.findUnique({ where: { id: userId } });
      if (user && user.role !== 'subscriber' && userId !== 'guest') {
        throw new BadRequestException('Assinatura inativa. Ative sua licença via PIX no aplicativo.');
      }
    }

    const existing = await this.prisma.botConfig.findUnique({ where: { userId } });

    if (existing) {
      return this.prisma.botConfig.update({
        where: { userId },
        data: {
          binanceApiKey: dto.binanceApiKey !== undefined ? dto.binanceApiKey : existing.binanceApiKey,
          binanceApiSecret: dto.binanceApiSecret !== undefined ? dto.binanceApiSecret : existing.binanceApiSecret,
          symbol: dto.symbol !== undefined ? dto.symbol : existing.symbol,
          tradeAmount: dto.tradeAmount !== undefined ? dto.tradeAmount : existing.tradeAmount,
          isActive: dto.isActive !== undefined ? dto.isActive : existing.isActive,
        },
      });
    }

    return this.prisma.botConfig.create({
      data: {
        userId,
        binanceApiKey: dto.binanceApiKey || null,
        binanceApiSecret: dto.binanceApiSecret || null,
        symbol: dto.symbol || 'SOL/USDT',
        tradeAmount: dto.tradeAmount || 12.0,
        isActive: dto.isActive || false,
      },
    });
  }

  async registerTrade(dto: RegisterTradeDto) {
    const userId = await this.ensureUserExists(dto.userId || 'guest');
    
    if (!dto.asset || !dto.type || !dto.price || !dto.amount || !dto.value) {
      throw new BadRequestException('Campos obrigatórios ausentes para o registro de trade.');
    }

    return this.prisma.botTrade.create({
      data: {
        userId,
        asset: dto.asset,
        type: dto.type,
        price: Number(dto.price),
        amount: Number(dto.amount),
        value: Number(dto.value),
        profitPct: dto.profitPct || null,
      },
    });
  }

  async getTrades(rawUserId?: string, limit = 50) {
    const userId = await this.ensureUserExists(rawUserId || 'guest');
    return this.prisma.botTrade.findMany({
      where: { userId },
      take: Math.max(1, limit),
      orderBy: { createdAt: 'desc' },
    });
  }
}
