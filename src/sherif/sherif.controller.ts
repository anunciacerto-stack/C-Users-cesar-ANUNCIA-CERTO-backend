import { Body, Controller, Get, Post } from '@nestjs/common';
import { SherifService } from './sherif.service';

@Controller('sherif')
export class SherifController {
  constructor(private readonly sherifService: SherifService) {}

  @Post('check')
  check(@Body() body: Record<string, unknown>): any {
    return this.sherifService.check(body);
  }

  @Get('history')
  history(): any {
    return this.sherifService.history();
  }
}
