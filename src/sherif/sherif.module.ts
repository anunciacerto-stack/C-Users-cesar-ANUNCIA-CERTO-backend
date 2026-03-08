import { Module } from '@nestjs/common';
import { SherifController } from './sherif.controller';
import { SherifService } from './sherif.service';
import { NfcModule } from '../nfc/nfc.module';

@Module({
  imports: [NfcModule],
  controllers: [SherifController],
  providers: [SherifService],
})
export class SherifModule {}
