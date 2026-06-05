import { Body, Controller, Post } from '@nestjs/common';
import { AiService } from './ai.service';
import { AiAssistDto } from './dto/ai-assist.dto';
import { AiExplainDto } from './dto/ai-explain.dto';
import { AiSearchDto } from './dto/ai-search.dto';

@Controller('ai')
export class AiController {
  constructor(private readonly aiService: AiService) {}

  @Post('assist')
  async assist(@Body() dto: AiAssistDto) {
    const data = await this.aiService.assist(dto);
    return { data };
  }

  @Post('search')
  async search(@Body() dto: AiSearchDto) {
    const data = await this.aiService.search(dto);
    return { data };
  }

  @Post('explain')
  async explain(@Body() dto: AiExplainDto) {
    const data = await this.aiService.explain(dto);
    return { data };
  }
}
