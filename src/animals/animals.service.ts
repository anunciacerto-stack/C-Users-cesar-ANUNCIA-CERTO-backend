import { BadRequestException, Injectable, NotFoundException } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';
import { CreateAnimalDto } from './dto/create-animal.dto';

@Injectable()
export class AnimalsService {
  constructor(private readonly prisma: PrismaService) {}

  async create(dto: CreateAnimalDto) {
    await this.ensureOwnerExists(dto.ownerId);

    const publicCode = await this.generateUniquePublicCode('ANI', (code) =>
      this.prisma.animalListing.findUnique({
        where: { publicCode: code },
        select: { id: true },
      }),
    );

    const animal = await this.prisma.animalListing.create({
      data: {
        title: dto.title.trim(),
        description: dto.description.trim(),
        animalType: normalizeLabel(dto.animalType),
        breed: optionalLabel(dto.breed),
        sex: optionalLabel(dto.sex),
        age: dto.age?.trim() || null,
        weight: dto.weight,
        price: dto.price,
        state: dto.state.trim().toUpperCase(),
        city: normalizeLabel(dto.city),
        tags: sanitizeTags(dto.tags),
        images: dto.images ?? [],
        qrEnabled: dto.qrEnabled,
        nfcEnabled: dto.nfcEnabled,
        ownerId: dto.ownerId,
        publicCode,
      },
      select: animalSelect(),
    });

    return {
      ...animal,
      publicUrl: this.buildPublicUrl(animal.publicCode),
      aiHints: [
        'Futuro: melhorar descricao com IA.',
        'Futuro: explicar rastreabilidade NFC/QR do animal.',
      ],
    };
  }

  async findAll() {
    const animals = await this.prisma.animalListing.findMany({
      orderBy: { createdAt: 'desc' },
      select: animalSelect(),
    });

    return animals.map((animal) => ({
      ...animal,
      publicUrl: this.buildPublicUrl(animal.publicCode),
    }));
  }

  async findById(id: string) {
    const animal = await this.prisma.animalListing.findUnique({
      where: { id },
      select: animalSelect(),
    });

    if (!animal) {
      throw new NotFoundException('Animal listing not found');
    }

    return {
      ...animal,
      publicUrl: this.buildPublicUrl(animal.publicCode),
    };
  }

  async findByState(state: string) {
    const animals = await this.prisma.animalListing.findMany({
      where: { state: { equals: state.trim().toUpperCase(), mode: 'insensitive' } },
      orderBy: { createdAt: 'desc' },
      select: animalSelect(),
    });

    return animals.map((animal) => ({
      ...animal,
      publicUrl: this.buildPublicUrl(animal.publicCode),
    }));
  }

  async findByCity(city: string) {
    const animals = await this.prisma.animalListing.findMany({
      where: { city: { equals: normalizeLabel(city), mode: 'insensitive' } },
      orderBy: { createdAt: 'desc' },
      select: animalSelect(),
    });

    return animals.map((animal) => ({
      ...animal,
      publicUrl: this.buildPublicUrl(animal.publicCode),
    }));
  }

  async findByType(animalType: string) {
    const animals = await this.prisma.animalListing.findMany({
      where: { animalType: { equals: normalizeLabel(animalType), mode: 'insensitive' } },
      orderBy: { createdAt: 'desc' },
      select: animalSelect(),
    });

    return animals.map((animal) => ({
      ...animal,
      publicUrl: this.buildPublicUrl(animal.publicCode),
    }));
  }

  async findPublicByCode(publicCode: string) {
    const animal = await this.prisma.animalListing.findUnique({
      where: { publicCode: publicCode.trim().toUpperCase() },
      select: publicAnimalSelect(),
    });

    if (!animal) {
      throw new NotFoundException('Animal listing not found');
    }

    return {
      ...animal,
      publicUrl: this.buildPublicUrl(animal.publicCode),
    };
  }

  buildPublicUrl(publicCode: string) {
    return `/public/animal/${publicCode}`;
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

function animalSelect() {
  return {
    id: true,
    ownerId: true,
    title: true,
    description: true,
    animalType: true,
    breed: true,
    sex: true,
    age: true,
    weight: true,
    price: true,
    state: true,
    city: true,
    tags: true,
    images: true,
    qrEnabled: true,
    nfcEnabled: true,
    publicCode: true,
    status: true,
    createdAt: true,
    updatedAt: true,
  };
}

function publicAnimalSelect() {
  return {
    title: true,
    description: true,
    animalType: true,
    breed: true,
    sex: true,
    age: true,
    weight: true,
    price: true,
    state: true,
    city: true,
    tags: true,
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

function sanitizeTags(tags: string[]) {
  return Array.from(
    new Set(
      (tags ?? [])
        .map((tag) => tag.trim().toLowerCase())
        .filter((tag) => tag.length > 0),
    ),
  );
}
