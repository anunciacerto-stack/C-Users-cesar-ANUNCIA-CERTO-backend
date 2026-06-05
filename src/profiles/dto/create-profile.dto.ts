import { Type } from 'class-transformer';
import { IsBoolean, IsEmail, IsIn, IsOptional, IsString, MaxLength } from 'class-validator';
import {
  ENTRY_TYPES,
  MAIN_CATEGORIES,
  PLAN_OPTIONS,
  STATUS_OPTIONS,
  SUBCATEGORIES_BY_MAIN,
} from '../../constants/categories';

const allSubcategories = Object.values(SUBCATEGORIES_BY_MAIN).flat();

export class CreateProfileDto {
  @IsString()
  @IsIn(ENTRY_TYPES)
  tipoEntrada!: (typeof ENTRY_TYPES)[number];

  @IsString()
  @IsIn(MAIN_CATEGORIES)
  categoriaPrincipal!: (typeof MAIN_CATEGORIES)[number];

  @IsString()
  @IsIn(allSubcategories)
  subcategoria!: string;

  @IsString()
  @MaxLength(120)
  titulo!: string;

  @IsString()
  @MaxLength(2000)
  descricao!: string;

  @IsOptional()
  @IsString()
  telefone?: string;

  @IsOptional()
  @IsString()
  whatsapp?: string;

  @IsOptional()
  @IsEmail()
  emailContato?: string;

  @IsOptional()
  @IsString()
  facebook?: string;

  @IsOptional()
  @IsString()
  instagram?: string;

  @IsString()
  @MaxLength(2)
  estado!: string;

  @IsString()
  cidade!: string;

  @IsOptional()
  @IsString()
  bairro?: string;

  @IsOptional()
  @IsString()
  endereco?: string;

  @IsOptional()
  @IsString()
  cep?: string;

  @Type(() => Boolean)
  @IsBoolean()
  destaque = false;

  @IsString()
  @IsIn(PLAN_OPTIONS)
  plano: (typeof PLAN_OPTIONS)[number] = 'base';

  @Type(() => Boolean)
  @IsBoolean()
  qrEnabled = false;

  @Type(() => Boolean)
  @IsBoolean()
  nfcEnabled = false;

  @IsString()
  @IsIn(STATUS_OPTIONS)
  status: (typeof STATUS_OPTIONS)[number] = 'ativo';
}
