import { Module } from '@nestjs/common';
import { FormaturasController } from './formaturas.controller';
import { FormaturasService } from './formaturas.service';

@Module({
  controllers: [FormaturasController],
  providers: [FormaturasService]
})
export class FormaturasModule {}
