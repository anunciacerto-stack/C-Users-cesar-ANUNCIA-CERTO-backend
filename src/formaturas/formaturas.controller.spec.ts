import { Test, TestingModule } from '@nestjs/testing';
import { FormaturasController } from './formaturas.controller';

describe('FormaturasController', () => {
  let controller: FormaturasController;

  beforeEach(async () => {
    const module: TestingModule = await Test.createTestingModule({
      controllers: [FormaturasController],
    }).compile();

    controller = module.get<FormaturasController>(FormaturasController);
  });

  it('should be defined', () => {
    expect(controller).toBeDefined();
  });
});
