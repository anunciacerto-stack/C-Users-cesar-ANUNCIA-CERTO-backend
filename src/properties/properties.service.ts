import { BadRequestException, Injectable, NotFoundException } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';
import { CreatePropertyDto } from './dto/create-property.dto';

@Injectable()
export class PropertiesService {
  constructor(private readonly prisma: PrismaService) {}

  async create(dto: CreatePropertyDto) {
    await this.ensureOwnerExists(dto.ownerId);

    const publicCode = await this.generateUniquePublicCode('IMV', (code) =>
      this.prisma.propertyListing.findUnique({
        where: { publicCode: code },
        select: { id: true },
      }),
    );

    const property = await this.prisma.propertyListing.create({
      data: {
        title: dto.title.trim(),
        description: dto.description.trim(),
        propertyType: normalizeLabel(dto.propertyType),
        transactionType: normalizeLabel(dto.transactionType),
        price: dto.price,
        state: dto.state.trim().toUpperCase(),
        city: normalizeLabel(dto.city),
        neighborhood: optionalLabel(dto.neighborhood),
        address: optionalLabel(dto.address),
        cep: dto.cep?.trim(),
        bedrooms: dto.bedrooms,
        bathrooms: dto.bathrooms,
        parkingSpots: dto.parkingSpots,
        area: dto.area,
        images: dto.images ?? [],
        qrEnabled: dto.qrEnabled,
        nfcEnabled: dto.nfcEnabled,
        ownerId: dto.ownerId,
        publicCode,
      },
      select: propertySelect(),
    });

    return {
      ...property,
      publicUrl: this.buildPublicUrl(property.publicCode),
      aiHints: [
        'Futuro: melhorar descricao com IA.',
        'Futuro: explicar uso de QR/NFC no anuncio.',
      ],
    };
  }

  async findAll() {
    const properties = await this.prisma.propertyListing.findMany({
      orderBy: { createdAt: 'desc' },
      select: propertySelect(),
    });

    return properties.map((property) => ({
      ...property,
      publicUrl: this.buildPublicUrl(property.publicCode),
    }));
  }

  async findById(id: string) {
    const property = await this.prisma.propertyListing.findUnique({
      where: { id },
      select: propertySelect(),
    });

    if (!property) {
      throw new NotFoundException('Property listing not found');
    }

    return {
      ...property,
      publicUrl: this.buildPublicUrl(property.publicCode),
    };
  }

  async findByState(state: string) {
    const properties = await this.prisma.propertyListing.findMany({
      where: { state: { equals: state.trim().toUpperCase(), mode: 'insensitive' } },
      orderBy: { createdAt: 'desc' },
      select: propertySelect(),
    });

    return properties.map((property) => ({
      ...property,
      publicUrl: this.buildPublicUrl(property.publicCode),
    }));
  }

  async findByCity(city: string) {
    const properties = await this.prisma.propertyListing.findMany({
      where: { city: { equals: normalizeLabel(city), mode: 'insensitive' } },
      orderBy: { createdAt: 'desc' },
      select: propertySelect(),
    });

    return properties.map((property) => ({
      ...property,
      publicUrl: this.buildPublicUrl(property.publicCode),
    }));
  }

  async findByType(propertyType: string) {
    const properties = await this.prisma.propertyListing.findMany({
      where: { propertyType: { equals: normalizeLabel(propertyType), mode: 'insensitive' } },
      orderBy: { createdAt: 'desc' },
      select: propertySelect(),
    });

    return properties.map((property) => ({
      ...property,
      publicUrl: this.buildPublicUrl(property.publicCode),
    }));
  }

  async findPublicByCode(publicCode: string) {
    const property = await this.prisma.propertyListing.findUnique({
      where: { publicCode: publicCode.trim().toUpperCase() },
      select: publicPropertySelect(),
    });

    if (!property) {
      throw new NotFoundException('Property listing not found');
    }

    return {
      ...property,
      publicUrl: this.buildPublicUrl(property.publicCode),
    };
  }

  buildPublicUrl(publicCode: string) {
    return `/public/property/${publicCode}`;
  }

  private async ensureOwnerExists(ownerId: string) {
    const owner = await this.prisma.user.findUnique({
      where: { id: ownerId },
      select: { id: true },
    });

    if (!owner) {
      throw new BadRequestException('Owner user not found');
    }
  }

  private async generateUniquePublicCode(
    prefix: string,
    exists: (code: string) => Promise<{ id: string } | null>,
  ) {
    for (let attempt = 0; attempt < 10; attempt += 1) {
      const code = `${prefix}-${randomSegment()}`;
      const existing = await exists(code);
      if (!existing) {
        return code;
      }
    }

    throw new BadRequestException('Unable to generate a unique public code');
  }
}

function propertySelect() {
  return {
    id: true,
    ownerId: true,
    title: true,
    description: true,
    propertyType: true,
    transactionType: true,
    price: true,
    state: true,
    city: true,
    neighborhood: true,
    address: true,
    cep: true,
    bedrooms: true,
    bathrooms: true,
    parkingSpots: true,
    area: true,
    images: true,
    qrEnabled: true,
    nfcEnabled: true,
    publicCode: true,
    status: true,
    createdAt: true,
    updatedAt: true,
  };
}

function publicPropertySelect() {
  return {
    title: true,
    description: true,
    propertyType: true,
    transactionType: true,
    price: true,
    state: true,
    city: true,
    neighborhood: true,
    address: true,
    cep: true,
    bedrooms: true,
    bathrooms: true,
    parkingSpots: true,
    area: true,
    images: true,
    qrEnabled: true,
    nfcEnabled: true,
    publicCode: true,
    status: true,
    createdAt: true,
  };
}

function randomSegment() {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
  let result = '';
  for (let index = 0; index < 6; index += 1) {
    result += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return result;
}

function normalizeLabel(value: string) {
  return value
    .trim()
    .toLowerCase()
    .split(' ')
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

function optionalLabel(value?: string) {
  const cleaned = value?.trim();
  return cleaned ? normalizeLabel(cleaned) : null;
}
