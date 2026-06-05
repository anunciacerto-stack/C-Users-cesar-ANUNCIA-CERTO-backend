import { BadRequestException, Injectable } from '@nestjs/common';
import {
  DROPDOWN_FIELDS,
  ENTRY_TYPES,
  MAIN_CATEGORIES,
  PLAN_OPTIONS,
  STATUS_OPTIONS,
  SUBCATEGORIES_BY_MAIN,
} from '../constants/categories';
import { CITIES_BY_STATE } from '../constants/cities-by-state';
import { BRAZIL_STATES } from '../constants/states';
import { PrismaService } from '../prisma/prisma.service';
import { CreateProfileDto } from './dto/create-profile.dto';

@Injectable()
export class ProfilesService {
  constructor(private readonly prisma: PrismaService) {}

  async create(dto: CreateProfileDto) {
    const normalizedState = dto.estado.trim().toUpperCase();

    const stateExists = BRAZIL_STATES.some((state) => state.sigla === normalizedState);
    if (!stateExists) {
      throw new BadRequestException('Estado invalido');
    }

    const subcategories = SUBCATEGORIES_BY_MAIN[dto.categoriaPrincipal] ?? [];
    if (!subcategories.includes(dto.subcategoria)) {
      throw new BadRequestException('Subcategoria invalida para a categoria principal informada');
    }

    return this.prisma.listingProfile.create({
      data: {
        ...dto,
        estado: normalizedState,
      },
      select: {
        id: true,
        tipoEntrada: true,
        categoriaPrincipal: true,
        subcategoria: true,
        titulo: true,
        cidade: true,
        estado: true,
        plano: true,
        status: true,
        createdAt: true,
        updatedAt: true,
      },
    });
  }

  getOptions(estado?: string) {
    const normalizedState = estado?.trim().toUpperCase();

    return {
      dropdownFields: DROPDOWN_FIELDS,
      tipoEntrada: ENTRY_TYPES,
      categoriaPrincipal: MAIN_CATEGORIES,
      subcategorias: SUBCATEGORIES_BY_MAIN,
      plano: PLAN_OPTIONS,
      status: STATUS_OPTIONS,
      estados: BRAZIL_STATES,
      cidades: normalizedState ? CITIES_BY_STATE[normalizedState] ?? [] : CITIES_BY_STATE,
    };
  }
}
