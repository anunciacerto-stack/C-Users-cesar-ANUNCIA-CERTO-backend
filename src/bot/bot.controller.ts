import { Body, Controller, Get, Post, Query } from '@nestjs/common';
import { BotService, SaveConfigDto, RegisterTradeDto } from './bot.service';

@Controller('bot')
export class BotController {
  constructor(private readonly botService: BotService) {}

  @Get('config')
  async getConfig(@Query('userId') userId?: string) {
    return this.botService.getConfig(userId);
  }

  @Post('config')
  async saveConfig(@Body() body: SaveConfigDto) {
    return this.botService.saveConfig(body);
  }

  @Post('trades')
  async registerTrade(@Body() body: RegisterTradeDto) {
    return this.botService.registerTrade(body);
  }

  @Get('trades')
  async getTrades(
    @Query('userId') userId?: string,
    @Query('limit') limit?: string,
  ) {
    const parsedLimit = limit ? parseInt(limit, 10) : 50;
    return this.botService.getTrades(userId, parsedLimit);
  }
}
