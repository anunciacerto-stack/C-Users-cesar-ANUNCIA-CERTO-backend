import { Module } from '@nestjs/common';
import { AiModule } from './ai/ai.module';
import { AnimalsModule } from './animals/animals.module';
import { AppController } from './app.controller';
import { AppService } from './app.service';
import { AuthModule } from './auth/auth.module';
import { UsersModule } from './users/users.module';
import { MarketplaceModule } from './marketplace/marketplace.module';
import { PaymentsModule } from './payments/payments.module';
import { NfcModule } from './nfc/nfc.module';
import { SherifModule } from './sherif/sherif.module';
import { PrismaModule } from './prisma/prisma.module';
import { ProfilesModule } from './profiles/profiles.module';
import { PropertiesModule } from './properties/properties.module';
import { BotModule } from './bot/bot.module';

@Module({
  imports: [
    PrismaModule,
    AuthModule,
    UsersModule,
    MarketplaceModule,
    PaymentsModule,
    NfcModule,
    SherifModule,
    ProfilesModule,
    AiModule,
    PropertiesModule,
    AnimalsModule,
    BotModule,
  ],
  controllers: [AppController],
  providers: [AppService],
})
export class AppModule {}
