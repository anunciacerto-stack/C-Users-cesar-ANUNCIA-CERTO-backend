import { IsNotEmpty, IsOptional, IsString, MaxLength } from 'class-validator';

export class AiSearchDto {
  @IsString()
  @IsNotEmpty()
  @MaxLength(300)
  query!: string;

  @IsString()
  @IsOptional()
  @MaxLength(80)
  context?: string;
}
