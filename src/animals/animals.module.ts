import { Module } from '@nestjs/common';
import { PrismaModule } from '../prisma/prisma.module';
import { AnimalsController, PublicAnimalsController } from './animals.controller';
import { AnimalsService } from './animals.service';

@Module({
  imports: [PrismaModule],
  controllers: [AnimalsController, PublicAnimalsController],
  providers: [AnimalsService],
  exports: [AnimalsService],
})
export class AnimalsModule {}
