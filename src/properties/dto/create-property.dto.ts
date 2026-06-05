import { Type } from 'class-transformer';
import {
  IsArray,
  IsBoolean,
  IsNotEmpty,
  IsNumber,
  IsOptional,
  IsString,
  IsUUID,
  MaxLength,
  Min,
} from 'class-validator';

export class CreatePropertyDto {
  @IsString()
  @IsNotEmpty()
  @MaxLength(160)
  title!: string;

  @IsString()
  @IsNotEmpty()
  @MaxLength(3000)
  description!: string;

  @IsString()
  @IsNotEmpty()
  @MaxLength(80)
  propertyType!: string;

  @IsString()
  @IsNotEmpty()
  @MaxLength(80)
  transactionType!: string;

  @Type(() => Number)
  @IsNumber()
  @Min(0)
  price!: number;

  @IsString()
  @IsNotEmpty()
  @MaxLength(2)
  state!: string;

  @IsString()
  @IsNotEmpty()
  @MaxLength(120)
  city!: string;

  @IsString()
  @IsOptional()
  @MaxLength(120)
  neighborhood?: string;

  @IsString()
  @IsOptional()
  @MaxLength(180)
  address?: string;

  @IsString()
  @IsOptional()
  @MaxLength(12)
  cep?: string;

  @Type(() => Number)
  @IsOptional()
  @IsNumber()
  @Min(0)
  bedrooms?: number;

  @Type(() => Number)
  @IsOptional()
  @IsNumber()
  @Min(0)
  bathrooms?: number;

  @Type(() => Number)
  @IsOptional()
  @IsNumber()
  @Min(0)
  parkingSpots?: number;

  @Type(() => Number)
  @IsOptional()
  @IsNumber()
  @Min(0)
  area?: number;

  @IsArray()
  @IsString({ each: true })
  images: string[] = [];

  @Type(() => Boolean)
  @IsBoolean()
  qrEnabled = false;

  @Type(() => Boolean)
  @IsBoolean()
  nfcEnabled = false;

  @IsUUID()
  ownerId!: string;
}
