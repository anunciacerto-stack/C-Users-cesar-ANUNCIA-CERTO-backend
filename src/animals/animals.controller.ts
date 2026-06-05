import { Body, Controller, Get, Param, ParseUUIDPipe, Post } from '@nestjs/common';
import { CreateAnimalDto } from './dto/create-animal.dto';
import { AnimalsService } from './animals.service';

@Controller('animals')
export class AnimalsController {
  constructor(private readonly animalsService: AnimalsService) {}

  @Post()
  async create(@Body() dto: CreateAnimalDto) {
    const data = await this.animalsService.create(dto);
    return { data };
  }

  @Get()
  async findAll() {
    const data = await this.animalsService.findAll();
    return { data };
  }

  @Get('state/:state')
  async findByState(@Param('state') state: string) {
    const data = await this.animalsService.findByState(state);
    return { data };
  }

  @Get('city/:city')
  async findByCity(@Param('city') city: string) {
    const data = await this.animalsService.findByCity(city);
    return { data };
  }

  @Get('type/:animalType')
  async findByType(@Param('animalType') animalType: string) {
    const data = await this.animalsService.findByType(animalType);
    return { data };
  }

  @Get(':id')
  async findById(@Param('id', new ParseUUIDPipe()) id: string) {
    const data = await this.animalsService.findById(id);
    return { data };
  }
}

@Controller('public')
export class PublicAnimalsController {
  constructor(private readonly animalsService: AnimalsService) {}

  @Get('animal/:publicCode')
  async findByPublicCode(@Param('publicCode') publicCode: string) {
    const data = await this.animalsService.findPublicByCode(publicCode);
    return { data };
  }
}
