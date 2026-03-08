import {
  Body,
  Controller,
  Delete,
  Get,
  NotFoundException,
  Param,
  ParseIntPipe,
  Post,
} from '@nestjs/common';
import { MarketplaceService } from './marketplace.service';

@Controller('marketplace')
export class MarketplaceController {
  constructor(private readonly marketplaceService: MarketplaceService) {}

  @Get()
  getStatus() {
    return this.marketplaceService.getStatus();
  }

  @Get('categories')
  async getCategories() {
    return this.marketplaceService.getCategories();
  }

  @Post('classifieds')
  async createClassified(
    @Body()
    body: {
      titulo: string;
      descricao: string;
      preco: number;
      categoria: string;
      cidade: string;
      estado: string;
      fotos?: string[];
      userId?: number;
    },
  ) {
    return this.marketplaceService.createClassified(body);
  }

  @Get('classifieds')
  async listClassifieds() {
    return this.marketplaceService.listClassifieds();
  }

  @Get('classifieds/:id')
  async getClassifiedById(@Param('id', ParseIntPipe) id: number) {
    const item = await this.marketplaceService.getClassifiedById(id);
    if (!item) {
      throw new NotFoundException('Classified not found');
    }
    return item;
  }

  @Delete('classifieds/:id')
  async deleteClassified(@Param('id', ParseIntPipe) id: number) {
    const deleted = await this.marketplaceService.deleteClassified(id);
    if (!deleted) {
      throw new NotFoundException('Classified not found');
    }
    return deleted;
  }

  @Post('mural')
  async createMuralPost(
    @Body()
    body: {
      assunto: string;
      conteudo: string;
      categoria: string;
      fotos?: string[];
      userId?: number;
    },
  ) {
    return this.marketplaceService.createMuralPost(body);
  }

  @Get('mural')
  async listMuralPosts() {
    return this.marketplaceService.listMuralPosts();
  }

  @Post('donations')
  async createDonation(
    @Body()
    body: {
      titulo: string;
      descricao: string;
      categoria: string;
      cidade: string;
      estado: string;
      fotos?: string[];
      userId?: number;
    },
  ) {
    return this.marketplaceService.createDonation(body);
  }

  @Get('donations')
  async listDonations() {
    return this.marketplaceService.listDonations();
  }
}
