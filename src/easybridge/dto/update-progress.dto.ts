import { IsInt, IsOptional, Min } from 'class-validator';

export class UpdateProgressDto {
  @IsOptional()
  @IsInt()
  @Min(0)
  xp?: number;

  @IsOptional()
  @IsInt()
  @Min(0)
  level?: number;

  @IsOptional()
  @IsInt()
  @Min(0)
  wordsLearned?: number;

  @IsOptional()
  @IsInt()
  @Min(0)
  quizzesDone?: number;
}
