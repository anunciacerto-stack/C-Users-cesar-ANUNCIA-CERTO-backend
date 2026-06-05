import { IsOptional, IsString, MaxLength } from 'class-validator';

export class AiAssistDto {
  @IsString()
  @IsOptional()
  @MaxLength(60)
  context?: string;

  @IsString()
  @IsOptional()
  @MaxLength(160)
  title?: string;

  @IsString()
  @IsOptional()
  @MaxLength(2000)
  description?: string;

  @IsString()
  @IsOptional()
  @MaxLength(80)
  category?: string;

  @IsString()
  @IsOptional()
  @MaxLength(80)
  subcategory?: string;

  @IsString()
  @IsOptional()
  @MaxLength(80)
  tipoEntrada?: string;

  @IsString()
  @IsOptional()
  @MaxLength(2)
  state?: string;

  @IsString()
  @IsOptional()
  @MaxLength(120)
  city?: string;
}
