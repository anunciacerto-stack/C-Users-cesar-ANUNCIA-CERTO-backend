import { Controller, Get } from '@nestjs/common';

@Controller('users')
export class UsersController {
  @Get()
  getStatus() {
    return { status: 'users module working' };
  }
}
