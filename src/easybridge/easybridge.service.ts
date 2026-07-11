import { Injectable } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';
import { UpdateProgressDto } from './dto/update-progress.dto';
import { CompleteLessonDto } from './dto/complete-lesson.dto';

@Injectable()
export class EasybridgeService {
  constructor(private readonly prisma: PrismaService) {}

  async getOrCreateProfile(userId: string) {
    let profile = await this.prisma.easyBridgeUser.findUnique({
      where: { userId },
    });

    if (!profile) {
      profile = await this.prisma.easyBridgeUser.create({
        data: { userId },
      });
    }

    return profile;
  }

  async getProgress(userId: string) {
    const profile = await this.getOrCreateProfile(userId);
    return {
      xp: profile.xp,
      level: profile.level,
      wordsLearned: profile.wordsLearned,
      quizzesDone: profile.quizzesDone,
      streakCurrent: profile.streakCurrent,
      streakLongest: profile.streakLongest,
      streakLastDate: profile.streakLastDate,
    };
  }

  async updateProgress(userId: string, dto: UpdateProgressDto) {
    const profile = await this.getOrCreateProfile(userId);

    return this.prisma.easyBridgeUser.update({
      where: { id: profile.id },
      data: {
        xp: dto.xp ?? profile.xp,
        level: dto.level ?? profile.level,
        wordsLearned: dto.wordsLearned ?? profile.wordsLearned,
        quizzesDone: dto.quizzesDone ?? profile.quizzesDone,
      },
    });
  }

  async completeLesson(userId: string, dto: CompleteLessonDto) {
    const profile = await this.getOrCreateProfile(userId);

    const existing = await this.prisma.easyBridgeLesson.findFirst({
      where: {
        easyBridgeUserId: profile.id,
        wordPt: dto.wordPt,
        wordEn: dto.wordEn,
      },
    });

    if (existing) {
      return { message: 'Lição já completada', lesson: existing };
    }

    const lesson = await this.prisma.easyBridgeLesson.create({
      data: {
        easyBridgeUserId: profile.id,
        categoryId: dto.categoryId,
        wordPt: dto.wordPt,
        wordEn: dto.wordEn,
      },
    });

    await this.prisma.easyBridgeUser.update({
      where: { id: profile.id },
      data: {
        wordsLearned: { increment: 1 },
        xp: { increment: 10 },
      },
    });

    return { message: 'Lição completada!', lesson };
  }

  async getLessons(userId: string) {
    const profile = await this.getOrCreateProfile(userId);

    return this.prisma.easyBridgeLesson.findMany({
      where: { easyBridgeUserId: profile.id },
      orderBy: { completedAt: 'desc' },
    });
  }

  async updateStreak(userId: string) {
    const profile = await this.getOrCreateProfile(userId);
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);

    let newCurrent = profile.streakCurrent;
    const lastDate = profile.streakLastDate
      ? new Date(profile.streakLastDate)
      : null;

    if (lastDate) {
      lastDate.setHours(0, 0, 0, 0);
    }

    if (lastDate && lastDate.getTime() === today.getTime()) {
      return {
        current: profile.streakCurrent,
        longest: profile.streakLongest,
        lastDate: profile.streakLastDate,
      };
    }

    if (lastDate && lastDate.getTime() === yesterday.getTime()) {
      newCurrent = profile.streakCurrent + 1;
    } else {
      newCurrent = 1;
    }

    const newLongest = Math.max(newCurrent, profile.streakLongest);

    const updated = await this.prisma.easyBridgeUser.update({
      where: { id: profile.id },
      data: {
        streakCurrent: newCurrent,
        streakLongest: newLongest,
        streakLastDate: today,
      },
    });

    return {
      current: updated.streakCurrent,
      longest: updated.streakLongest,
      lastDate: updated.streakLastDate,
    };
  }

  async getRanking() {
    const ranking = await this.prisma.easyBridgeUser.findMany({
      orderBy: { xp: 'desc' },
      take: 50,
      include: {
        user: {
          select: { name: true },
        },
      },
    });

    return ranking.map((r, index) => ({
      position: index + 1,
      name: r.user.name,
      xp: r.xp,
      level: r.level,
      wordsLearned: r.wordsLearned,
      streakCurrent: r.streakCurrent,
    }));
  }
}
