import { Body, Controller, Get, Param, ParseUUIDPipe, Post } from '@nestjs/common';
import { CreatePropertyDto } from './dto/create-property.dto';
import { PropertiesService } from './properties.service';

@Controller('properties')
export class PropertiesController {
  constructor(private readonly propertiesService: PropertiesService) {}

  @Post()
  async create(@Body() dto: CreatePropertyDto) {
    const data = await this.propertiesService.create(dto);
    return { data };
  }

  @Get()
  async findAll() {
    const data = await this.propertiesService.findAll();
    return { data };
  }

  @Get('state/:state')
  async findByState(@Param('state') state: string) {
    const data = await this.propertiesService.findByState(state);
    return { data };
  }

  @Get('city/:city')
  async findByCity(@Param('city') city: string) {
    const data = await this.propertiesService.findByCity(city);
    return { data };
  }

  @Get('type/:propertyType')
  async findByType(@Param('propertyType') propertyType: string) {
    const data = await this.propertiesService.findByType(propertyType);
    return { data };
  }

  @Get(':id')
  async findById(@Param('id', new ParseUUIDPipe()) id: string) {
    const data = await this.propertiesService.findById(id);
    return { data };
  }
}

@Controller('public')
export class PublicPropertiesController {
  constructor(private readonly propertiesService: PropertiesService) {}

  @Get('property/:publicCode')
  async findByPublicCode(@Param('publicCode') publicCode: string) {
    const data = await this.propertiesService.findPublicByCode(publicCode);
    return { data };
  }
}
