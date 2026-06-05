import { IsNotEmpty, IsOptional, IsString, MaxLength } from 'class-validator';

export class AiExplainDto {
  @IsString()
  @IsNotEmpty()
  @MaxLength(80)
  topic!: string;

  @IsString()
  @IsOptional()
  @MaxLength(80)
  context?: string;
}
