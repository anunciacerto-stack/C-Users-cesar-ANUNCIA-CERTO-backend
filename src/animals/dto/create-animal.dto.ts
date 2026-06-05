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

export class CreateAnimalDto {
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
  animalType!: string;

  @IsString()
  @IsOptional()
  @MaxLength(80)
  breed?: string;

  @IsString()
  @IsOptional()
  @MaxLength(30)
  sex?: string;

  @IsString()
  @IsOptional()
  @MaxLength(40)
  age?: string;

  @Type(() => Number)
  @IsOptional()
  @IsNumber()
  @Min(0)
  weight?: number;

  @Type(() => Number)
  @IsOptional()
  @IsNumber()
  @Min(0)
  price?: number;

  @IsString()
  @IsNotEmpty()
  @MaxLength(2)
  state!: string;

  @IsString()
  @IsNotEmpty()
  @MaxLength(120)
  city!: string;

  @IsArray()
  @IsString({ each: true })
  tags: string[] = [];

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
