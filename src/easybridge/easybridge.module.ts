import { Module } from '@nestjs/common';
import { EasybridgeController } from './easybridge.controller';
import { EasybridgeService } from './easybridge.service';
import { PrismaModule } from '../prisma/prisma.module';

@Module({
  imports: [PrismaModule],
  controllers: [EasybridgeController],
  providers: [EasybridgeService],
})
export class EasybridgeModule {}
