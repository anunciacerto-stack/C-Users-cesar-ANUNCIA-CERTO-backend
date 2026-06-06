import { Body, Controller, Get, Post, Query } from '@nestjs/common';
import { BotService, SaveConfigDto, RegisterTradeDto } from './bot.service';

@Controller('bot')
export class BotController {
  constructor(private readonly botService: BotService) {}

  @Get('config')
  async getConfig(@Query('userId') userId?: string) {
    console.log(`[GET /bot/config] Query userId: ${userId}`);
    try {
      const result = await this.botService.getConfig(userId);
      console.log(`[GET /bot/config] Success: isActive=${result.isActive}`);
      return result;
    } catch (err) {
      console.error(`[GET /bot/config] Error:`, err);
      throw err;
    }
  }

  @Post('config')
  async saveConfig(@Body() body: SaveConfigDto) {
    console.log(`[POST /bot/config] Body:`, JSON.stringify(body));
    try {
      const result = await this.botService.saveConfig(body);
      console.log(`[POST /bot/config] Success: isActive=${result.isActive}`);
      return result;
    } catch (err) {
      console.error(`[POST /bot/config] Error:`, err);
      throw err;
    }
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
