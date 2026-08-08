import { BadRequestException, Injectable } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';
import { CreateListingDto } from './dto/create-listing.dto';

export type CategoryTree = Record<string, string[]>;

export interface CreateClassifiedInput {
  titulo: string;
  descricao: string;
  preco: number;
  categoria: string;
  cidade: string;
  estado: string;
  fotos?: string[];
  userId?: string;
}

export interface CreateMuralInput {
  assunto: string;
  conteudo: string;
  categoria: string;
  fotos?: string[];
  userId?: string;
}

export interface CreateDonationInput {
  titulo: string;
  descricao: string;
  categoria: string;
  cidade: string;
  estado: string;
  fotos?: string[];
  userId?: string;
}

@Injectable()
export class MarketplaceService {
  constructor(private readonly prisma: PrismaService) {}

  async createListing(dto: CreateListingDto) {
    const owner = await this.prisma.user.findUnique({
      where: { id: dto.ownerId },
      select: { id: true },
    });

    if (!owner) {
      throw new BadRequestException('Owner user not found');
    }

    return this.prisma.listing.create({
      data: {
        title: dto.title,
        description: dto.description,
        price: dto.price,
        category: dto.category,
        subcategory: dto.subcategory,
        state: dto.state,
        city: dto.city,
        images: dto.images,
        qrEnabled: dto.qrEnabled,
        nfcEnabled: dto.nfcEnabled,
        ownerId: dto.ownerId,
      },
      select: this.listingSelect(),
    });
  }

  listAllListings() {
    return this.prisma.listing.findMany({
      orderBy: { createdAt: 'desc' },
      select: this.listingSelect(),
    });
  }

  listByCategory(category: string) {
    return this.prisma.listing.findMany({
      where: { category: { equals: category, mode: 'insensitive' } },
      orderBy: { createdAt: 'desc' },
      select: this.listingSelect(),
    });
  }

  listByState(state: string) {
    return this.prisma.listing.findMany({
      where: { state: { equals: state, mode: 'insensitive' } },
      orderBy: { createdAt: 'desc' },
      select: this.listingSelect(),
    });
  }

  listByCity(city: string) {
    return this.prisma.listing.findMany({
      where: { city: { equals: city, mode: 'insensitive' } },
      orderBy: { createdAt: 'desc' },
      select: this.listingSelect(),
    });
  }

  getListingById(id: string) {
    return this.prisma.listing.findUnique({
      where: { id },
      select: this.listingSelect(),
    });
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

  private listingSelect() {
    return {
      id: true,
      title: true,
      description: true,
      price: true,
      category: true,
      subcategory: true,
      state: true,
      city: true,
      images: true,
      qrEnabled: true,
      nfcEnabled: true,
      ownerId: true,
      createdAt: true,
      owner: {
        select: {
          id: true,
          name: true,
          email: true,
          phone: true,
        },
      },
    };
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

  private async resolveUserId(userId?: string) {
    if (!userId) {
      return null;
    }

    const user = await this.prisma.user.findUnique({
      where: { id: userId },
      select: { id: true },
    });

    return user?.id ?? null;
  }

  async listUniversalProducts() {
    return this.prisma.universalProduct.findMany({
      orderBy: { name: 'asc' },
    });
  }

  async createUniversalProduct(data: {
    name: string;
    description?: string;
    price: number;
    category: string;
    image: string;
  }) {
    return this.prisma.universalProduct.create({
      data,
    });
  }

  async seedUniversalProducts() {
    await this.prisma.universalProduct.deleteMany();

    const products = [
      {
        name: "Arroz Camil 5kg",
        description: "Arroz agulhinha tipo 1 de excelente qualidade, perfeito para o dia a dia.",
        price: 22.90,
        category: "Grãos",
        image: "https://images.unsplash.com/photo-1586201375761-83865001e31c?w=500&auto=format&fit=crop&q=60"
      },
      {
        name: "Feijão Carioca Kicaldo 1kg",
        description: "Feijão carioca selecionado, tipo 1, caldo grosso e saboroso.",
        price: 8.49,
        category: "Grãos",
        image: "https://images.unsplash.com/photo-1551462147-ff29053bfc14?w=500&auto=format&fit=crop&q=60"
      },
      {
        name: "Leite Integral Italac 1L",
        description: "Leite UHT integral, rico em cálcio e vitaminas.",
        price: 5.29,
        category: "Laticínios",
        image: "https://images.unsplash.com/photo-1550583724-b2692b85b150?w=500&auto=format&fit=crop&q=60"
      },
      {
        name: "Café Pilão Vácuo 500g",
        description: "O café forte do Brasil, com torra e moagem intensas.",
        price: 14.90,
        category: "Bebidas",
        image: "https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?w=500&auto=format&fit=crop&q=60"
      },
      {
        name: "Sabão Líquido Omo 2L",
        description: "Sabão líquido concentrado para roupas, rende muito mais.",
        price: 27.90,
        category: "Limpeza",
        image: "https://images.unsplash.com/photo-1607613009820-a29f7bb81c04?w=500&auto=format&fit=crop&q=60"
      },
      {
        name: "Pão Francês Unidade",
        description: "Pão francês quentinho e crocante, assado na hora.",
        price: 0.75,
        category: "Padaria",
        image: "https://images.unsplash.com/photo-1509440159596-0249088772ff?w=500&auto=format&fit=crop&q=60"
      },
      {
        name: "Kit Churrasco Completo",
        description: "Contém 1kg de Picanha, 1kg de Linguiça Tosca, 1kg de Coxinha da Asa e Pão de Alho.",
        price: 149.90,
        category: "Açougue",
        image: "https://images.unsplash.com/photo-1544025162-d76694265947?w=500&auto=format&fit=crop&q=60"
      },
      {
        name: "Refrigerante Coca-Cola 2L",
        description: "Refrigerante de cola tradicional, sabor original gelado.",
        price: 9.90,
        category: "Bebidas",
        image: "https://images.unsplash.com/photo-1622483767028-3f66f32aef97?w=500&auto=format&fit=crop&q=60"
      },
      {
        name: "Cerveja Heineken Latão 473ml",
        description: "Cerveja puro malte holandesa premium gelada.",
        price: 6.50,
        category: "Bebidas",
        image: "https://images.unsplash.com/photo-1608270586620-248524c67de9?w=500&auto=format&fit=crop&q=60"
      },
      {
        name: "Azeite Carbonell Extra Virgem 500ml",
        description: "Azeite de oliva extra virgem importado da Espanha.",
        price: 34.90,
        category: "Óleos",
        image: "https://images.unsplash.com/photo-1474979266404-7eaacbcd87c5?w=500&auto=format&fit=crop&q=60"
      },
      {
        name: "Macarrão Barilla Espaguete 500g",
        description: "Macarrão de sêmola de trigo duro importado da Itália.",
        price: 9.70,
        category: "Massas",
        image: "https://images.unsplash.com/photo-1563379971899-660589a0163e?w=500&auto=format&fit=crop&q=60"
      },
      {
        name: "Sorvete Kibon Chocolate 1.5L",
        description: "Sorvete cremoso de chocolate tradicional Kibon.",
        price: 21.90,
        category: "Sobremesas",
        image: "https://images.unsplash.com/photo-1563805042-7684c019e1cb?w=500&auto=format&fit=crop&q=60"
      }
    ];

    return this.prisma.universalProduct.createMany({
      data: products
    });
  }
}

