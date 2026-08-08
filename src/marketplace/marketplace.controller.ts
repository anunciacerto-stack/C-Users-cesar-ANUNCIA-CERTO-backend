import {
  Body,
  Controller,
  Delete,
  Get,
  NotFoundException,
  Param,
  ParseIntPipe,
  ParseUUIDPipe,
  Post,
} from '@nestjs/common';
import { CreateListingDto } from './dto/create-listing.dto';
import { MarketplaceService } from './marketplace.service';

@Controller('marketplace')
export class MarketplaceController {
  constructor(private readonly marketplaceService: MarketplaceService) {}

  @Post()
  async createListing(@Body() dto: CreateListingDto) {
    const listing = await this.marketplaceService.createListing(dto);
    return { data: listing };
  }

  @Get()
  async listAllListings() {
    const listings = await this.marketplaceService.listAllListings();
    return { data: listings };
  }

  @Get('category/:category')
  async listByCategory(@Param('category') category: string) {
    const listings = await this.marketplaceService.listByCategory(category);
    return { data: listings };
  }

  @Get('state/:state')
  async listByState(@Param('state') state: string) {
    const listings = await this.marketplaceService.listByState(state);
    return { data: listings };
  }

  @Get('city/:city')
  async listByCity(@Param('city') city: string) {
    const listings = await this.marketplaceService.listByCity(city);
    return { data: listings };
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
      userId?: string;
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
      userId?: string;
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
      userId?: string;
    },
  ) {
    return this.marketplaceService.createDonation(body);
  }

  @Get('donations')
  async listDonations() {
    return this.marketplaceService.listDonations();
  }

  @Get(':id')
  async getListingById(@Param('id', new ParseUUIDPipe()) id: string) {
    const listing = await this.marketplaceService.getListingById(id);
    if (!listing) {
      throw new NotFoundException('Listing not found');
    }
    return { data: listing };
  }

  @Get('universal-products')
  async listUniversalProducts() {
    return this.marketplaceService.listUniversalProducts();
  }

  @Post('universal-products')
  async createUniversalProduct(
    @Body()
    body: {
      name: string;
      description?: string;
      price: number;
      category: string;
      image: string;
    },
  ) {
    return this.marketplaceService.createUniversalProduct(body);
  }

  @Post('universal-products/seed')
  async seedUniversalProducts() {
    return this.marketplaceService.seedUniversalProducts();
  }
}

