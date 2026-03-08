import { Injectable } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';

export type CategoryTree = Record<string, string[]>;

export interface CreateClassifiedInput {
  titulo: string;
  descricao: string;
  preco: number;
  categoria: string;
  cidade: string;
  estado: string;
  fotos?: string[];
  userId?: number;
}

export interface CreateMuralInput {
  assunto: string;
  conteudo: string;
  categoria: string;
  fotos?: string[];
  userId?: number;
}

export interface CreateDonationInput {
  titulo: string;
  descricao: string;
  categoria: string;
  cidade: string;
  estado: string;
  fotos?: string[];
  userId?: number;
}

@Injectable()
export class MarketplaceService {
  constructor(private readonly prisma: PrismaService) {}

  getStatus() {
    return { status: 'marketplace module working' };
  }

  async getCategories() {
    await this.ensureDefaultCategories();

    const categories = await this.prisma.category.findMany({
      orderBy: [{ parentId: 'asc' }, { id: 'asc' }],
    });

    const tree: CategoryTree = {};

    for (const category of categories) {
      if (category.parentId === null) {
        tree[category.nome] = [];
      }
    }

    for (const category of categories) {
      if (category.parentId !== null) {
        const parent = categories.find((item) => item.id === category.parentId);
        if (parent && tree[parent.nome]) {
          tree[parent.nome].push(category.nome);
        }
      }
    }

    return tree;
  }

  async createClassified(input: CreateClassifiedInput) {
    return this.prisma.classified.create({
      data: {
        titulo: input.titulo,
        descricao: input.descricao,
        preco: Number(input.preco),
        categoria: input.categoria,
        cidade: input.cidade,
        estado: input.estado,
        fotos: input.fotos ?? [],
        userId: await this.resolveUserId(input.userId),
      },
    });
  }

  async listClassifieds() {
    return this.prisma.classified.findMany({
      orderBy: { created_at: 'desc' },
    });
  }

  async getClassifiedById(id: number) {
    return this.prisma.classified.findUnique({
      where: { id },
    });
  }

  async deleteClassified(id: number) {
    const existing = await this.prisma.classified.findUnique({
      where: { id },
    });

    if (!existing) {
      return null;
    }

    return this.prisma.classified.delete({
      where: { id },
    });
  }

  async createMuralPost(input: CreateMuralInput) {
    return this.prisma.muralPost.create({
      data: {
        assunto: input.assunto,
        conteudo: input.conteudo,
        categoria: input.categoria,
        fotos: input.fotos ?? [],
        userId: await this.resolveUserId(input.userId),
      },
    });
  }

  async listMuralPosts() {
    return this.prisma.muralPost.findMany({
      orderBy: { created_at: 'desc' },
    });
  }

  async createDonation(input: CreateDonationInput) {
    return this.prisma.donation.create({
      data: {
        titulo: input.titulo,
        descricao: input.descricao,
        categoria: input.categoria,
        cidade: input.cidade,
        estado: input.estado,
        fotos: input.fotos ?? [],
        userId: await this.resolveUserId(input.userId),
      },
    });
  }

  async listDonations() {
    return this.prisma.donation.findMany({
      orderBy: { created_at: 'desc' },
    });
  }

  private async ensureDefaultCategories() {
    const count = await this.prisma.category.count();
    if (count > 0) {
      return;
    }

    const animal = await this.prisma.category.create({
      data: { nome: 'animal' },
    });

    const veiculos = await this.prisma.category.create({
      data: { nome: 'veiculos' },
    });

    await this.prisma.category.createMany({
      data: [
        { nome: 'gato', parentId: animal.id },
        { nome: 'cachorro', parentId: animal.id },
        { nome: 'cabra', parentId: animal.id },
        { nome: 'cavalo', parentId: animal.id },
        { nome: 'boi', parentId: animal.id },
        { nome: 'moto', parentId: veiculos.id },
        { nome: 'carro', parentId: veiculos.id },
        { nome: 'caminhao', parentId: veiculos.id },
      ],
    });
  }

  private async resolveUserId(userId?: number) {
    if (!userId) {
      return null;
    }

    const user = await this.prisma.user.findUnique({
      where: { id: userId },
      select: { id: true },
    });

    return user?.id ?? null;
  }
}
