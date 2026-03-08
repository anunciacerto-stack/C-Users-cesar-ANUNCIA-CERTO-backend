import { Module } from '@nestjs/common';
import { NfcController } from './nfc.controller';
import { NfcService } from './nfc.service';
import { NfcCoreService } from './nfc-core.service';

@Module({
  controllers: [NfcController],
  providers: [NfcCoreService, NfcService],
  exports: [NfcCoreService, NfcService],
})
export class NfcModule {}
