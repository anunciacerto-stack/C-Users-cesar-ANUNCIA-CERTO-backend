import { Body, BadRequestException, Controller, Get, Param, Post, Query, Req } from '@nestjs/common';
import type { Request } from 'express';
import { NfcService } from './nfc.service';

@Controller('nfc')
export class NfcController {
  constructor(private readonly nfcService: NfcService) {}

  @Post('register')
  async register(@Body() body: Record<string, unknown>): Promise<any> {
    return this.nfcService.register(body);
  }

  @Post('update')
  async update(@Body() body: Record<string, unknown>): Promise<any> {
    return this.nfcService.update(body);
  }

  @Get('status/:objectId')
  async status(@Param('objectId') objectId: string): Promise<any> {
    if (!objectId?.trim()) {
      throw new BadRequestException('objectId is required');
    }
    return this.nfcService.getStatus(objectId.trim());
  }

  @Get('history')
  async history(@Query('limit') limit?: string): Promise<any> {
    const numericLimit = Number(limit);
    if (Number.isFinite(numericLimit) && numericLimit > 0) {
      return this.nfcService.getAll(Math.floor(numericLimit));
    }
    return this.nfcService.getAll();
  }

  @Get('scan/:tagId')
  async scan(@Param('tagId') tagId: string, @Req() req: Request): Promise<any> {
    if (!tagId?.trim()) {
      throw new BadRequestException('tagId is required');
    }
    const userAgent = req.headers['user-agent'] as string;
    const ipAddress = (req.headers['x-forwarded-for'] || req.socket.remoteAddress) as string;
    
    // Register the scan for analytics
    await this.nfcService.registerScan(tagId.trim(), userAgent, ipAddress);
    
    // Return a success message or redirect URL
    return { success: true, message: 'Scan registered successfully', tagId };
  }

  @Get('analytics/:tagId')
  async getAnalytics(@Param('tagId') tagId: string): Promise<any> {
    if (!tagId?.trim()) {
      throw new BadRequestException('tagId is required');
    }
    return this.nfcService.getAnalytics(tagId.trim());
  }

  @Get('resolve/:tagId')
  async resolve(@Param('tagId') tagId: string): Promise<any> {
    if (!tagId?.trim()) {
      throw new BadRequestException('tagId is required');
    }
    return this.nfcService.resolveTag(tagId.trim());
  }
}
