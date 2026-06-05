import { Inject, Injectable } from '@nestjs/common';
import { AI_PROVIDER_TOKEN } from './constants/ai-prompts';
import { AiAssistDto } from './dto/ai-assist.dto';
import { AiExplainDto } from './dto/ai-explain.dto';
import { AiSearchDto } from './dto/ai-search.dto';
import {
  type AiAssistResult,
  type AiExplainResult,
  type AiProvider,
  type AiSearchResult,
} from './providers/ai.provider';

@Injectable()
export class AiService {
  constructor(
    @Inject(AI_PROVIDER_TOKEN)
    private readonly provider: AiProvider,
  ) {}

  assist(input: AiAssistDto): Promise<AiAssistResult> {
    return this.provider.assist(input);
  }

  search(input: AiSearchDto): Promise<AiSearchResult> {
    return this.provider.search(input);
  }

  explain(input: AiExplainDto): Promise<AiExplainResult> {
    return this.provider.explain(input);
  }
}
