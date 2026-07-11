import {
  Body,
  Controller,
  Get,
  Post,
  Put,
  Req,
  UseGuards,
} from '@nestjs/common';
import { AuthGuard } from '@nestjs/passport';
import { Request } from 'express';
import { EasybridgeService } from './easybridge.service';
import { UpdateProgressDto } from './dto/update-progress.dto';
import { CompleteLessonDto } from './dto/complete-lesson.dto';

@Controller('easybridge')
@UseGuards(AuthGuard('jwt'))
export class EasybridgeController {
  constructor(private readonly easybridgeService: EasybridgeService) {}

  @Get('progress')
  getProgress(@Req() req: Request & { user: any }) {
    return this.easybridgeService.getProgress(req.user.id);
  }

  @Put('progress')
  updateProgress(
    @Req() req: Request & { user: any },
    @Body() dto: UpdateProgressDto,
  ) {
    return this.easybridgeService.updateProgress(req.user.id, dto);
  }

  @Post('lesson')
  completeLesson(
    @Req() req: Request & { user: any },
    @Body() dto: CompleteLessonDto,
  ) {
    return this.easybridgeService.completeLesson(req.user.id, dto);
  }

  @Get('lessons')
  getLessons(@Req() req: Request & { user: any }) {
    return this.easybridgeService.getLessons(req.user.id);
  }

  @Post('streak')
  updateStreak(@Req() req: Request & { user: any }) {
    return this.easybridgeService.updateStreak(req.user.id);
  }

  @Get('ranking')
  getRanking() {
    return this.easybridgeService.getRanking();
  }
}
