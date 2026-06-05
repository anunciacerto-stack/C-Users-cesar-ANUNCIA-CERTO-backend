import { Type } from 'class-transformer';
import { IsArray, IsBoolean, IsNotEmpty, IsNumber, IsString, IsUUID, Min } from 'class-validator';

export class CreateListingDto {
  @IsString()
  @IsNotEmpty()
  title!: string;

  @IsString()
  @IsNotEmpty()
  description!: string;

  @Type(() => Number)
  @IsNumber()
  @Min(0)
  price!: number;

  @IsString()
  @IsNotEmpty()
  category!: string;

  @IsString()
  @IsNotEmpty()
  subcategory!: string;

  @IsString()
  @IsNotEmpty()
  state!: string;

  @IsString()
  @IsNotEmpty()
  city!: string;

  @IsArray()
  @IsString({ each: true })
  images!: string[];

  @Type(() => Boolean)
  @IsBoolean()
  qrEnabled = false;

  @Type(() => Boolean)
  @IsBoolean()
  nfcEnabled = false;

  @IsUUID()
  ownerId!: string;
}
