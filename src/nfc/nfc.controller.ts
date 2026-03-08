import { Body, BadRequestException, Controller, Get, Param, Post, Query } from '@nestjs/common';
import { NfcService } from './nfc.service';

@Controller('nfc')
export class NfcController {
  constructor(private readonly nfcService: NfcService) {}

  @Post('register')
  register(@Body() body: Record<string, unknown>): any {
    return this.nfcService.register(body);
  }

  @Post('update')
  update(@Body() body: Record<string, unknown>): any {
    return this.nfcService.update(body);
  }

  @Get('status/:objectId')
  status(@Param('objectId') objectId: string): any {
    if (!objectId?.trim()) {
      throw new BadRequestException('objectId is required');
    }
    return this.nfcService.getStatus(objectId.trim());
  }

  @Get('history')
  history(@Query('limit') limit?: string): any {
    const numericLimit = Number(limit);
    if (Number.isFinite(numericLimit) && numericLimit > 0) {
      return this.nfcService.getAll().slice(0, Math.floor(numericLimit));
    }
    return this.nfcService.getAll();
  }
}
