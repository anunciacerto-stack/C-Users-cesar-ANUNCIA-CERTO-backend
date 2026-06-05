import { Module } from '@nestjs/common';
import { AiController } from './ai.controller';
import { AiService } from './ai.service';
import { AI_PROVIDER_TOKEN } from './constants/ai-prompts';
import { createAiProvider } from './providers/ai.provider';

@Module({
  controllers: [AiController],
  providers: [
    AiService,
    {
      provide: AI_PROVIDER_TOKEN,
      useFactory: createAiProvider,
    },
  ],
})
export class AiModule {}
