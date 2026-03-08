import { Module } from '@nestjs/common';
import { AppController } from './app.controller';
import { AppService } from './app.service';
import { AuthModule } from './auth/auth.module';
import { UsersModule } from './users/users.module';
import { MarketplaceModule } from './marketplace/marketplace.module';
import { PaymentsModule } from './payments/payments.module';
import { NfcModule } from './nfc/nfc.module';
import { SherifModule } from './sherif/sherif.module';
import { PrismaModule } from './prisma/prisma.module';

@Module({
  imports: [PrismaModule, AuthModule, UsersModule, MarketplaceModule, PaymentsModule, NfcModule, SherifModule],
  controllers: [AppController],
  providers: [AppService],
})
export class AppModule {}
