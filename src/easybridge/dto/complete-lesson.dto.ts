import { IsNotEmpty, IsString } from 'class-validator';

export class CompleteLessonDto {
  @IsString()
  @IsNotEmpty()
  categoryId: string;

  @IsString()
  @IsNotEmpty()
  wordPt: string;

  @IsString()
  @IsNotEmpty()
  wordEn: string;
}
