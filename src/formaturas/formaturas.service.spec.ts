import { Test, TestingModule } from '@nestjs/testing';
import { FormaturasService } from './formaturas.service';

describe('FormaturasService', () => {
  let service: FormaturasService;

  beforeEach(async () => {
    const module: TestingModule = await Test.createTestingModule({
      providers: [FormaturasService],
    }).compile();

    service = module.get<FormaturasService>(FormaturasService);
  });

  it('should be defined', () => {
    expect(service).toBeDefined();
  });
});
