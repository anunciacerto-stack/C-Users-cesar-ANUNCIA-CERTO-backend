import { Module } from '@nestjs/common';
import { NfcController } from './nfc.controller';
import { NfcService } from './nfc.service';
import { NfcCoreService } from './nfc-core.service';
import { PrismaModule } from '../prisma/prisma.module';

@Module({
  imports: [PrismaModule],
  controllers: [NfcController],
  providers: [NfcCoreService, NfcService],
  exports: [NfcCoreService, NfcService],
})
export class NfcModule {}
